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
