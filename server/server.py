"""
Module Name: server.py
Description: The main entry point for running the server. It will set up the socket, listen for incoming connections, and route messages according to the protocol.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sys
import selectors
import socket
import types
import server.utils as utils
from . import database
from configs.config import *

# Import both protocol modules.
import server.protocols.custom_protocol as custom_protocol
import server.protocols.json_protocol as json_protocol

# gRPC imports
import chat_service_pb2_grpc
import grpc
import threading
from concurrent import futures
from server.protocols.grpc_server_protocol import MyChatService

sel = selectors.DefaultSelector()
actual_address = None

def accept_wrapper(sock):
    """Accept new connections and register them."""
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"", username=None)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

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
            # Process complete messages (terminated by newline)
            while b"\n" in data.inb:
                message_bytes, data.inb = data.inb.split(b"\n", 1)
                try:
                    message_str = message_bytes.decode("utf-8")
                except Exception as e:
                    print(f"Decoding error: {e}")
                    continue

                # Check the protocol version from the beginning of the message.
                if message_str.startswith("1.0"):
                    # Process using the custom protocol.
                    version, command, args = custom_protocol.parse_message(message_str)
                    response = custom_protocol.process_message(message_str)
                    if command in ("LOGIN", "CREATE") and not response.startswith("1.0 ERROR"):
                        username = args[0]
                        data.username = username
                        utils.add_active_client(username, sock)
                        debug(f"User {username} is now online (Custom protocol).")
                elif message_str.startswith("2.0"):
                    # Process using the JSON protocol.
                    version, opcode, msg_data = json_protocol.parse_message(message_str)
                    response = json_protocol.process_message(message_str)
                    if opcode in ("LOGIN", "CREATE") and not "ERROR" in response:
                        username = msg_data[0]
                        data.username = username
                        utils.add_active_client(username, sock)
                        debug(f"User {username} is now online (JSON protocol).")
                else:
                    # Unsupported protocol version; return error message.
                    error_response = json_protocol.wrap_message("ERROR", [str(UNSUPPORTED_VERSION)])
                    data.outb += error_response.encode("utf-8") + b"\n"
                    debug(f"Unsupported protocol version from {data.addr}: {message_str}")
                    continue

                debug(f"Received message from {data.addr}: {message_str}")
                if response:
                    data.outb += response.encode("utf-8") + b"\n"
        else:
            if data.username:
                utils.remove_active_client(data.username)
                debug(f"User {data.username} disconnected.")
            sel.unregister(sock)
            sock.close()

    if mask & selectors.EVENT_WRITE:
        if data.outb:
            try:
                sent = sock.send(data.outb)
                debug(f"Sent {data.outb[:sent]} to {data.addr}")
                data.outb = data.outb[sent:]
            except Exception as e:
                print(f"Error writing to {data.addr}: {e}")

def get_local_ip():
    """
    Get the current local IP address by connecting to an external server.
    This method returns the IP address used to reach the Internet.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public DNS server. The IP doesn't matter.
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
    
    port_to_use = actual_address[1] + 1
    grpc_address = f"{actual_address[0]}:{port_to_use}"
    
    # Attempt to bind the gRPC server to the specified address.
    bound_port = server.add_insecure_port(grpc_address)
    
    # Check if the binding was successful.
    if bound_port == 0:
        print(f"Error: Port {port_to_use} is in use. Please try again with a different configuration.")
        sys.exit(1)
    
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    # Initialize the database (create tables, etc.)
    database.initialize_db()

    # Get the current local IP address.
    local_ip = get_local_ip()

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind to the current IP address and port 0 (random available port)
    lsock.bind((local_ip, 0))
    lsock.listen()
    # Get the actual bound address (IP and chosen port)
    actual_address = lsock.getsockname()
    print("Listening on", actual_address)
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)
    
    # Start the gRPC server in a separate thread.
    grpc_thread = threading.Thread(target=create_rpc_threads, daemon=True)
    grpc_thread.start()

    # Main event loop to handle incoming connections and messages for protocol 1.0 and 2.0
    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    # This is our listening socket
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()
