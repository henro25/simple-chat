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
# Handle gPRC Requests
# ------------------------
def send_login_request(Client, request):
    """
    Handle the login request and update the UI accordingly.
    """
    # gRPC call
    return Client.stub.Login(request)

# ------------------------
# Handle gPRC Responses
# ------------------------
def handle_login_response(Client, response):
    # Access the structured fields directly.
    page_code = response.page_code
    client_username = response.client_username

    # Build a conversation list (or user list) from the repeated UserUnread field.
    convo_list = [(user.username, user.unread_count) for user in response.user_unreads]

    # Use page code to update the UI or signal success.
    if page_code == config.REG_PG:
        Client.register_page.registerSuccessful.emit(client_username, convo_list)
    elif page_code == config.LGN_PG:
        Client.login_page.loginSuccessful.emit(client_username, convo_list)

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

def send_grpc_request(Client, request):
    # Send the request
    if isinstance(request, chat_service_pb2.LoginRequest):
        response = send_login_request(Client, request)
        
    config.debug(f"gRPC response: \n{response}")
    
    # Check for errors (all responses come with an errno)
    if response.errno != config.SUCCESS:
        handle_error(Client, response)
        return
    
    # Handle the response
    if isinstance(response, chat_service_pb2.LoginResponse):
        handle_login_response(Client, response)
