"""
Module Name: utils.py
Description: Contains helper functions and utilities (such as logging wrappers, error handling functions, and dictionaries for tracking states).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import threading
from configs.config import debug

# Global replication configuration
is_primary = False       # True if this server is the primary
actual_address = None    # Tuple of (ip, port) for this server

# Active clients dictionary to track logged-in users
active_clients = {}

# Passive clients dictionary to track users that have not logged in, but are connected
passive_clients = {}

# RPC Send Queue that holds live updates to be sent to active clients
rpc_send_queue = {}

# List of active servers.
active_servers = []

# Create locks for thread-safe access to shared resources
active_clients_lock = threading.Lock()
rpc_send_queue_lock = threading.Lock()
passive_clients_lock = threading.Lock()

# -------------------------
# Helper functions for managing active and passive clients
# -------------------------

def add_active_client(username, client_socket):
    remove_passive_client(client_socket)
    with active_clients_lock:
        active_clients[username] = client_socket
        debug(f"User {username} added to active clients.")

def get_active_client(username):
    with active_clients_lock:
        return active_clients.get(username)

def remove_active_client(username):
    with active_clients_lock:
        if username in active_clients:
            del active_clients[username]
            print(f"User {username} removed from active clients.")
            
def add_passive_client(addr, client_sock):
    with passive_clients_lock:
        passive_clients[addr] = client_sock

def get_passive_client(addr):
    with passive_clients_lock:
        return passive_clients.get(addr)

def remove_passive_client(client_socket):
    with passive_clients_lock:
        for addr, sock in list(passive_clients.items()):
            if sock == client_socket:
                del passive_clients[addr]
                debug(f"Passive client {addr} removed.")
                break
            
# -------------------------
# Helper functions for managing RPC send queue
# -------------------------

def add_rpc_send_queue_user(username):
    with rpc_send_queue_lock:
        rpc_send_queue[username] = []

def remove_rpc_send_queue_user(username):
    with rpc_send_queue_lock:
        if username in rpc_send_queue:
            del rpc_send_queue[username]
            print(f"User {username} removed from RPC send queue.")

# -------------------------
# Replication configuration accessors
# -------------------------
def set_replication_config(primary, address):
    """
    Set the replication configuration globals.
    
    Parameters:
      primary (bool): True if this server is primary.
      address (tuple): (ip, port) tuple for this server.
    """
    global is_primary, actual_address
    is_primary = primary
    actual_address = address
    debug(f"Replication config set: is_primary={is_primary}, actual_address={actual_address}")

def get_replication_config():
    """
    Returns the current replication configuration.
    
    Returns:
      tuple: (is_primary, actual_address)
    """
    return is_primary, actual_address