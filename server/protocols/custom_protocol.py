"""
Module Name: custom_protocol.py
Description: Contains protocol message parsing and handling functions for the server.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

from server import database
from configs.config import *

def parse_message(message):
    """
    Parse a protocol message into version, command, and arguments.
    
    Expected message examples:
      - "1.0 CREATE username password"
      - "1.0 LOGIN username password"
    
    Returns:
        (version, command, args) if valid; otherwise (None, None, []).
    """
    tokens = message.strip().split()
    if len(tokens) < 2:
        return None, None, []
    version = tokens[0]
    command = tokens[1].upper()
    args = tokens[2:]
    return version, command, args

def handle_create(args):
    """
    Handle the CREATE command.
    Expects args: [username, password].
    """
    username, password = args[0], args[1]
    success, errno = database.register_account(username, password)
    if success:
        return handle_get_conversations(username)
    else:
        return f"1.0 ERROR {errno}"

def handle_login(args):
    """
    Handle the LOGIN command.
    Expects args: [username, password].
    """
    username, password = args[0], args[1]
    success, errno = database.verify_login(username, password)
    if success:
        return handle_get_conversations(username)
    else:
        return f"1.0 ERROR {errno}"

def handle_get_conversations(recipient):
    """
    Called when the client sends a successful CREATE or LOGIN message.
    Expects args: recipient (str).
    Returns a response in the format:
      "1.0 USERS user1 num_unread1 user2 num_unread2 ..."
    """
    response = "1.0 USERS"
    for user, unread in database.get_conversations(recipient):
        response += f" {user} {unread}"
    return response

def process_message(message):
    """
    Process a message string according to our custom protocol.
    Dispatches to the appropriate handler.
    """
    version, command, args = parse_message(message)
    if version not in SUPPORTED_VERSIONS:
        return f"1.0 ERROR {UNSUPPORTED_VERSION}"
    
    if command == "CREATE":
        return handle_create(args)
    elif command == "LOGIN":
        return handle_login(args)
    else:
        return f"1.0 ERROR {UNKNOWN_COMMAND}"
