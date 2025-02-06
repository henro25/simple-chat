"""
Module Name: client.py
Description: The main client program that handles network communication with the server. It is the “controller” that connects UI events to network operations.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import socket

from configs.config import *

class Client:
    def __init__(self, host=SERVER_HOST, port=SERVER_PORT):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.sock.connect(self.server_address)
            debug(f"Client: connected to server at {self.server_address}")
        except Exception as e:
            debug(f"Client: failed to connect to server at {self.server_address}: {e}")
            raise

    def send_request(self, request):
        debug(f"Client: sending request: {request}")
        self.sock.sendall(request.encode('utf-8'))
        response_data = self.sock.recv(4096).decode('utf-8')
        debug(f"Client: received response: {response_data}")
        return response_data

    def close(self):
        self.sock.close()
