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

import sys
import socket
import selectors

import configs.config as config

# Import both protocol modules.
import client.protocols.custom_protocol as custom_protocol
import client.protocols.json_protocol as json_protocol
import client.protocols.grpc_protocol as grpc_protocol

# gRPC imports
import grpc
import chat_service_pb2_grpc

# Create a default selector
sel = selectors.DefaultSelector()

class Client:
    def __init__(self, host=config.SERVER_HOST, port=config.SERVER_PORT):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)  # Set socket to non-blocking mode
        self.messaging_page = None  # store the current messaging page the user is on
        self.register_page = None   # store the register page for client
        self.login_page = None      # store the login page for client
        self.list_convos_page = None  # store the current list convo page the client is on
        self.username = None        # Store username of client
        self.cur_convo = None       # Store username of other user if client on messaging page
        self.registered = 0         # Stores state of socket
        self.inb = ""  # Buffer to hold incoming data
        self.channel = grpc.insecure_channel(f'{config.SERVER_HOST}:{config.SERVER_PORT + 1}') # gRPC channel
        self.stub = chat_service_pb2_grpc.ChatServiceStub(self.channel) # gRPC stub
        
        try:
            self.sock.connect(self.server_address)
            config.debug(f"Client: connected to server at {self.server_address}")
        except BlockingIOError:
            pass
        except Exception as e:
            config.debug(f"Client: failed to connect to server at {self.server_address}: {e}")
            raise

    def service_connection(self, key, mask):
        """Handles both incoming communication with the server."""
        if mask & selectors.EVENT_READ:
            self.receive_message()
    
    def receive_message(self):
        """Handles incoming messages from the server."""
        try:
            new_data = self.sock.recv(4096)
            if new_data:
                # Append new data (decoded as utf-8) to the buffer.
                self.inb += new_data.decode('utf-8')
                # Process all complete messages (terminated by newline).
                while "\n" in self.inb:
                    # Split off one complete message and update the buffer with the remainder.
                    message, self.inb = self.inb.split("\n", 1)
                    if message:  # Only process if non-empty
                        config.debug(f"Received server response: {message.strip()}")
                        # Check the protocol version and dispatch accordingly.
                        if message.startswith("1.0"):
                            custom_protocol.process_message(message, self)
                        elif message.startswith("2.0"):
                            json_protocol.process_message(message, self)
                        else:
                            error_response = json_protocol.wrap_message("ERROR", [str(config.UNSUPPORTED_VERSION)])
                            config.debug(f"Unsupported protocol version received: {message.strip()}")
            else:
                # Handle the case where recv() returns an empty byte string (connection closed).
                pass
        except BlockingIOError:
            pass
        except Exception as e:
            config.debug(f"Current IP address and port: {self.server_address}")
            print(f"Error receiving message: {e}")
            sys.exit(1)

    def send_request(self, request):
        """
        Send a request to the server, either via gRPC or directly via sockets.
        Instead of immediately waiting for a response, we store outgoing data and
        let the selector notify us when we can send it with sockets.
        """
        if config.CUR_PROTO_VERSION == "3.0":
            grpc_protocol.send_grpc_request(self, request)
            return
        
        # For other versions, we send the request directly via sockets
        config.debug(f"Client: sending request: {request}")
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
        except Exception as e:
            print(f"Error in client run loop: {e}")

    def reset(self):
        """Resets client information"""
        self.username = None
        self.outgoing_requests = []

    def close(self):
        """Close the client connection."""
        sel.unregister(self.sock)
        self.sock.close()
