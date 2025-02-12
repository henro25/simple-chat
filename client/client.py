"""
Module Name: client.py
Description: The main client program that handles network communication with the server. It is the “controller” that connects UI events to network operations.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import socket
import selectors

from configs.config import *
from client.protocols.custom_protocol import *

# Create a default selector
sel = selectors.DefaultSelector()

class Client:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)  # Set socket to non-blocking mode
        self.messaging_page = None # store the current messaging page the user is on
        self.register_page = None # store the register page for client
        self.login_page = None # store the login page for client
        self.list_convos_page = None # store the current list convo page the client is on
        self.outgoing_requests = []  # Queue for outgoing messages
        self.username = None # Store username of client
        self.cur_convo = None # Store username of other user if client on messaging page
        self.registered = 0 # Stores state of socket
        try:
            self.sock.connect(self.server_address)
            debug(f"Client: connected to server at {self.server_address}")
        except BlockingIOError:
            pass
        except Exception as e:
            debug(f"Client: failed to connect to server at {self.server_address}: {e}")
            raise

    def service_connection(self, key, mask):
        """Handles both incoming and outgoing communication with the server."""
        if mask & selectors.EVENT_READ:
            self.receive_message()
        # if mask & selectors.EVENT_WRITE:
        #     self.process_outgoing_requests()
    
    def receive_message(self):
        """Handles incoming messages from the server."""
        try:
            response_data = self.sock.recv(4096).decode('utf-8')
            if response_data:
                debug(f"Received server response: {response_data.strip()}")  # Debugging
                process_message(response_data, self)
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"Error receiving message: {e}")
            
    def send_request(self, request):
        """
        Send a request to the server.
        
        Instead of immediately waiting for a response, we store outgoing data and
        let the selector notify us when we can send it.
        """
        debug(f"Client: sending request: {request}")
        try:
            self.sock.sendall(request.encode('utf-8'))
        except Exception as e:
            print(f"Error sending request: {e}")

    def run(self):
        """Main event loop to listen for messages and handle requests."""
        # Register socket with selectors for READ and WRITE events
        if not self.registered:
            sel.register(self.sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=self)
            self.registered = 1
        try:
            events = sel.select(timeout=None)
            for key, mask in events:
                self.service_connection(key, mask)
        except KeyboardInterrupt:
            self.close()
            print("Client shutting down.")

    def close(self):
        """Close the client connection."""
        sel.unregister(self.sock)
        self.sock.close()
