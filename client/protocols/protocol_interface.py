"""
Module Name: protocol_interface.py
Description: Redirects protocol function calls to either the custom protocol or the JSON protocol
             based on the CUR_PROTO_VERSION value. If the current protocol version is not supported, an error message is returned.
Author: Henry Huang and Bridget Ma
Date: 2024-2-12
"""

import configs.config as config
import client.protocols.custom_protocol as custom_protocol
import client.protocols.json_protocol as json_protocol

# gRPC import
import chat_service_pb2

def unsupported_error():
    return f"{config.CUR_PROTO_VERSION} ERROR {config.UNSUPPORTED_VERSION}"

def parse_message(message):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.parse_message(message)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.parse_message(message)
    else:
        return unsupported_error()

def create_registration_request(username, password):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.create_registration_request(username, password)
    elif config.CUR_PROTO_VERSION == "2.0":
        # For JSON, we assume that wrapping a message with opcode "CREATE" is equivalent.
        return json_protocol.create_registration_request(username, password)
    elif config.CUR_PROTO_VERSION == "3.0":
        return chat_service_pb2.RegisterRequest(username=username, password=password)
    else:
        return unsupported_error()

def create_login_request(username, password):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.create_login_request(username, password)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.create_login_request(username, password)
    elif config.CUR_PROTO_VERSION == "3.0":
        return chat_service_pb2.LoginRequest(username=username, password=password)
    else:
        return unsupported_error()

def create_delete_account_request(username):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.create_delete_account_request(username)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.create_delete_account_request(username)
    else:
        return unsupported_error()

def deserialize_chat_conversations(chat_conversations):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.deserialize_chat_conversations(chat_conversations)
    elif config.CUR_PROTO_VERSION == "2.0":
        # Assuming the JSON protocol provides a similar function.
        return json_protocol.deserialize_chat_conversations(chat_conversations)
    else:
        return unsupported_error()

def create_chat_history_request(username, other_user, num_msgs, oldest_msg_id=-1):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.create_chat_history_request(username, other_user, num_msgs, oldest_msg_id)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.create_chat_history_request(username, other_user, num_msgs, oldest_msg_id)
    else:
        return unsupported_error()

def deserialize_chat_history(chat_history):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.deserialize_chat_history(chat_history)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.deserialize_chat_history(chat_history)
    else:
        return unsupported_error()

def create_send_message_request(username, other_user, message):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.create_send_message_request(username, other_user, message)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.create_send_message_request(username, other_user, message)
    else:
        return unsupported_error()

def create_delete_message_request(msg_id):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.create_delete_message_request(msg_id)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.create_delete_message_request(msg_id)
    else:
        return unsupported_error()

def handle_users(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_users(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_users(args, Client)
    else:
        return unsupported_error()

def handle_incoming_message(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_incoming_message(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_incoming_message(args, Client)
    else:
        return unsupported_error()

def handle_chat_history(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_chat_history(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_chat_history(args, Client)
    else:
        return unsupported_error()

def handle_ack(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_ack(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_ack(args, Client)
    else:
        return unsupported_error()

def handle_delete(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_delete(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_delete(args, Client)
    else:
        return unsupported_error()

def handle_push_user(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_push_user(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_push_user(args, Client)
    else:
        return unsupported_error()

def handle_delete_acc(Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_delete_acc(Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_delete_acc(Client)
    else:
        return unsupported_error()

def handle_error(args, Client):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.handle_error(args, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.handle_error(args, Client)
    else:
        return unsupported_error()

def process_message(message, Client=None):
    if config.CUR_PROTO_VERSION == "1.0":
        return custom_protocol.process_message(message, Client)
    elif config.CUR_PROTO_VERSION == "2.0":
        return json_protocol.process_message(message, Client)
    else:
        return unsupported_error()
