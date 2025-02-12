"""
Module Name: json_protocol.py
Description: Implements a JSON wire protocol logic on the client side. This ensures that messages are constructed, parsed, and validated consistently with the server's expectations.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import json
from configs.config import *
from client.protocols.custom_protocol import deserialize_chat_history, deserialize_chat_conversations

# Define the protocol version used for JSON messages.
PROTOCOL_VERSION = "2.0"

def wrap_message(opcode, data):
    """
    Wrap the opcode and data into a JSON protocol message prefixed with the protocol version.
    Example:
      "2.0 {"opcode": "LOGIN", "data": ["username", "password"]}\n"
    """
    return f"{PROTOCOL_VERSION} {json.dumps({'opcode': opcode, 'data': data})}\n"

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

def create_registration_request(username, password):
    """
    Construct a registration request message in JSON.
    """
    return wrap_message("CREATE", [username, password])

def create_login_request(username, password):
    """
    Construct a login request message in JSON.
    """
    return wrap_message("LOGIN", [username, password])

def create_delete_account_request(username):
    """
    Construct an account deletion request message in JSON.
    """
    return wrap_message("DEL_ACC", [username])

# def deserialize_chat_conversations(chat_conversations):
#     """
#     Parse a server response for conversations.
    
#     Expected data format (as received in the JSON message):
#       [page_code, client_username, user1, unread1, user2, unread2, ...]
    
#     Returns a list of tuples: [(user1, unread1), (user2, unread2), ...].
#     """
#     convo_list = []
#     # Skip the first two elements (page code and client username)
#     for i in range(2, len(chat_conversations), 2):
#         if i + 1 < len(chat_conversations):
#             user = chat_conversations[i]
#             try:
#                 unread = int(chat_conversations[i + 1])
#             except ValueError:
#                 unread = 0
#             convo_list.append((user, unread))
#     return convo_list

def create_chat_history_request(username, other_user, num_msgs, oldest_msg_id=-1):
    """
    Construct a chat history request message in JSON.
    """
    return wrap_message("READ", [username, other_user, oldest_msg_id, num_msgs])

# def deserialize_chat_history(chat_history):
#     """
#     Parse a server response for chat history.
    
#     Expected data format (as part of the JSON "data" array):
#       [page_code, is_client, num_msgs, msg_id1, num_words1, msg_word1a, msg_word1b, ...,
#        msg_id2, num_words2, msg_word2a, msg_word2b, ...]
    
#     Returns:
#         (num_msgs_read, message_list)
#       where message_list is a list of tuples: [(is_client, msg_id, message), ...].
#     Note: The num_msgs_read value may be zero if not provided.
#     """
#     if not chat_history:
#         return 0, []
#     try:
#         page_code = int(chat_history[0])
#         is_client = int(chat_history[1])
#         num_msgs = int(chat_history[2])
#     except Exception:
#         return 0, []
    
#     message_list = []
#     ind = 3
#     num_msgs_read = 0  # This value could be adjusted if the protocol sends it differently.
#     for _ in range(num_msgs):
#         try:
#             msg_id = int(chat_history[ind])
#             num_words = int(chat_history[ind + 1])
#             ind += 2
#             msg_words = chat_history[ind:ind + num_words]
#             msg = ' '.join(msg_words)
#             message_list.append((is_client, msg_id, msg))
#             ind += num_words
#         except Exception:
#             break
#     return num_msgs_read, message_list

def create_send_message_request(username, other_user, message):
    """
    Construct a send message request in JSON.
    """
    return wrap_message("SEND", [username, other_user, message])

def create_delete_message_request(msg_id):
    """
    Construct a delete message request in JSON.
    """
    return wrap_message("DEL_MSG", [msg_id])

# --- Handler functions (for processing incoming messages) ---

def handle_users(data, Client):
    """Handles a list of users sent from server."""
    page_code = int(data[0])
    username = data[1]
    convo_list = deserialize_chat_conversations(data[2:])
    if page_code == REG_PG:
        Client.register_page.registerSuccessful.emit(username, convo_list)
    elif page_code == LGN_PG:
        Client.login_page.loginSuccessful.emit(username, convo_list)

