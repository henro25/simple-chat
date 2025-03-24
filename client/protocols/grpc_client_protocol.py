"""
Module Name: grpc_client_protocol.py
Description: Connects the gRPC logic on the client side. This ensures that messages are handled accordingly with the server's expectations and UI is updated.
Author: Henry Huang and Bridget Ma
Date: 2024-2-17 (updated for replication)
"""

import configs.config as config
import grpc
import chat_service_pb2
import chat_service_pb2_grpc

# ------------------------
# Handle gRPC Responses and Live Updates
# ------------------------

def handle_error(Client, response):
    """
    Handles an error message.
    """
    try:
        errno = int(response.errno)
    except Exception:
        errno = -1
    if errno in (1, 2, 3, 8):
        Client.login_page.displayLoginErrors(errno)

def handle_login_response(Client, response):
    """Handles the user Login and Registration responses."""
    page_code = response.page_code
    Client.username = response.client_username

    convo_list = [(user.username, user.unread_count) for user in response.user_unreads]
    
    # Start the live updates thread if not already started.
    Client.start_live_updates()

    if page_code == config.REG_PG:
        Client.register_page.registerSuccessful.emit(Client.username, convo_list)
    elif page_code == config.LGN_PG:
        Client.login_page.loginSuccessful.emit(Client.username, convo_list)

def handle_chat_history(Client, response):
    """Handles the chat history response."""
    page_code = response.page_code
    num_unreads = response.unread_count

    chat_history = [(msg.sender, msg.msg_id, msg.text) for msg in response.chat_history]
    config.debug(f"page_code: {page_code}, num_unreads: {num_unreads}")
    if page_code == config.CONVO_PG:
        Client.list_convos_page.conversationSelected.emit(chat_history, num_unreads)
    else:
        if Client.messaging_page.num_unread > 0:
            Client.messaging_page.updateUnreadCount(num_unreads)
            Client.listConvosPage.updateAfterRead(num_unreads)
        Client.messaging_page.addChatHistory(chat_history)
        
def handle_ack(Client, response):
    """Handles a message acknowledgement."""
    Client.messaging_page.displaySentMessage(response.msg_id)
    
def handle_delete_msg(Client, response):
    """
    Handles a delete message response.
    """
    msg_id = response.msg_id
    sender = response.sender
    unread = response.read_status
    
    if Client.cur_convo and msg_id in Client.messaging_page.message_info:
        Client.messaging_page.removeMessageDisplay(msg_id)
    else:
        if unread:
            Client.listConvosPage.num_unreads[sender] -= 1
            ind = Client.listConvosPage.convo_order.index(sender)
            del Client.listConvosPage.convo_order[ind]
            Client.listConvosPage.convo_order.insert(0, sender)
            Client.listConvosPage.refresh(0)

def handle_delete_acc(Client):
    """
    Handles an account deletion notification.
    """
    Client.listConvosPage.successfulAccountDel()
    
def handle_incoming_message(Client, push_msg):
    """Handles an incoming message pushed from the server."""
    sender = push_msg.sender
    msg_id = push_msg.msg_id
    message = push_msg.text

    config.debug(f"Received push message from {sender} (id {msg_id}): {message}")

    if Client.cur_convo == sender:
        Client.messaging_page.displayIncomingMessage(sender, msg_id, message)
        Client.stub.AckPushMessage(chat_service_pb2.AckPushMessageRequest(msg_id=msg_id))
    else:
        Client.listConvosPage.num_unreads[sender] += 1
        ind = Client.listConvosPage.convo_order.index(sender)
        del Client.listConvosPage.convo_order[ind]
        Client.listConvosPage.convo_order.insert(0, sender)
        Client.listConvosPage.refresh(0)

def handle_push_user(Client, push_user):
    """
    Handles a new user pushed from the server.
    """
    new_user = push_user.username
    Client.listConvosPage.convo_order.append(new_user)
    Client.listConvosPage.num_unreads[new_user] = 0
    Client.listConvosPage.displayConvo(new_user)

