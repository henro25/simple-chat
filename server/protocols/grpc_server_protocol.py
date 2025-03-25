"""
Module Name: gRPC.py
Description: The gRPC server implementation for handling client requests.
Author: Henry Huang and Bridget Ma
Date: 2024-2-17 (updated for full replication)
"""

import socket
from .. import database
import server.utils as utils
from configs.config import *

import chat_service_pb2
import chat_service_pb2_grpc

class MyChatService(chat_service_pb2_grpc.ChatServiceServicer):
    
    def Register(self, request, context):
        success, errno = database.register_account(request.username, request.password)
        if success:
            with utils.rpc_send_queue_lock:
                utils.debug(f"Active RPC clients: {list(utils.rpc_send_queue.keys())}")
                for recipient in utils.rpc_send_queue.keys():
                    utils.debug(f"Server: appending push_user message to {recipient} via gRPC")
                    utils.rpc_send_queue[recipient].append(
                        chat_service_pb2.PushUser(
                            errno=SUCCESS,
                            username=request.username,
                        )
                    )
            user_unreads = [
                chat_service_pb2.UserUnread(username=user, unread_count=unread)
                for user, unread in database.get_conversations(request.username)
            ]
            utils.debug(f"User {request.username} registered successfully.")
            client_sock = utils.get_passive_client((request.ip_address, request.port))
            utils.add_active_client(request.username, client_sock)
            utils.add_rpc_send_queue_user(request.username)
            # Replicate registration operation.
            is_primary, _ = utils.get_replication_config()
            if is_primary:
                replicate_to_backups({
                    "sender": request.username,
                    "recipient": "",
                    "text": request.password,  # or the hashed password
                    "operation": "REGISTER"
                })
            return chat_service_pb2.LoginResponse(
                errno=SUCCESS,
                page_code=REG_PG,
                client_username=request.username,
                user_unreads=user_unreads)
        else:
            utils.debug(f"User {request.username} failed to register: {errno}")
            return chat_service_pb2.LoginResponse(errno=errno)
    
    def Login(self, request, context):
        success, errno = database.verify_login(request.username, request.password)
        with utils.rpc_send_queue_lock:
            if request.username in utils.rpc_send_queue:
                return chat_service_pb2.LoginResponse(errno=USER_LOGGED_ON)
        if success:
            user_unreads = [
                chat_service_pb2.UserUnread(username=user, unread_count=unread)
                for user, unread in database.get_conversations(request.username)
            ]
            utils.debug(f"User {request.username} logged in successfully.")
            client_sock = utils.get_passive_client((request.ip_address, request.port))
            utils.add_active_client(request.username, client_sock)
            utils.add_rpc_send_queue_user(request.username)
            # Replicate login operation so that backups know the user is active.
            is_primary, _ = utils.get_replication_config()
            if is_primary:
                replicate_to_backups({
                    "sender": request.username,
                    "recipient": "",
                    "text": f"{request.username},{request.ip_address},{request.port}",
                    "operation": "LOGIN"
                })
            return chat_service_pb2.LoginResponse(
                errno=SUCCESS,
                page_code=LGN_PG,
                client_username=request.username,
                user_unreads=user_unreads)
        else:
            utils.debug(f"User {request.username} failed to log in: {errno}")
            return chat_service_pb2.LoginResponse(errno=errno)
        
    def GetChatHistory(self, request, context):
        username = request.username
        other_user = request.other_user
        num_msgs = request.num_msgs
        oldest_msg_id = request.oldest_msg_id
        page_code = MSG_PG if oldest_msg_id != -1 else CONVO_PG
        unread_count, history = database.get_recent_messages(username, other_user, oldest_msg_id, num_msgs)
        chat_messages = []
        for message in history:
            msg = chat_service_pb2.Message(
                sender=message["sender"],
                msg_id=message["id"],
                text=message["message"]
            )
            chat_messages.append(msg)
        utils.debug(f"{username} read {unread_count} unread messages from {other_user}")
        read_ids = [message["id"] for message in history]
        # Replicate chat history operation if it changed read status.
        if unread_count > 0 and read_ids:
            is_primary, _ = utils.get_replication_config()
            if is_primary:
                # Here, we simply replicate that the user has read messages;
                # you could also send specific message IDs if your database supports that.
                ids_str = ",".join(str(mid) for mid in read_ids)
                replicate_to_backups({
                    "sender": username,
                    "recipient": other_user,
                    "text": ids_str,
                    "operation": "READ_HISTORY"
                })
        return chat_service_pb2.ChatHistoryResponse(
            errno=SUCCESS,
            page_code=page_code,
            unread_count=unread_count,
            chat_history=chat_messages
        )
        
    def SendMessage(self, request, context):
        sender = request.sender
        recipient = request.recipient
        message = request.text
        msg_id = -1
        if database.verify_valid_recipient(recipient) == 1:
            msg_id = database.store_message(sender, recipient, message)
            is_primary, _ = utils.get_replication_config()
            if is_primary:
                replicate_to_backups({
                    "sender": sender,
                    "recipient": recipient,
                    "text": message,
                    "operation": "SEND"
                })
        with utils.rpc_send_queue_lock:
            if recipient in utils.rpc_send_queue:
                utils.debug(f"Server: appending push SEND message to {recipient} via gRPC")
                utils.rpc_send_queue[recipient].append(
                    chat_service_pb2.PushMessage(
                        errno=SUCCESS,
                        sender=sender,
                        msg_id=msg_id,
                        text=message
                    )
                )
        return chat_service_pb2.SendMessageResponse(errno=SUCCESS, msg_id=msg_id)
    
    def DeleteMessage(self, request, context):
        msg_id = request.msg_id
        recipient, sender, unread, errno = database.delete_message(msg_id)
        if recipient:
            is_primary, _ = utils.get_replication_config()
            if is_primary:
                replicate_to_backups({
                    "sender": sender,
                    "recipient": recipient,
                    "text": str(msg_id),
                    "operation": "DELETE"
                })
            response = chat_service_pb2.DeleteMessageResponse(
                errno=SUCCESS, 
                sender=sender,
                msg_id=msg_id, 
                read_status=unread
            )
            with utils.rpc_send_queue_lock:
                if recipient in utils.rpc_send_queue:
                    utils.debug(f"Server: appending push DELETE message to {recipient} via gRPC")
                    utils.rpc_send_queue[recipient].append(
                        chat_service_pb2.PushDeleteMsg(
                            errno=SUCCESS,
                            msg_id=msg_id,
                            sender=sender,
                            read_status=unread
                        )
                    )
            return response
        else:
            return chat_service_pb2.DeleteMessageResponse(errno=errno)
        
    def DeleteAccount(self, request, context):
        errno = database.deactivate_account(request.username)
        if errno == SUCCESS:
            is_primary, _ = utils.get_replication_config()
            if is_primary:
                replicate_to_backups({
                    "sender": request.username,
                    "recipient": "",
                    "text": request.username,
                    "operation": "DELETE_ACCOUNT"
                })
            self._cleanup_client_stream(request.username)
            return chat_service_pb2.DeleteAccountResponse(errno=SUCCESS)
        else:
            return chat_service_pb2.DeleteAccountResponse(errno=errno)
    
    def AckPushMessage(self, request, context):
        utils.debug(f"Received AckPushMessage: {request}")
        msg_id = request.msg_id
        database.mark_message_as_read(msg_id)
        is_primary, _ = utils.get_replication_config()
        if is_primary:
            replicate_to_backups({
                "sender": "",
                "recipient": "",
                "text": str(msg_id),
                "operation": "ACK"
            })
        return chat_service_pb2.AckPushMessageResponse(errno=SUCCESS)

    def UpdateStream(self, request_iterator, context):
        try:
            first_request = next(request_iterator)
        except StopIteration:
            return
        username = first_request.username
        utils.debug(f"User {username} subscribed for live updates.")
        try:
            while context.is_active():
                update = self._get_update_for_user(username)
                if update:
                    utils.debug(f"Sending update to {username}: {update}")
                    if isinstance(update, chat_service_pb2.PushMessage):
                        yield chat_service_pb2.LiveUpdate(push_message=update)
                    elif isinstance(update, chat_service_pb2.PushUser):
                        yield chat_service_pb2.LiveUpdate(push_user=update)
                    elif isinstance(update, chat_service_pb2.PushDeleteMsg):
                        yield chat_service_pb2.LiveUpdate(push_delete_msg=update)
        except Exception as e:
            print(f"Exception in UpdateStream for {username}: {e}")
        finally:
            self._cleanup_client_stream(username)

    def _get_update_for_user(self, username):
        if utils.rpc_send_queue.get(username):
            return utils.rpc_send_queue[username].pop(0)
        return None

    def _cleanup_client_stream(self, username):
        utils.remove_active_client(username)
        utils.remove_rpc_send_queue_user(username)
        
    def JoinNetwork(self, request, context):
        utils.debug(f"JoinNetwork request received from server {request.server_ip}:{request.server_port}")
        found = False
        for server in utils.active_servers:
            if server.ip == request.server_ip and server.port == request.server_port:
                found = True
                break
        if not found:
            new_server = type("ServerInfo", (), {})()
            new_server.ip = request.server_ip
            new_server.port = request.server_port
            new_server.is_primary = 0
            utils.active_servers.append(new_server)
            database.add_server(request.server_ip, request.server_port, is_primary=0)
            utils.debug(f"Added new backup server {request.server_ip}:{request.server_port} to active_servers.")
        server_info_list = []
        for server in utils.active_servers:
            server_info_list.append(chat_service_pb2.ServerInfo(ip=server.ip, port=server.port))
        return chat_service_pb2.JoinNetworkResponse(server_list=server_info_list)
    
    def HealthCheck(self, request, context):
        return chat_service_pb2.HealthCheckResponse(status="OK")
    
    def ReplicateWrite(self, request, context):
        operation = request.operation
        errno = SUCCESS
        if operation == "SEND":
            msg_id = database.store_message(request.sender, request.recipient, request.text)
            with utils.rpc_send_queue_lock:
                if request.recipient in utils.rpc_send_queue:
                    utils.debug(f"Replication: appending push SEND message to {request.recipient} via gRPC")
                    utils.rpc_send_queue[request.recipient].append(
                        chat_service_pb2.PushMessage(
                            errno=SUCCESS,
                            sender=request.sender,
                            msg_id=msg_id,
                            text=request.text
                        )
                    )
        elif operation == "DELETE":
            try:
                msg_id = int(request.text)
            except Exception as e:
                utils.debug(f"Replication DELETE error parsing msg_id: {e}")
                errno = DB_ERROR
                return chat_service_pb2.ReplicationResponse(errno=errno)
            recipient, sender, unread, errno = database.delete_message(msg_id)
            if recipient:
                with utils.rpc_send_queue_lock:
                    if request.recipient in utils.rpc_send_queue:
                        utils.debug(f"Replication: appending push DELETE message to {request.recipient} via gRPC")
                        utils.rpc_send_queue[request.recipient].append(
                            chat_service_pb2.PushDeleteMsg(
                                errno=SUCCESS,
                                msg_id=msg_id,
                                sender=sender,
                                read_status=unread
                            )
                        )
        elif operation == "ACK":
            try:
                msg_id = int(request.text)
                database.mark_message_as_read(msg_id)
                utils.debug(f"Replication: ACK replicated for message id {msg_id}")
            except Exception as e:
                utils.debug(f"Replication ACK error: {e}")
                errno = DB_ERROR
        elif operation == "REGISTER":
            success, reg_errno = database.register_account(request.username, request.text)
            if not success:
                utils.debug(f"Replication: registration failed for {request.username} with error {reg_errno}")
                errno = reg_errno
        elif operation == "DELETE_ACCOUNT":
            reg_errno = database.deactivate_account(request.text)  # request.text carries the username.
            if reg_errno != SUCCESS:
                utils.debug(f"Replication: account deletion failed for {request.text} with error {reg_errno}")
                errno = reg_errno
        elif operation == "LOGIN":
            # Replicate login by marking the user as active.
            utils.add_active_client(request.username, None)
            utils.debug(f"Replication: LOGIN replicated for user {request.username}")
        elif operation == "READ_HISTORY":
            # Replicate chat history read operation.
            ids_str = request.text  # e.g., "101,102,103"
            msg_ids = [int(x) for x in ids_str.split(",") if x]
            for msg_id in msg_ids:
                database.mark_message_as_read(msg_id)
            utils.debug(f"Replication: READ_HISTORY replicated for user {request.username} in conversation with {request.recipient}")
            # Optionally, call a database function to update read status on backups.
        else:
            utils.debug(f"Unknown replication operation: {operation}")
            errno = DB_ERROR
        return chat_service_pb2.ReplicationResponse(errno=errno)
    
    def UpdateServerList(self, request, context):
        new_list = []
        for s in request.server_list:
            server_info = type("ServerInfo", (), {})()
            server_info.ip = s.ip
            server_info.port = s.port
            new_list.append(server_info)
        utils.debug("Server list updated via UpdateServerList RPC.")
        utils.active_servers = new_list
        return chat_service_pb2.UpdateServerListResponse(errno=SUCCESS)

