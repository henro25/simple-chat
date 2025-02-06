"""
Module Name: server.py
Description: The main entry point for running the server. It will set up the socket, listen for incoming connections, and route messages according to your protocol.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import selectors
import socket
import types
from . import database  # Your database module for registration/login

from .config import *

# Create a default selector
sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Accept the connection
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def process_message(message):
    """
    Process a message string according to our custom protocol.
    
    Expected formats:
      - "1.0 CREATE username password"
      - "1.0 LOGIN username password"
    
    Returns a response string.
    """
    tokens = message.strip().split()

    version, command, username, password = tokens[0], tokens[1], tokens[2], tokens[3]
    
    if version not in SUPPORTED_VERSIONS:
        return f"1.0 ERROR {UNSUPPORTED_VERSION}"
    
    if command.upper() == "CREATE":
        success, errno = database.register_account(username, password)
        if success:
            return "1.0 SUCCESS Registration complete"
        else:
            # For example, error code 1 indicates username already exists.
            return f"1.0 ERROR {errno}"
    elif command.upper() == "LOGIN":
        success, errno = database.verify_login(username, password)
        if success:
            return "1.0 SUCCESS Login successful"
        else:
            # For example, error code 4 for login failure.
            return f"1.0 ERROR {errno}"

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data

    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)  # Read incoming data
        except Exception as e:
            print(f"Error reading from {data.addr}: {e}")
            recv_data = None

        if recv_data:
            data.inb += recv_data
            # If newline is detected, process complete messages.
            while b"\n" in data.inb:
                message_bytes, data.inb = data.inb.split(b"\n", 1)
                try:
                    message_str = message_bytes.decode("utf-8")
                except Exception as e:
                    print(f"Decoding error: {e}")
                    message_str = ""
                print(f"Received message from {data.addr}: {message_str}")
                response = process_message(message_str)
                print(f"Sending response: {response}")
                data.outb += response.encode("utf-8") + b"\n"
        else:
            print(f"Closing connection to {data.addr}")
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
    lsock.bind((HOST, PORT))
    lsock.listen()
    print("Listening on", (HOST, PORT))
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
