"""
Module Name: server.py
Description: The main entry point for running the server. It will set up the socket, listen for incoming connections, and route messages according to the protocol.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import selectors
import socket
import types
from . import database  # database module for registration/login

import server.protocols.custom_protocol as custom_protocol
from configs.config import *
from server.state import active_clients

# Create a default selector
sel = selectors.DefaultSelector()

# # Create a dict to track active users
# active_clients = {}

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
            while b"\n" in data.inb:
                message_bytes, data.inb = data.inb.split(b"\n", 1)
                try:
                    message_str = message_bytes.decode("utf-8")
                except Exception as e:
                    print(f"Decoding error: {e}")
                    message_str = ""

                _, command, args =custom_protocol.parse_message(message_str)

                debug(f"Received message from {data.addr}: {message_str}")
                response = custom_protocol.process_message(message_str)
                # Handle login to track active clients
                if command == "LOGIN" or command == "CREATE" and response[:10] != "1.0 ERROR":
                    username = args[0]
                    data.username = username # store username of data
                    active_clients[username] = sock  # Track active user
                    # debug(active_clients)
                    debug(f"User {username} is now online.")

                if response:
                    data.outb += response.encode("utf-8") + b"\n"
        else:
            if data.username:
                active_clients.pop(data.username, None)  # Remove user from active clients
                debug(f"User {data.username} disconnected.")
            sel.unregister(sock)
            sock.close()

    if mask & selectors.EVENT_WRITE:
        if data.outb:
            try:
                sent = sock.send(data.outb)
                data.outb = data.outb[sent:]
            except Exception as e:
                print(f"Error writing to {data.addr}: {e}")

if __name__ == "__main__":
    # Initialize the database (create tables, etc.)
    database.initialize_db()

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((SERVER_HOST, SERVER_PORT))
    lsock.listen()
    print("Listening on", (SERVER_HOST, SERVER_PORT))
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)

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
