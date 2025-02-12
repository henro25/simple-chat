"""
Module Name: custom_protocol.py
Description: Implements the custom wire protocol logic on the client side. This ensures that messages are constructed, parsed, and validated consistently with the server's expectations.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

from configs.config import *
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QScrollArea, QSizePolicy, QMessageBox, QApplication
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, pyqtSignal

def parse_message(message):
    """
    Parse a protocol message into version, command, and arguments.
    
    Expected message examples:
      - "1.0 ERROR [errno]"
      - "1.0 PUSH_MSG [recipient] [msg]"
    
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

def create_registration_request(username, password):
    """
    Construct a registration request message.
    """
    return f"1.0 CREATE {username} {password}\n"

def create_login_request(username, password):
    """
    Construct a login request message.
    """
    return f"1.0 LOGIN {username} {password}\n"

def create_delete_account_request(username):
    """
    Construct a account deletion request message.
    """
    return f"1.0 DEL_ACC {username}\n"

def deserialize_chat_conversations(chat_conversations):
    """
    Parse a server response of the form:
      "1.0 USERS page_code client_username user1 unread1 user2 unread2 ..."
    into a list of tuples: [(user1, num_unread1), (user2, num_unread2), ...].
    """
    convo_list = []
    for i in range(0, len(chat_conversations), 2):
        if i+1 < len(chat_conversations):
            user = chat_conversations[i]
            try:
                unread = int(chat_conversations[i+1])
            except ValueError:
                unread = 0
            convo_list.append((user, unread))
    return convo_list

def create_chat_history_request(username, other_user, num_msgs, oldest_msg_id=-1):
    """
    Construct a chat history request message.
    """
    return f"1.0 READ {username} {other_user} {oldest_msg_id} {num_msgs}\n"

def deserialize_chat_history(chat_history):
    """
    Parse a server response of the form:
      `1.0 MSGS [page code] [1 if user who sent the ealiest message is same as the user 
      receiving this history else 0] [num msgs] [msg ID (if 1), num words, msg1] 
      [msg ID (if 1), num words, msg2] ...`
    into a list of tuples: [(username, msg ID, message), (username, msg ID, message), ...].
    """
    if not chat_history:
        return 0, []
    message_list = []
    is_client = int(chat_history[0])
    ind = 1
    num_msgs_read = 0
    while ind < len(chat_history):
        try:
            num_messages = int(chat_history[ind])
            ind += 1
            # update the number of messages read from the other user; used to update num_unread
            if not is_client:
                num_msgs_read += num_messages
        except ValueError:
            num_messages = 0
        while num_messages > 0 and ind < len(chat_history):
            try:
                id = int(chat_history[ind])
                num_words = int(chat_history[ind+1])
                ind += 2
                msg = ' '.join(chat_history[ind:ind+num_words])
                message_list.append((is_client, id, msg))
                ind += num_words
            except ValueError:
                num_messages = 0
            num_messages -= 1
        is_client = abs(1-is_client)
    
    return num_msgs_read, message_list

def create_send_message_request(username, other_user, message):
    """
    Construct a chat history request message.
    """
    return f"1.0 SEND {username} {other_user} {message}\n"

def create_delete_message_request(msg_id):
    """
    Construct a delete message request message.
    """
    return f"1.0 DEL_MSG {msg_id}\n"

def handle_users(args, Client):
    """Handles a list of users sent from server."""
    page_code = int(args[0])
    username = args[1]
    convo_list = deserialize_chat_conversations(args[2:])
    if page_code == REG_PG:
        Client.register_page.registerSuccessful.emit(username, convo_list)
    elif page_code == LGN_PG:
        Client.login_page.loginSuccessful.emit(username, convo_list)

def handle_incoming_message(args, Client):
    """Handles an incoming message pushed from the server."""
    sender = args[0]
    msg_id = int(args[1])
    message = " ".join(args[2:])

    # Notify the UI to update the chat if in conversation with sender
    if Client.cur_convo == sender:
        Client.messaging_page.displayIncomingMessage(sender, msg_id, message)
        # Send message delivered acknowledgement back to server
        ack = f"1.0 REC_MSG {msg_id}\n"
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

def handle_chat_history(args, Client):
    """Handles chat history sent from server."""
    page_code = int(args[0])
    num_msgs_read, chat_history = deserialize_chat_history(args[1:])
    updated_unread = max(0, Client.list_convos_page.num_unreads[Client.cur_convo] - num_msgs_read)
    if page_code==CONVO_PG:
        Client.list_convos_page.conversationSelected.emit(chat_history, updated_unread)
    else:
        if Client.messaging_page.num_unread > 0:
            Client.messaging_page.updateUnreadCount(updated_unread)
            Client.list_convos_page.updateAfterRead(updated_unread)
        Client.messaging_page.addChatHistory(chat_history)

def handle_ack(args, Client):
    """Handles message sent acknowledgement sent from server."""
    msg_id = int(args[0])
    Client.messaging_page.displaySentMessage(msg_id)

def handle_delete(args, Client):
    msg_id = int(args[0])
    sender = args[1]
    unread = int(args[2])
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

def handle_push_user(args, Client):
    new_user = args[0]
    Client.list_convos_page.convo_order.append(new_user)
    Client.list_convos_page.displayConvo(new_user)

def handle_delete_acc(Client):
    Client.list_convos_page.successfulAccountDel()

def handle_error(args, Client):
    errno = int(args[0])
    if errno == 1 or errno == 2 or errno == 3 or errno == 8:
        Client.login_page.displayLoginErrors(errno)

def process_message(message, Client):
    """
    Process a message string according to our custom protocol.
    Dispatches to the appropriate handler.
    """
    version, command, args = parse_message(message)
    if version not in SUPPORTED_VERSIONS:
        return f"1.0 ERROR {UNSUPPORTED_VERSION}"
    
    if command == "USERS":
        handle_users(args, Client)
    elif command == "MSGS":
        handle_chat_history(args, Client)
    elif command == "ACK":
        handle_ack(args, Client)
    elif command == "DEL_MSG":
        handle_delete(args, Client)
    elif command == "PUSH_MSG":
        handle_incoming_message(args, Client)
    elif command == "PUSH_USER":
        handle_push_user(args, Client)
    elif command == "DEL_ACC":
        handle_delete_acc(Client)
    elif command == "ERROR":
        handle_error(args, Client)
    else:
        print(f"1.0 ERROR {UNKNOWN_COMMAND}")