def handle_server_list_update(Client, push_server_list_update):
    """
    Handles a live update containing an updated server list.
    The update contains a repeated ServerInfo field.
    """
    config.debug("Received server list update.")
    new_server_list = [(s.ip, s.port) for s in push_server_list_update.server_list]
    Client.server_list = new_server_list  # Save the updated list in the client.
    config.debug(f"Updated server list: {Client.server_list}")

    # Optionally, if the current gRPC channel is no longer valid,
    # attempt to reconnect using an alternate server.
    try:
        # Test the current stub with a HealthCheck.
        response = Client.stub.HealthCheck(chat_service_pb2.HealthCheckRequest(), timeout=2)
        if response.status != "OK":
            raise Exception("HealthCheck failed")
    except Exception as e:
        config.debug("Current primary is unresponsive; reconnecting to an alternative server.")
        reconnect_to_alternative(Client)

def reconnect_to_alternative(Client):
    """
    Chooses a new server from the updated server list and re-establishes the gRPC channel and stub.
    """
    for (ip, port) in Client.server_list:
        # Skip the current server if it's the one we already tried.
        if f"{ip}:{port + 1}" == Client.current_grpc_endpoint:
            continue
        try:
            new_channel = grpc.insecure_channel(f"{ip}:{port + 1}")
            new_stub = chat_service_pb2_grpc.ChatServiceStub(new_channel)
            # Perform a quick HealthCheck.
            response = new_stub.HealthCheck(chat_service_pb2.HealthCheckRequest(), timeout=2)
            if response.status == "OK":
                Client.channel = new_channel
                Client.stub = new_stub
                Client.current_grpc_endpoint = f"{ip}:{port + 1}"
                config.debug(f"Switched to new server at {Client.current_grpc_endpoint}")
                return
        except Exception as e:
            config.debug(f"Failed to connect to alternative server {ip}:{port + 1}: {e}")
    config.debug("No alternative server available. Please try again later.")

def send_grpc_request(Client, request):
    """
    Sends the given gRPC request and handles the response.
    If the current channel fails, it attempts to reconnect using the alternative servers.
    """
    try:
        if isinstance(request, chat_service_pb2.RegisterRequest):
            response = Client.stub.Register(request)
        elif isinstance(request, chat_service_pb2.LoginRequest):
            response = Client.stub.Login(request)
        elif isinstance(request, chat_service_pb2.ChatHistoryRequest):
            response = Client.stub.GetChatHistory(request)
        elif isinstance(request, chat_service_pb2.SendMessageRequest):
            response = Client.stub.SendMessage(request)
        elif isinstance(request, chat_service_pb2.DeleteMessageRequest):
            response = Client.stub.DeleteMessage(request)
        elif isinstance(request, chat_service_pb2.DeleteAccountRequest):
            response = Client.stub.DeleteAccount(request)
        else:
            config.debug("Unknown gRPC request type.")
            return
        
        config.debug(f"gRPC response: \n{response}")
        
        if response.errno != config.SUCCESS:
            handle_error(Client, response)
            return
        
        if isinstance(response, chat_service_pb2.LoginResponse):
            handle_login_response(Client, response)
        elif isinstance(response, chat_service_pb2.ChatHistoryResponse):
            handle_chat_history(Client, response)
        elif isinstance(response, chat_service_pb2.SendMessageResponse):
            handle_ack(Client, response)
        elif isinstance(response, chat_service_pb2.DeleteMessageResponse):
            handle_delete_msg(Client, response)
        elif isinstance(response, chat_service_pb2.DeleteAccountResponse):
            handle_delete_acc(Client)
    except grpc.RpcError as rpc_error:
        config.debug(f"gRPC request failed: {rpc_error}")
        reconnect_to_alternative(Client)

def process_live_update(Client, update):
    """Processes live updates from the server."""
    if isinstance(update, chat_service_pb2.LiveUpdate):
        update_type = update.WhichOneof("update")
        config.debug(f"Received live update: {update_type}")
        
        if update_type == "push_message":
            handle_incoming_message(Client, update.push_message)
        elif update_type == "push_user":
            handle_push_user(Client, update.push_user)
        elif update_type == "push_delete_msg":
            handle_delete_msg(Client, update.push_delete_msg)
        elif update_type == "push_server_list_update":
            handle_server_list_update(Client, update.push_server_list_update)
        else:
            config.debug("Received unknown live update type.")
    else:
        config.debug("Invalid live update format.")
