"""
Module Name: gRPC.py
Description: The gRPC server implementation for handling client requests.
Author: Henry Huang and Bridget Ma
Date: 2024-2-17
"""

from .. import database
from server.utils import active_clients
from configs.config import *

import chat_service_pb2
import chat_service_pb2_grpc

# -----------------------------
# gRPC server setup
# -----------------------------
class MyChatService(chat_service_pb2_grpc.ChatServiceServicer):
    def Login(self, request, context):
        
        success, errno = database.verify_login(request.username, request.password)
        
        # Check for active client
        if request.username in active_clients:
            return chat_service_pb2.LoginResponse(errno=USER_LOGGED_ON)
        
        if success:
            user_unreads = [
                chat_service_pb2.UserUnread(username=user, unread_count=unread)
                for user, unread in database.get_conversations(request.username)
            ]

            debug(f"User {request.username} logged in successfully.")
            active_clients[request.username] = "active"
            return chat_service_pb2.LoginResponse(
                errno=SUCCESS,
                page_code=LGN_PG,
                client_username=request.username,
                user_unreads=user_unreads)
        else:
            debug(f"User {request.username} failed to log in: {errno}")
            return chat_service_pb2.LoginResponse(
                errno=errno,
                page_code=0,
                client_username=request.username,
                user_unreads=[]
            )
