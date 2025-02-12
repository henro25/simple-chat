"""
Module Name: client.py
Description: The main client program that handles network communication with the server.
It connects UI events to network operations and now supports two protocol versions:
  - 1.0: Handled by client.protocols.custom_protocol
  - 2.0: Handled by client.protocols.json_protocol
If an unsupported version is received, an error is generated.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import socket
import selectors

from configs.config import *

# Import both protocol modules.
import client.protocols.custom_protocol as custom_protocol
import client.protocols.json_protocol as json_protocol

# Create a default selector
sel = selectors.DefaultSelector()

class Client:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)  # Set socket to non-blocking mode
        self.messaging_page = None  # store the current messaging page the user is on
        self.register_page = None   # store the register page for client
        self.login_page = None      # store the login page for client
        self.list_convos_page = None  # store the current list convo page the client is on
        self.outgoing_requests = []  # Queue for outgoing messages
        self.username = None        # Store username of client
        self.cur_convo = None       # Store username of other user if client on messaging page
        self.registered = 0         # Stores state of socket
        try:
            self.sock.connect(self.server_address)
            debug(f"Client: connected to server at {self.server_address}")
        except BlockingIOError:
            pass
        except Exception as e:
            debug(f"Client: failed to connect to server at {self.server_address}: {e}")
            raise

    def service_connection(self, key, mask):
        """Handles both incoming communication with the server."""
        if mask & selectors.EVENT_READ:
            self.receive_message()
    
    def receive_message(self):
        """Handles incoming messages from the server."""
        try:
            response_data = self.sock.recv(4096).decode('utf-8')
            if response_data:
                debug(f"Received server response: {response_data.strip()}")
                # Check the protocol version and dispatch accordingly.
                if response_data.startswith("1.0"):
                    # Process with the custom protocol.
                    custom_protocol.process_message(response_data, self)
                elif response_data.startswith("2.0"):
                    # Process with the JSON protocol.
                    json_protocol.process_message(response_data, self)
                else:
                    # Unsupported version; generate an error response.
                    error_response = json_protocol.wrap_message("ERROR", [str(UNSUPPORTED_VERSION)])
                    debug(f"Unsupported protocol version received: {response_data.strip()}")
                    # Optionally, you might want to display or handle the error locally.
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

    def reset(self):
        """Resets client information"""
        self.username = None
        self.outgoing_requests = []

    def close(self):
        """Close the client connection."""
        sel.unregister(self.sock)
        self.sock.close()