def handle_incoming_message(data, Client):
    """Handles an incoming message pushed from the server."""
    sender = data[0]
    msg_id = int(data[1])
    message = " ".join(data[2:])

    # Notify the UI to update the chat if in conversation with sender
    if Client.cur_convo == sender:
        Client.messaging_page.displayIncomingMessage(sender, msg_id, message)
        # Send message delivered acknowledgement back to server
        ack = wrap_message("REC_MSG", [msg_id])
        Client.send_request(ack)
    # Update number of unreads displayed on list convos page
    else:
        Client.list_convos_page.num_unreads[sender] += 1
        # Move sender to top of convos
        ind = Client.list_convos_page.convo_order.index(sender)
        del Client.list_convos_page.convo_order[ind]
        Client.list_convos_page.convo_order.insert(0, sender)
        # Refresh the page
        Client.list_convos_page.refresh(0)

def handle_chat_history(data, Client):
    """Handles chat history sent from server."""
    page_code = int(data[0])
    num_msgs_read, chat_history = deserialize_chat_history(data[1:])
    updated_unread = max(0, Client.list_convos_page.num_unreads[Client.cur_convo] - num_msgs_read)
    debug(f"page_code: {page_code}, updated_unread: {updated_unread}")
    if page_code==CONVO_PG:
        Client.list_convos_page.conversationSelected.emit(chat_history, updated_unread)
    else:
        if Client.messaging_page.num_unread > 0:
            Client.messaging_page.updateUnreadCount(updated_unread)
            Client.list_convos_page.updateAfterRead(updated_unread)
        Client.messaging_page.addChatHistory(chat_history)

def handle_ack(data, Client):
    """
    Handles a message acknowledgement.
    
    Expected data format:
      [msg_id]
    """
    msg_id = int(data[0])
    Client.messaging_page.displaySentMessage(msg_id)

def handle_delete(data, Client):
    """
    Handles a delete message response.
    
    Expected data format:
      [msg_id]
    """
    msg_id = int(data[0])
    sender = data[1]
    unread = int(data[2])
    # If in conversation then real time deletion
    if Client.cur_convo and msg_id in Client.messaging_page.message_info:
        Client.messaging_page.removeMessageDisplay(msg_id)
    else:
        if unread:
            # Update number of unreads
            Client.list_convos_page.num_unreads[sender] -= 1
            # Move sender to top of convos
            ind = Client.list_convos_page.convo_order.index(sender)
            del Client.list_convos_page.convo_order[ind]
            Client.list_convos_page.convo_order.insert(0, sender)
            # Refresh the page
            Client.list_convos_page.refresh(0)

def handle_push_user(data, Client):
    """
    Handles a new user pushed from the server.
    
    Expected data format:
      [new_user]
    """
    new_user = data[0]
    Client.list_convos_page.convo_order.append(new_user)
    Client.list_convos_page.num_unreads[new_user] = 0
    Client.list_convos_page.displayConvo(new_user)

def handle_delete_acc(Client):
    """
    Handles an account deletion notification.
    """
    Client.list_convos_page.successfulAccountDel()

def handle_error(data, Client):
    """
    Handles an error message.
    
    Expected data format:
      [errno]
    """
    try:
        errno = int(data[0])
    except Exception:
        errno = -1
    if errno in (1, 2, 3, 8):
        Client.login_page.displayLoginErrors(errno)

def process_message(message, Client):
    """
    Process an incoming JSON protocol message and dispatch to the appropriate handler.
    """
    version, opcode, data = parse_message(message)
    if version != PROTOCOL_VERSION:
        # If the version is unsupported, return an error message.
        error_msg = wrap_message("ERROR", [UNSUPPORTED_VERSION])
        return error_msg

    if opcode == "USERS":
        handle_users(data, Client)
    elif opcode == "MSGS":
        handle_chat_history(data, Client)
    elif opcode == "ACK":
        handle_ack(data, Client)
    elif opcode == "DEL_MSG":
        handle_delete(data, Client)
    elif opcode == "PUSH_MSG":
        handle_incoming_message(data, Client)
    elif opcode == "PUSH_USER":
        handle_push_user(data, Client)
    elif opcode == "DEL_ACC":
        handle_delete_acc(Client)
    elif opcode == "ERROR":
        handle_error(data, Client)
    else:
        print(f"2.0 ERROR {UNKNOWN_COMMAND}")