# ---------------------------
# Replication Helper Function
# ---------------------------
def replicate_to_backups(message_data):
    """
    Replicate a client operation to all backup servers.
    message_data is a dictionary containing:
      - sender
      - recipient
      - text (for SEND: message text; for DELETE/ACK: message id as string;
              for REGISTER: password or hashed password; for DELETE_ACCOUNT: username;
              for LOGIN: a comma-separated string of username, ip, and port;
              for READ_HISTORY: can be a flag or comma-separated list of message IDs)
      - operation ("SEND", "DELETE", "ACK", "REGISTER", "DELETE_ACCOUNT", "LOGIN", "READ_HISTORY")
    """
    import grpc
    _, actual_addr = utils.get_replication_config()
    for server_info in utils.active_servers:
        if (server_info.ip, server_info.port) == actual_addr:
            continue
        try:
            backup_grpc_address = f"{server_info.ip}:{server_info.port + 1}"
            channel = grpc.insecure_channel(backup_grpc_address)
            stub = chat_service_pb2_grpc.ChatServiceStub(channel)
            replication_req = chat_service_pb2.ReplicationRequest(
                sender=message_data.get("sender", ""),
                recipient=message_data.get("recipient", ""),
                text=message_data["text"],
                operation=message_data["operation"]
            )
            stub.ReplicateWrite(replication_req)
            utils.debug(f"Replicated {message_data['operation']} operation to backup {server_info.ip}:{server_info.port}")
        except Exception as e:
            utils.debug(f"Replication to {server_info.ip}:{server_info.port} failed: {e}")
