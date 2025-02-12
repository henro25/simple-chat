"""
Module Name: json_protocol.py
Description: Implements a JSON wire protocol logic for the server. It defines how messages are parsed, validated, and constructed (both for sending responses and interpreting client requests).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import json
from server import database
from configs.config import *
from server.utils import active_clients

PROTOCOL_VERSION = "2.0"

def wrap_message(opcode, data):
    """
    Wrap the opcode and data into a JSON protocol message prefixed with the protocol version.
    """
    return f"{PROTOCOL_VERSION} {json.dumps({'opcode': opcode, 'data': data})}"

def parse_message(message):
    """
    Parse a JSON protocol message into version, opcode, and data.

    Expected message example:
      "2.0 {\"opcode\": \"LOGIN\", \"data\": [\"username\", \"password\"]}"

    Returns:
        (version, opcode, data) if valid; otherwise (None, None, []).
    """
    try:
        tokens = message.strip().split(' ', 1)
        if len(tokens) < 2:
            return None, None, []
        version = tokens[0]
        json_part = tokens[1]
        msg_obj = json.loads(json_part)
        opcode = msg_obj.get("opcode")
        data = msg_obj.get("data", [])
        return version, opcode, data
    except Exception:
        return None, None, []

def handle_create(data):
    """
    Handle the CREATE command.
    Expects data: [username, password].
    """
    username, password = data[0], data[1]
    success, errno = database.register_account(username, password)
    if success:
        push_user = wrap_message("PUSH_USER", [username])
        for user, sock in active_clients.items():
            if user != username:
                try:
                    debug(f"Server: pushing message: {push_user}")
                    sock.sendall(push_user.encode('utf-8') + b"\n")
                except Exception as e:
                    print(f"Failed to push message to {user}: {e}")
        return handle_get_conversations(username, REG_PG)
    else:
        return wrap_message("ERROR", [errno])

def handle_login(data):
    """
    Handle the LOGIN command.
    Expects data: [username, password].
    """
    username, password = data[0], data[1]
    success, errno = database.verify_login(username, password)
    if success:
        return handle_get_conversations(username, LGN_PG)
    else:
        return wrap_message("ERROR", [errno])

def handle_get_conversations(recipient, page_code):
    """
    Called after a successful CREATE or LOGIN.
    Returns a response with data:
      [page_code, recipient, user1, unread1, user2, unread2, ...]
    """
    data = [str(page_code), recipient]
    for user, unread in database.get_conversations(recipient):
        data.extend([user, str(unread)])
    return wrap_message("USERS", data)

def handle_get_chat_history(data):
    """
    Handle a client's request for chat history.
    Expects data: [client, user2, oldest_msg_id].

    Returns a response with data:
      [page_code, is_client, num_msgs, msg_id, num_words, msg, ...]
    """
    client = data[0]
    user2 = data[1]
    oldest_msg_id = int(data[2])
    num_msgs = int(data[3])
    page_code = MSG_PG if oldest_msg_id != -1 else CONVO_PG
    history = database.get_recent_messages(client, user2, oldest_msg_id=oldest_msg_id, limit=num_msgs)
    data_list = [str(page_code)]
    if not history:
        return wrap_message("MSGS", data_list)
    is_client = int(history[0]["sender"] == client)
    data_list.append(str(is_client))
    num_messages = 0
    num_messages_from_sender_read = 0
    cur_sender = history[0]["sender"]
    formatted_messages = []
    for message in history:
        if cur_sender != message["sender"]:
            formatted_messages.insert(0, str(num_messages))
            data_list.extend(formatted_messages)
            num_messages = 0
            formatted_messages = []
            cur_sender = message["sender"]
        else:
            num_messages_from_sender_read += 1
        num_messages += 1
        msg_id = message["id"]
        message_text = message["message"]
        num_words = message_text.count(" ") + 1
        formatted_messages.extend([str(msg_id), str(num_words), message_text])
    formatted_messages.insert(0, str(num_messages))
    data_list.extend(formatted_messages)
    cur_num_unread = database.get_num_unread(client)
    database.update_num_unread(client, user2, -min(cur_num_unread, num_messages_from_sender_read))
    debug(f"{client} read {min(cur_num_unread, num_messages_from_sender_read)} unread messages from {user2}")
    return wrap_message("MSGS", data_list)

def handle_send_message(data):
    """
    Handle a client's request to send a message.
    Expects data: [sender, recipient, message].

    Returns a response with data: [msg_id].
    """
    sender = data[0]
    recipient = data[1]
    message = " ".join(data[2:])
    valid_recipient = database.verify_valid_recipient(recipient)
    msg_id = -1
    if valid_recipient:
        msg_id = database.store_message(sender, recipient, message)
    push_message = wrap_message("PUSH_MSG", [sender, str(msg_id), message])
    if recipient in active_clients:
        recipient_sock = active_clients[recipient]
        try:
            debug(f"Server: pushing message: {push_message}")
            recipient_sock.sendall(push_message.encode('utf-8') + b"\n")
        except Exception as e:
            print(f"Failed to push message to {recipient}: {e}")
    database.update_num_unread(recipient, sender, 1)
    return wrap_message("ACK", [str(msg_id)])

def handle_delete_messages(data):
    """
    Handle a client's request to delete a message.
    Expects data: [msg_id].

    Returns a response with data: [msg_id] on success.
    """
    msg_id = int(data[0])
    recipient, errno = database.delete_message(msg_id)
    if recipient:
        response = wrap_message("DEL_MSG", [str(msg_id)])
        if recipient in active_clients:
            recipient_sock = active_clients[recipient]
            try:
                debug(f"Server: pushing message: {response}")
                recipient_sock.sendall(response.encode('utf-8') + b"\n")
            except Exception as e:
                print(f"Failed to push message to {recipient}: {e}")
        return response
    else:
        return wrap_message("ERROR", [errno])

def handle_delete_account(data):
    """
    Handle a client's request to delete their account.
    Expects data: [username].

    Returns a response with opcode DEL_ACC on success.
    """
    username = data[0]
    errno = database.deactivate_account(username)
    if errno == SUCCESS:
        del active_clients[username]
        return wrap_message("DEL_ACC", [])
    else:
        return wrap_message("ERROR", [errno])

def process_message(message):
    """
    Process an incoming JSON protocol message and dispatch to the appropriate server handler.
    """
    version, opcode, data = parse_message(message)
    if version != PROTOCOL_VERSION:
        return wrap_message("ERROR", [UNSUPPORTED_VERSION])
    if opcode == "CREATE":
        return handle_create(data)
    elif opcode == "LOGIN":
        return handle_login(data)
    elif opcode == "READ":
        return handle_get_chat_history(data)
    elif opcode == "SEND":
        return handle_send_message(data)
    elif opcode == "DEL_MSG":
        return handle_delete_messages(data)
    elif opcode == "DEL_ACC":
        return handle_delete_account(data)
    else:
        return wrap_message("ERROR", [UNKNOWN_COMMAND])
