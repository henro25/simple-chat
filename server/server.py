"""
Module Name: server.py
Description: The main entry point for running the server with replication and fault tolerance.
Author: Henry Huang and Bridget Ma (modified for replication)
Date: 2024-3-26 (modified)
"""

import sys
import selectors
import socket
import types
import threading
import time
from concurrent import futures

import server.utils as utils
from . import database
from configs.config import *

# Import both protocol modules.
import server.protocols.custom_protocol as custom_protocol
import server.protocols.json_protocol as json_protocol

# gRPC imports
import chat_service_pb2_grpc
import chat_service_pb2
import grpc
from server.protocols.grpc_server_protocol import MyChatService

sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    """Accept new connections and register them."""
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"", username=None)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)
    utils.add_passive_client(addr, conn)

def service_connection(key, mask):
    """Handles client-server communication."""
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)
        except Exception as e:
            print(f"Error reading from {data.addr}: {e}")
            recv_data = None
        if recv_data:
            data.inb += recv_data
            while b"\n" in data.inb:
                message_bytes, data.inb = data.inb.split(b"\n", 1)
                try:
                    message_str = message_bytes.decode("utf-8")
                except Exception as e:
                    print(f"Decoding error: {e}")
                    continue
                if message_str.startswith("1.0"):
                    version, command, args = custom_protocol.parse_message(message_str)
                    response = custom_protocol.process_message(message_str)
                    if command in ("LOGIN", "CREATE") and not response.startswith("1.0 ERROR"):
                        username = args[0]
                        data.username = username
                        utils.add_active_client(username, sock)
                        utils.add_rpc_send_queue_user(username)
                        utils.debug(f"User {username} is now online (Custom protocol).")
                elif message_str.startswith("2.0"):
                    version, opcode, msg_data = json_protocol.parse_message(message_str)
                    response = json_protocol.process_message(message_str)
                    if opcode in ("LOGIN", "CREATE") and "ERROR" not in response:
                        username = msg_data[0]
                        data.username = username
                        utils.add_active_client(username, sock)
                        utils.add_rpc_send_queue_user(username)
                        utils.debug(f"User {username} is now online (JSON protocol).")
                else:
                    error_response = json_protocol.wrap_message("ERROR", [str(UNSUPPORTED_VERSION)])
                    data.outb += error_response.encode("utf-8") + b"\n"
                    utils.debug(f"Unsupported protocol version from {data.addr}: {message_str}")
                    continue
                utils.debug(f"Received message from {data.addr}: {message_str}")
                if response:
                    data.outb += response.encode("utf-8") + b"\n"
        else:
            if data.username:
                utils.remove_active_client(data.username)
                utils.debug(f"User {data.username} disconnected.")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            try:
                sent = sock.send(data.outb)
                utils.debug(f"Sent {data.outb[:sent]} to {data.addr}")
                data.outb = data.outb[sent:]
            except Exception as e:
                print(f"Error writing to {data.addr}: {e}")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def create_rpc_threads():
    """Create and start gRPC server threads on the specified port + 1."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_service_pb2_grpc.add_ChatServiceServicer_to_server(MyChatService(), server)
    # Use the replication config from utils.
    _, actual_addr = utils.get_replication_config()
    port_to_use = actual_addr[1] + 1
    grpc_address = f"{actual_addr[0]}:{port_to_use}"
    bound_port = server.add_insecure_port(grpc_address)
    if bound_port == 0:
        print(f"Error: Port {port_to_use} is in use. Please try again with a different configuration.")
        sys.exit(1)
    server.start()
    threading.Thread(target=monitor_servers, daemon=True).start()
    server.wait_for_termination()

def join_network(bootstrap_ip, bootstrap_port):
    bootstrap_grpc_address = f"{bootstrap_ip}:{bootstrap_port + 1}"
    channel = grpc.insecure_channel(bootstrap_grpc_address)
    stub = chat_service_pb2_grpc.ChatServiceStub(channel)
    try:
        join_req = chat_service_pb2.JoinNetworkRequest(
            server_ip=utils.actual_address[0],
            server_port=utils.actual_address[1]
        )
        join_resp = stub.JoinNetwork(join_req)
        utils.active_servers.clear()
        for s in join_resp.server_list:
            server_info = type("ServerInfo", (), {})()
            server_info.ip = s.ip
            server_info.port = s.port
            server_info.is_primary = 0
            utils.active_servers.append(server_info)
            database.add_server(s.ip, s.port, is_primary=0)
        print("Joined network. Received server list:", utils.active_servers)
    except Exception as e:
        print("Error joining network:", e)
        sys.exit(1)

def broadcast_server_list():
    for server_info in utils.active_servers:
        if (server_info.ip, server_info.port) == utils.actual_address:
            continue
        try:
            grpc_address = f"{server_info.ip}:{server_info.port + 1}"
            channel = grpc.insecure_channel(grpc_address)
            stub = chat_service_pb2_grpc.ChatServiceStub(channel)
            update_req = chat_service_pb2.UpdateServerListRequest(
                server_list=[chat_service_pb2.ServerInfo(ip=s.ip, port=s.port) for s in utils.active_servers]
            )
            resp = stub.UpdateServerList(update_req)
            print(f"Broadcasted server list to {server_info.ip}:{server_info.port}")
        except Exception as e:
            print(f"Failed to broadcast to {server_info.ip}:{server_info.port}: {e}")

def elect_new_primary():
    if not utils.active_servers:
        return
    sorted_servers = sorted(utils.active_servers, key=lambda s: (s.ip, s.port))
    new_primary = sorted_servers[0]
    if (new_primary.ip, new_primary.port) == utils.actual_address:
        utils.set_replication_config(True, utils.actual_address)
        print("This server has been elected as the new PRIMARY.")
        database.add_server(utils.actual_address[0], utils.actual_address[1], is_primary=1)
    else:
        utils.set_replication_config(False, utils.actual_address)
        print(f"New primary is {new_primary.ip}:{new_primary.port}")
    broadcast_server_list()

def monitor_servers():
    while True:
        time.sleep(5)
        updated = False
        for server_info in utils.active_servers.copy():
            if (server_info.ip, server_info.port) == utils.actual_address:
                database.update_heartbeat(utils.actual_address[0], utils.actual_address[1])
                continue
            try:
                grpc_address = f"{server_info.ip}:{server_info.port + 1}"
                channel = grpc.insecure_channel(grpc_address)
                stub = chat_service_pb2_grpc.ChatServiceStub(channel)
                health_req = chat_service_pb2.HealthCheckRequest()
                resp = stub.HealthCheck(health_req, timeout=2)
                if resp.status != "OK":
                    raise Exception("Health check failed")
                database.update_heartbeat(server_info.ip, server_info.port)
            except Exception as e:
                print(f"Server {server_info.ip}:{server_info.port} is unresponsive. Removing from active servers.")
                utils.active_servers.remove(server_info)
                database.remove_server(server_info.ip, server_info.port)
                updated = True
        if updated:
            if not any(s for s in utils.active_servers if s.is_primary):
                elect_new_primary()
            broadcast_server_list()

if __name__ == "__main__":
    from os import environ
    
    # Initialize the main database and the server list table.
    # After binding the socket, get the address:
    local_ip = get_local_ip()
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((local_ip, 0))
    lsock.listen()
    addr = lsock.getsockname()
    
    # Set a unique database name based on the server's address.
    environ["DATABASE_NAME"] = f"chat_{addr[0]}_{addr[1]}.db"
    print(f"chat_{addr[0]}_{addr[1]}.db")
    
    database.initialize_db()

    # Set replication config accordingly.
    utils.set_replication_config(False, addr)  # default; may update below
    print("Listening on", addr)
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)
    
    if len(sys.argv) >= 3:
        bootstrap_ip = sys.argv[1]
        bootstrap_port = int(sys.argv[2])
        print(f"Joining network via bootstrap server {bootstrap_ip}:{bootstrap_port}")
        join_network(bootstrap_ip, bootstrap_port)
        utils.set_replication_config(False, addr)
        database.add_server(addr[0], addr[1], is_primary=0)
    else:
        utils.set_replication_config(True, addr)
        primary_server_info = type("ServerInfo", (), {})()
        primary_server_info.ip = addr[0]
        primary_server_info.port = addr[1]
        primary_server_info.is_primary = 1
        utils.active_servers.append(primary_server_info)
        database.add_server(addr[0], addr[1], is_primary=1)
        print("Starting as primary server.")
    
    grpc_thread = threading.Thread(target=create_rpc_threads, daemon=True)
    grpc_thread.start()

    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()
