"""
Module Name: custom_protocol.py
Description: Contains protocol message parsing and handling functions for the server.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

from server import database
from configs.config import *
from server.utils import active_clients


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
        push_user = f'1.0 PUSH_USER {username}'
        for user, sock in active_clients.items():
            if user != username:
                try:
                    debug(f"Server: pushing message: {push_user}")
                    sock.sendall(push_user.encode('utf-8') + b"\n")
                except Exception as e:
                    print(f"Failed to push message to {user}: {e}")
        return handle_get_conversations(username, REG_PG)
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
        return handle_get_conversations(username, LGN_PG)
    else:
        return f"1.0 ERROR {errno}"

def handle_get_conversations(recipient, page_code):
    """
    Called when the client sends a successful CREATE or LOGIN message.
    Expects args: recipient (str).
    Returns a response in the format:
      "1.0 USERS pagecode recipient user1 num_unread1 user2 num_unread2 ..."
    """
    response = f"1.0 USERS {page_code} {recipient}"
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
    page_code = MSG_PG if oldest_msg_id != -1 else CONVO_PG
    history = database.get_recent_messages(client, user2, oldest_msg_id=oldest_msg_id)
    response = f"1.0 MSGS {page_code}"
    if not history:
        return response
    is_client = int(history[0]["sender"] == client)
    response = f"{response} {is_client}"
    num_messages = 0
    num_messages_from_sender_read = 0
    cur_sender = history[0]["sender"]
    formatted_messages = ""
    for message in history:
        if cur_sender != message["sender"]:
            formatted_messages = f" {num_messages}{formatted_messages}"
            response += formatted_messages
            num_messages = 0
            formatted_messages = ""
            cur_sender = message["sender"]
        else:
            num_messages_from_sender_read += 1
        num_messages += 1
        message_text = message["message"]
        id = message["id"]
        num_words = message_text.count(" ") + 1
        cur_msg = f" {id} {num_words} {message_text}"
        formatted_messages += cur_msg
    formatted_messages = f" {num_messages}{formatted_messages}"
    response += formatted_messages
    
    # Update the number of unread messages for the recipient
    cur_num_unread = database.get_num_unread(client)
    database.update_num_unread(client, user2, -min(cur_num_unread, num_messages_from_sender_read))
    debug(f"{client} read {min(cur_num_unread, num_messages_from_sender_read)} unread messages from {user2}")
    
    return response

def handle_send_message(args):
    """
    Handle a client's request to send a message.

    Parameters: [sender, recipient, message]

    Returns a response in the format:
        `1.0 ACK [msg ID]`
    """
    msg_id = -1
    sender = args[0]
    recipient = args[1]
    # check if recipient has deactivated their account
    valid_recipient = database.verify_valid_recipient(recipient)
    if valid_recipient:
        message = ' '.join(args[2: ])
        msg_id = database.store_message(sender, recipient, message)

    # Send the message to the recipient if they are online
    push_message = f"1.0 PUSH_MSG {sender} {msg_id} {message}\n"
    # debug(active_clients)
    if recipient in active_clients:
        recipient_sock = active_clients[recipient]
        try:
            debug(f"Server: pushing message: {message}")
            recipient_sock.sendall(push_message.encode('utf-8') + b"\n")
        except Exception as e:
            print(f"Failed to push message to {recipient}: {e}")
    
    # Update the number of unread messages for the recipient
    database.update_num_unread(recipient, sender, 1)

    return f"1.0 ACK {msg_id}"

def handle_delete_messages(args):
    """
    Handle a client's request to send a message.

    Parameters: [msg ID]

    Returns a response in the format:
        `1.0 DEL_MSG [msg ID]`
    """
    id = int(args[0])
    recipient, errno = database.delete_message(id)
    if recipient:
        response = f"1.0 DEL_MSG {id}"
        if recipient in active_clients:
            print(recipient)
            recipient_sock = active_clients[recipient]
            try:
                debug(f"Server: pushing message: {response}")
                recipient_sock.sendall(response.encode('utf-8') + b"\n")
            except Exception as e:
                print(f"Failed to push message to {recipient}: {e}")
        return response
    else:
        return f"1.0 ERROR {errno}"
    
def handle_delete_account(args):
    """
    Handle a client's request to delete their account.

    Parameters: [username]

    Returns a response in the format:
        `1.0 DEL_ACC`
    """
    username = args[0]
    errno = database.deactivate_account(username)
    if errno==SUCCESS:
        del active_clients[username]
        return '1.0 DEL_ACC'
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
    elif command == "DEL_ACC":
        return handle_delete_account(args)
    else:
        return f"1.0 ERROR {UNKNOWN_COMMAND}"
