"""
Module Name: gRPC.py
Description: The gRPC server implementation for handling client requests.
Author: Henry Huang and Bridget Ma
Date: 2024-2-17
"""

from .. import database
import server.utils as utils
from configs.config import *

import chat_service_pb2
import chat_service_pb2_grpc

temp_updates = [f"New Message {i}!" for i in range(10)]

# -----------------------------
# gRPC server setup
# -----------------------------
class MyChatService(chat_service_pb2_grpc.ChatServiceServicer):
    
    def Register(self, request, context):
        success, errno = database.register_account(request.username, request.password)
        
        if success:
            # TODO: Push USER message to all active clients
            
            user_unreads = [
                chat_service_pb2.UserUnread(username=user, unread_count=unread)
                for user, unread in database.get_conversations(request.username)
            ]

            debug(f"User {request.username} registered successfully.")
            utils.add_active_client(request.username, "active")
            
            return chat_service_pb2.LoginResponse(
                errno=SUCCESS,
                page_code=REG_PG,
                client_username=request.username,
                user_unreads=user_unreads)
        else:
            debug(f"User {request.username} failed to registers: {errno}")
            return chat_service_pb2.LoginResponse(errno=errno)
        
    def Login(self, request, context):        
        success, errno = database.verify_login(request.username, request.password)
        
        # Check for active client
        with utils.active_clients_lock:
            if request.username in utils.active_clients:
                return chat_service_pb2.LoginResponse(errno=USER_LOGGED_ON)
        
        if success:
            user_unreads = [
                chat_service_pb2.UserUnread(username=user, unread_count=unread)
                for user, unread in database.get_conversations(request.username)
            ]

            debug(f"User {request.username} logged in successfully.")
            utils.add_active_client(request.username, "active")
            
            return chat_service_pb2.LoginResponse(
                errno=SUCCESS,
                page_code=LGN_PG,
                client_username=request.username,
                user_unreads=user_unreads)
        else:
            debug(f"User {request.username} failed to log in: {errno}")
            return chat_service_pb2.LoginResponse(errno=errno)
        
    def GetChatHistory(self, request, context):
        """
        Fetch a conversation's history between the requesting user and another user.
        The request includes:
          - username: The requesting user's username.
          - other_user: The other user in the conversation.
          - num_msgs: The number of messages requested.
          - oldest_msg_id: Starting message id (-1 indicates to fetch the most recent messages).
        """
        username = request.username
        other_user = request.other_user
        num_msgs = request.num_msgs
        oldest_msg_id = request.oldest_msg_id

        # Determine the page code based on oldest_msg_id:
        # If oldest_msg_id != -1, assume this is an ongoing conversation (MSG_PG),
        # otherwise, it is a new conversation load (CONVO_PG).
        page_code = MSG_PG if oldest_msg_id != -1 else CONVO_PG

        # Retrieve unread count and chat history from your database.
        # Assume database.get_recent_messages returns a tuple: (unread_count, history)
        # where history is a list of dictionaries like:
        # {"sender": <username>, "id": <msg_id>, "message": <text>}
        unread_count, history = database.get_recent_messages(username, other_user, oldest_msg_id, num_msgs)

        # Build the list of Message objects for the response.
        chat_messages = []
        for message in history:
            msg = chat_service_pb2.Message(
                sender=message["sender"],
                msg_id=message["id"],
                text=message["message"]
            )
            chat_messages.append(msg)

        debug(f"{username} read {unread_count} unread messages from {other_user}")

        # Construct and return the ChatHistoryResponse.
        return chat_service_pb2.ChatHistoryResponse(
            errno=SUCCESS,
            page_code=page_code,
            unread_count=unread_count,
            chat_history=chat_messages
        )
        
    def SendMessage(self, request, context):
        """
        Send a message from the requesting user to another user.
        The request includes:
          - sender: The requesting user's username.
          - recipient: The other user in the conversation.
          - text: The message text sent.
        """
        sender = request.sender
        recipient = request.recipient
        message = request.text

        # check if recipient has deactivated their account
        if database.verify_valid_recipient(recipient):
            msg_id = database.store_message(sender, recipient, message)
        
        # TODO: Push message to recipient if they are online
        # push_message = wrap_message("PUSH_MSG", [sender, str(msg_id), message])
        
        # with utils.active_clients_lock:
        #     if recipient in utils.active_clients:
        #         recipient_sock = utils.active_clients[recipient]
        #         try:
        #             debug(f"Server: pushing message: {push_message}")
        #             recipient_sock.sendall(push_message.encode('utf-8') + b"\n")
        #         except Exception as e:
        #             print(f"Failed to push message to {recipient}: {e}")
        
        return chat_service_pb2.SendMessageResponse(errno=SUCCESS, msg_id=msg_id)
    
    def DeleteMessage(self, request, context):
        """
        Handles a client's request to delete a message.
        Expects data: [msg_id].

        Returns a response with data: [msg_id] on success.
        """
        
        msg_id = request.msg_id
        recipient, sender, unread, errno = database.delete_message(msg_id)
        if recipient:
            response = chat_service_pb2.DeleteMessageResponse(
                errno=SUCCESS, 
                sender=sender,
                msg_id=msg_id, 
                read_status=unread
            )
            
            # TODO: Push live message to recipient if they are online
            # with utils.active_clients_lock:
            #     if recipient in utils.active_clients:
            #         recipient_sock = utils.active_clients[recipient]
            #         try:
            #             debug(f"Server: pushing message: {response}")
            #             recipient_sock.sendall(response.encode('utf-8') + b"\n")
            #         except Exception as e:
            #             print(f"Failed to push message to {recipient}: {e}")
            return response
        else:
            return chat_service_pb2.DeleteMessageResponse(errno=errno)
        
    def UpdateStream(self, request_iterator, context):
        """
        Bi-directional stream where the client sends subscription/heartbeat messages,
        and the server yields live update messages. When the client disconnects,
        the context will be canceled.
        """
        # Optionally, grab the first message to know which user this stream is for.
        try:
            first_request = next(request_iterator)
        except StopIteration:
            return  # No messages received; end stream.

        username = first_request.username
        # (Register the client’s live update stream if necessary.)
        print(f"User {username} subscribed for live updates.")

        try:
            # Main streaming loop.
            while context.is_active():
                # Here you would check for new updates for the client.
                # For example, checking a message queue, database, etc.
                update = self._get_update_for_user(username)
                if update:
                    yield chat_service_pb2.LiveUpdate(update_message=update)
        except Exception as e:
            print(f"Exception in UpdateStream for {username}: {e}")
        finally:
            # Clean up when client disconnects.
            self._cleanup_client_stream(username)

    def _get_update_for_user(self, username):
        """
        Placeholder function: Check if there is a new update for the given user.
        Return the update message string if available, otherwise return None.
        """
        # Replace with your actual update-checking logic.
        if temp_updates:
            return temp_updates.pop()
        return None

    def _cleanup_client_stream(self, username):
        """
        Remove the client from any active streaming lists, etc.
        """
        utils.remove_active_client(username)
