"""
Module Name: grpc_protocol.py
Description: Connects the gRPC logic on the client side. This ensures that messages are handled accordingly with the server's expectations and UI is updated.
Author: Henry Huang and Bridget Ma
Date: 2024-2-17
"""

import configs.config as config

# gRPC import
import chat_service_pb2

# ------------------------
# Handle gPRC Responses
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
    """ Handles the user Login and Registration responses. """
    # Access the structured fields directly.
    page_code = response.page_code
    Client.username = response.client_username

    # Build a conversation list (or user list) from the repeated UserUnread field.
    convo_list = [(user.username, user.unread_count) for user in response.user_unreads]
    
    # Start the live updates thread
    Client.start_live_updates()

    # Use page code to update the UI or signal success.
    if page_code == config.REG_PG:
        Client.register_page.registerSuccessful.emit(Client.username, convo_list)
    elif page_code == config.LGN_PG:
        Client.login_page.loginSuccessful.emit(Client.username, convo_list)

def handle_chat_history(Client, response):
    """ Handles the chat history response. """
    page_code = response.page_code
    num_unreads = response.unread_count

    # Build a chat history list from the repeated ChatMessage field.
    chat_history = [(msg.sender == Client.username, msg.msg_id, msg.text) for msg in response.chat_history]
    print("chat_history:", chat_history)

    updated_unread = max(0, Client.list_convos_page.num_unreads[Client.cur_convo] - num_unreads)
    config.debug(f"page_code: {page_code}, updated_unread: {updated_unread}")
    if page_code==config.CONVO_PG:
        Client.list_convos_page.conversationSelected.emit(chat_history, updated_unread)
    else:
        if Client.messaging_page.num_unread > 0:
            Client.messaging_page.updateUnreadCount(updated_unread)
            Client.list_convos_page.updateAfterRead(updated_unread)
        Client.messaging_page.addChatHistory(chat_history)
        
def handle_ack(Client, response):
    """ Handles a message acknowledgement. """
    Client.messaging_page.displaySentMessage(response.msg_id)
    
def handle_delete_msg(Client, response):
    """
    Handles a delete message response.
    """
    msg_id = response.msg_id
    sender = response.sender
    unread = response.read_status
    
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

def handle_delete_acc(Client):
    """
    Handles an account deletion notification.
    """
    Client.list_convos_page.successfulAccountDel()

def send_grpc_request(Client, request):
    # Send the request
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
        
    config.debug(f"gRPC response: \n{response}")
    
    # Check for errors (all responses come with an errno)
    if response.errno != config.SUCCESS:
        handle_error(Client, response)
        return
    
    # Handle the response
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
