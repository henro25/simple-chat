"""
Module Name: custom_protocol.py
Description: Implements the custom wire protocol logic on the client side. This ensures that messages are constructed, parsed, and validated consistently with the server's expectations.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

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

def deserialize_chat_conversations(chat_conversations):
    """
    Parse a server response of the form:
      "1.0 USERS user1 unread1 user2 unread2 ..."
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

def create_chat_history_request(username, other_user):
    """
    Construct a chat history request message.
    """
    return f"1.0 READ {username} {other_user}\n"

def deserialize_chat_history(chat_history, username, other_user):
    """
    Parse a server response of the form:
      `1.0 MSGS [1 if user who sent the ealiest message is same as the user 
      receiving this history else 0] [num msgs] [msg ID (if 1), num words, msg1] 
      [msg ID (if 1), num words, msg2] ...`
    into a list of tuples: [(username, msg ID, message), (username, msg ID, message), ...].
    """
    if len(chat_history)==0:
        return []
    message_list = []
    is_client = int(chat_history[0])
    ind = 1
    while ind < len(chat_history):
        try:
            num_messages = int(chat_history[ind])
            ind += 1
        except ValueError:
            num_messages = 0
        while num_messages > 0 and ind < len(chat_history):
            try:
                id = int(chat_history[ind])
                num_words = int(chat_history[ind+1])
                ind += 2
                user = username if is_client else other_user
                msg = ' '.join(chat_history[ind:ind+num_words])
                message_list.append((user, id, msg))
                ind += num_words
            except ValueError:
                num_messages = 0
            num_messages -= 1
        is_client = abs(1-is_client)
    return message_list

def create_send_message_request(username, other_user, message):
    """
    Construct a chat history request message.
    """
    return f"1.0 SEND {username} {other_user} {message}\n"

def deserialize_message_acknowledgement(ack):
    """
    Parse a server response of the form:
      `1.0 ACK [msg ID]`
    into a msg ID
    """
    return int(ack[0])

def create_delete_message_request(msg_id):
    """
    Construct a delete message request message.
    """
    return f"1.0 DEL_MSG {msg_id}\n"