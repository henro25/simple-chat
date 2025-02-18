"""
Module Name: utils.py
Description: Contains helper functions and utilities (such as logging wrappers, error handling functions, and dictionaries for tracking states).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import threading

# Your shared dictionary
active_clients = {}

# Create a lock for active_clients
active_clients_lock = threading.Lock()

def add_active_client(username, client_info):
    with active_clients_lock:
        active_clients[username] = client_info

def get_active_client(username):
    with active_clients_lock:
        return active_clients.get(username)

def remove_active_client(username):
    with active_clients_lock:
        if username in active_clients:
            del active_clients[username]
            print(f"User {username} removed from active clients.")
