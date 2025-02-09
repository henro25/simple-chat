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

def handle_get_chat_history(args):
    """
    Handle a client's request for chat history ealier than the oldest_msg_id. When oldest_msg_id == -1, return 
    the most recent messages. 

    Parameters: [client, user2, oldest_msg_id]

    Returns a response in the format:
        `1.0 MSGS [1 if user who sent the ealiest message is same as the user receiving this history else 0] 
        [num msgs] [msg ID (if 1), num words, msg1] [msg ID (if 1), num words, msg2] ...`
    """
    client = args[0]
    user2 = args[1]
    oldest_msg_id = int(args[2])
    history = database.get_recent_messages(client, user2, oldest_msg_id=oldest_msg_id)
    if not history:
        return "1.0 MSGS "
    response = "1.0 MSGS " + ("1" if history[0]["sender"] == client else "0")
    num_messages = 0
    cur_sender = history[0]["sender"]
    formatted_messages = ""
    for message in history:
        if cur_sender != message["sender"]:
            formatted_messages = f" {num_messages} {formatted_messages}"
            response += formatted_messages
            num_messages = 0
            formatted_messages = ""
        num_messages += 1
        message_text = message["message"]
        id = message["id"] if message["sender"] == client else -1
        num_words = message_text.count(" ")+1
        cur_msg = f" {id} {num_words} {message_text}"
        formatted_messages += cur_msg
    formatted_messages = f" {num_messages}{formatted_messages}"
    response += formatted_messages
    return response

def handle_send_message(args):
    """
    Handle a client's request to send a message.

    Parameters: [sender, recipient, message]

    Returns a response in the format:
        `1.0 ACK [msg ID]`
    """
    sender = args[0]
    recipient = args[1]
    message = args[2]
    msg_id = database.store_message(sender, recipient, message)
    return f"1.0 ACK {msg_id}"

def handle_delete_messages(args):
    """
    Handle a client's request to send a message.

    Parameters: [msg ID]

    Returns a response in the format:
        `1.0 DEL_MSG [msg ID]`
    """
    id = int(args[0])
    success, errno = database.delete_message(id)
    if success:
        return f"1.0 DEL_MSG {id}"
    else:
        return f"1.0 ERROR {errno}"

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
    elif command == "READ":
        return handle_get_chat_history(args)
    elif command == "SEND":
        return handle_send_message(args)
    elif command == "DEL_MSG":
        return handle_delete_messages(args)
    else:
        return f"1.0 ERROR {UNKNOWN_COMMAND}"
