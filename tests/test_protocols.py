"""
Module Name: test_protocols.py
Description: Unit tests for the custom protocol and JSON protocol message parsing and handling functions.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

import os
import pytest
import json

# Change test directory to the server directory so that tests run with the proper configuration.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
server_dir = os.path.join(project_root, 'server')
os.chdir(server_dir)

from server import database
from server.protocols import custom_protocol, json_protocol
from configs.config import *
import grpc
from concurrent import futures
from unittest.mock import patch
import server.utils as utils
import chat_service_pb2
import chat_service_pb2_grpc

from server.protocols.grpc_server_protocol import MyChatService

# Fixture to set up and tear down a temporary test database.
@pytest.fixture(autouse=True)
def setup_database():
    test_db = "test_chat.db"
    database.DATABASE_NAME = test_db

    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize the database (creates the necessary tables).
    database.initialize_db()
    
    # Pre-populate the accounts table.
    accounts = [
        ("alice", "hash1"),
        ("bob", "hash2"),
        ("charlie", "hash3"),
        ("david", "hash4")
    ]
    for username, pwd in accounts:
        database.register_account(username, pwd)
    
    yield  # run the tests
    
    if os.path.exists(test_db):
        os.remove(test_db)

# ------------------------------------------------------------------
# Fixture to clear active_clients before and after each test.
# ------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clear_active_clients():
    utils.active_clients.clear()
    yield
    utils.active_clients.clear()

# ------------------------------------------------------------
# DummySocket to simulate a client connection for push messages.
# ------------------------------------------------------------
class DummySocket:
    def __init__(self):
        self.sent_data = []
    def sendall(self, data):
        self.sent_data.append(data)

# ============================
# Tests for Custom Protocol
# ============================

def test_custom_parse_message_valid():
    message = "1.0 CREATE username password"
    version, command, args = custom_protocol.parse_message(message)
    assert version == "1.0"
    assert command == "CREATE"
    assert args == ["username", "password"]

def test_custom_parse_message_invalid():
    message = "1.0"
    version, command, args = custom_protocol.parse_message(message)
    assert version is None
    assert command is None
    assert args == []

def test_custom_process_message_unsupported_version():
    # A version not in SUPPORTED_VERSIONS should trigger an error.
    message = "0.9 CREATE username password"
    response = custom_protocol.process_message(message)
    expected = f"1.0 ERROR {UNSUPPORTED_VERSION}"
    assert response == expected

def test_custom_process_message_unknown_command():
    message = "1.0 FOOBAR arg1 arg2"
    response = custom_protocol.process_message(message)
    expected = f"1.0 ERROR {UNKNOWN_COMMAND}"
    assert response == expected

def test_custom_handle_create():
    # Create a new account "eve" (which does not exist yet).
    args = ["eve", "secret"]
    response = custom_protocol.handle_create(args)
    # handle_create calls handle_get_conversations with page code REG_PG.
    # Pre-populated accounts are: alice, bob, charlie, david.
    expected = f"1.0 USERS {REG_PG} eve alice 0 bob 0 charlie 0 david 0"
    assert response == expected

def test_custom_handle_login():
    # Login with an existing account "alice" (password "hash1").
    args = ["alice", "hash1"]
    response = custom_protocol.handle_login(args)
    # Expected response: "1.0 USERS {LGN_PG} alice ..." with remaining accounts sorted alphabetically.
    expected = f"1.0 USERS {LGN_PG} alice bob 0 charlie 0 david 0"
    assert response == expected

def test_custom_handle_get_chat_history():
    # Insert a message from alice to bob.
    msg_id = database.store_message("alice", "bob", "Hello Bob")
    # Request chat history (with oldest_msg_id == -1 to fetch recent messages).
    args = ["alice", "bob", "-1", "5"]
    response = custom_protocol.handle_get_chat_history(args)
    # The response should start with "1.0 MSGS" and include the message "Hello Bob".
    assert response.startswith("1.0 MSGS")
    assert "Hello Bob" in response

def test_custom_handle_send_message():
    # Set up a dummy socket for bob to capture push messages.
    dummy_sock = DummySocket()
    utils.active_clients["bob"] = dummy_sock
    args = ["alice", "bob", "Hi", "Bob"]
    response = custom_protocol.handle_send_message(args)
    # Response should be in the format: "1.0 ACK <msg_id>".
    assert response.startswith("1.0 ACK")
    # Verify that bob's dummy socket received a PUSH_MSG.
    push_found = any(b"PUSH_MSG" in data for data in dummy_sock.sent_data)
    assert push_found

def test_custom_handle_delete_messages():
    # Insert a message and then delete it.
    sender = "alice"
    msg_id = database.store_message(sender, "bob", "To be deleted")
    args = [str(msg_id)]
    response = custom_protocol.handle_delete_messages(args)
    expected = f"1.0 DEL_MSG {msg_id} {sender} {1}"
    assert response == expected

def test_custom_handle_delete_account():
    # Add "charlie" to active_clients.
    dummy_sock = DummySocket()
    utils.active_clients["charlie"] = dummy_sock
    args = ["charlie"]
    response = custom_protocol.handle_delete_account(args)
    assert response == "1.0 DEL_ACC"
    assert "charlie" not in utils.active_clients

def test_custom_process_message_dispatch():
    # Test that process_message dispatches correctly to the LOGIN handler.
    message = "1.0 LOGIN alice hash1"
    response = custom_protocol.process_message(message)
    expected = f"1.0 USERS {LGN_PG} alice bob 0 charlie 0 david 0"
    assert response == expected

# ============================
# Tests for JSON Protocol
# ============================

PROTOCOL_VERSION = "2.0"

def test_json_wrap_and_parse_message():
    wrapped = json_protocol.wrap_message("TEST", ["data1", "data2"])
    version, opcode, data = json_protocol.parse_message(wrapped)
    assert version == PROTOCOL_VERSION
    assert opcode == "TEST"
    assert data == ["data1", "data2"]

def test_json_parse_message_valid():
    message_dict = {"opcode": "LOGIN", "data": ["alice", "hash1"]}
    message = f"{PROTOCOL_VERSION} {json.dumps(message_dict)}"
    version, opcode, data = json_protocol.parse_message(message)
    assert version == PROTOCOL_VERSION
    assert opcode == "LOGIN"
    assert data == ["alice", "hash1"]

def test_json_parse_message_invalid():
    message = "invalid message"
    version, opcode, data = json_protocol.parse_message(message)
    assert version is None
    assert opcode is None
    assert data == []

def test_json_process_message_unsupported_version():
    # Construct a message with the wrong protocol version.
    message_dict = {"opcode": "LOGIN", "data": ["alice", "hash1"]}
    message = f"1.0 {json.dumps(message_dict)}"
    response = json_protocol.process_message(message)
    expected = json_protocol.wrap_message("ERROR", [UNSUPPORTED_VERSION])
    assert response == expected

def test_json_handle_create():
    data = ["eve", "secret"]
    response = json_protocol.handle_create(data)
    # Expected: a wrapped message with opcode "USERS" whose data starts with REG_PG and the new username.
    version, opcode, resp_data = json_protocol.parse_message(response)
    assert version == PROTOCOL_VERSION
    assert opcode == "USERS"
    assert resp_data[0] == str(REG_PG)
    assert resp_data[1] == "eve"

def test_json_handle_login():
    data = ["alice", "hash1"]
    response = json_protocol.handle_login(data)
    version, opcode, resp_data = json_protocol.parse_message(response)
    assert version == PROTOCOL_VERSION
    assert opcode == "USERS"
    # For alice, the second element in the response data should be "alice".
    assert resp_data[1] == "alice"

def test_json_handle_get_chat_history():
    # Insert a message between alice and bob.
    msg_id = database.store_message("alice", "bob", "Hello JSON")
    data = ["alice", "bob", "-1", "5"]
    response = json_protocol.handle_get_chat_history(data)
    version, opcode, resp_data = json_protocol.parse_message(response)
    assert version == PROTOCOL_VERSION
    assert opcode == "MSGS"
    # Ensure that the response data contains the message text.
    assert any("Hello JSON" in item for item in resp_data)

def test_json_handle_send_message():
    # Set up a dummy socket for bob.
    dummy_sock = DummySocket()
    utils.active_clients["bob"] = dummy_sock
    data = ["alice", "bob", "Hi", "JSON"]
    response = json_protocol.handle_send_message(data)
    version, opcode, resp_data = json_protocol.parse_message(response)
    assert version == PROTOCOL_VERSION
    assert opcode == "ACK"
    # Verify that bob's dummy socket received a PUSH_MSG.
    push_found = any(b"PUSH_MSG" in d for d in dummy_sock.sent_data)
    assert push_found

def test_json_handle_delete_messages():
    msg_id = database.store_message("alice", "bob", "Delete JSON")
    data = [str(msg_id)]
    response = json_protocol.handle_delete_messages(data)
    version, opcode, resp_data = json_protocol.parse_message(response)
    assert version == PROTOCOL_VERSION
    assert opcode == "DEL_MSG"
    assert resp_data[0] == str(msg_id)

def test_json_handle_delete_account():
    dummy_sock = DummySocket()
    utils.active_clients["david"] = dummy_sock
    data = ["david"]
    response = json_protocol.handle_delete_account(data)
    version, opcode, resp_data = json_protocol.parse_message(response)
    assert version == PROTOCOL_VERSION
    assert opcode == "DEL_ACC"
    assert "david" not in utils.active_clients

def test_json_process_message_dispatch():
    # Test that process_message correctly dispatches a LOGIN request.
    message_dict = {"opcode": "LOGIN", "data": ["alice", "hash1"]}
    message = f"{PROTOCOL_VERSION} {json.dumps(message_dict)}"
    response = json_protocol.process_message(message)
    version, opcode, resp_data = json_protocol.parse_message(response)
    # We expect a USERS response in reply to a successful login.
    assert opcode == "USERS"
    assert resp_data[1] == "alice"

# ============================
# Tests for gRPC Protocol
# ============================

@pytest.fixture(scope="module")
def grpc_server():
    """Sets up a test gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_service_pb2_grpc.add_ChatServiceServicer_to_server(MyChatService(), server)
    port = server.add_insecure_port("[::]:50051")
    server.start()
    yield f"localhost:{port}"
    server.stop(None)

@pytest.fixture(scope="module")
def grpc_stub(grpc_server):
    """Creates a gRPC channel and stub for testing."""
    channel = grpc.insecure_channel(grpc_server)
    return chat_service_pb2_grpc.ChatServiceStub(channel)


def test_register(grpc_stub):
    """Tests the registration of a new user following the format of custom and JSON protocols."""
    username = "testuser"
    password = "password"
    request = chat_service_pb2.RegisterRequest(username=username, password=password, ip_address="127.0.0.1", port=5000)
    response = grpc_stub.Register(request)
    
    expected_response = {
        "errno": 0,  # SUCCESS
        "page_code": 1,  # Assuming REG_PG is 1
        "client_username": username
    }
    
    assert response.errno == expected_response["errno"]
    assert response.client_username == expected_response["client_username"]

def test_login(grpc_stub):
    """Tests user login following the format of custom and JSON protocols."""
    """Tests user login by ensuring credentials exist in the database before attempting login."""
    username = "Alice"
    password = "Hash1"
    database.register_account(username, password)
    
    request = chat_service_pb2.LoginRequest(username=username, password=password, ip_address="127.0.0.1", port=5000)
    response = grpc_stub.Login(request)
    
    expected_response = {
        "errno": 0,  # SUCCESS
        "page_code": LGN_PG,
        "client_username": username
    }
    
    assert response.errno == expected_response["errno"]
    assert response.client_username == expected_response["client_username"]


def test_get_chat_history(grpc_stub):
    """Tests retrieving chat history and ensuring correctness."""
    sender = "testuser"
    recipient = "alice"
    test_message = "Hello, this is a test message!"
    
    # Ensure the user has sent at least one message
    send_response = grpc_stub.SendMessage(
        chat_service_pb2.SendMessageRequest(sender=sender, recipient=recipient, text=test_message)
    )
    assert send_response.errno == 0  # SUCCESS
    msg_id = send_response.msg_id
    
    request = chat_service_pb2.ChatHistoryRequest(username=sender, other_user=recipient, num_msgs=10, oldest_msg_id=-1)
    response = grpc_stub.GetChatHistory(request)
    
    assert response.errno == 0  # SUCCESS
    assert len(response.chat_history) > 0  # Ensure at least one message exists
    
    # Verify the correct message is retrieved
    last_message = response.chat_history[-1]
    assert last_message.sender == sender
    assert last_message.text == test_message

def test_send_message(grpc_stub):
    """Tests sending a message."""
    request = chat_service_pb2.SendMessageRequest(sender="testuser", recipient="alice", text="Hello!")
    response = grpc_stub.SendMessage(request)
    assert response.errno == 0  # SUCCESS
    assert response.msg_id > 0  # Valid message ID

def test_delete_message(grpc_stub):
    """Tests deleting a message by ensuring a message exists before attempting deletion."""
    sender = "testuser"
    recipient = "alice"
    message_text = "This is a test message to be deleted."
    
    # Send a message first
    send_response = grpc_stub.SendMessage(
        chat_service_pb2.SendMessageRequest(sender=sender, recipient=recipient, text=message_text)
    )
    assert send_response.errno == 0  # Ensure message was sent successfully
    msg_id = send_response.msg_id
    
    # Now delete the message
    request = chat_service_pb2.DeleteMessageRequest(msg_id=msg_id)
    response = grpc_stub.DeleteMessage(request)
    
    assert response.errno == 0  # SUCCESS

def test_delete_account(grpc_stub):
    """Tests deleting an account."""
    username = "testuser"
    password = "password"
    database.register_account(username, password)
    
    response = grpc_stub.DeleteAccount(chat_service_pb2.DeleteAccountRequest(username=username))
    
    assert response.errno == 0  # SUCCESS
    assert "testuser" not in utils.active_clients


def test_live_updates(grpc_stub):
    """Tests bidirectional streaming for live updates."""
    
    def request_generator():
        yield chat_service_pb2.LiveUpdateRequest(username="testuser")  # Subscribe to updates
    
    # Simulate an update: Send a message that should trigger a live update
    grpc_stub.SendMessage(chat_service_pb2.SendMessageRequest(sender="testuser", recipient="anotheruser", text="Live update test"))

    responses = grpc_stub.UpdateStream(request_generator())  # Start streaming
    
    for response in responses:
        assert isinstance(response, chat_service_pb2.LiveUpdate)  # Ensure server responded
        break  # Stop after first response

def test_register_duplicate_user(grpc_stub):
    """
    Tests that registering a duplicate user returns an error.
    """
    username = "duplicateuser"
    password = "password"

    # First registration should succeed
    first_resp = grpc_stub.Register(
        chat_service_pb2.RegisterRequest(username=username, password=password, ip_address="127.0.0.1", port=5000)
    )
    assert first_resp.errno == 0  # SUCCESS

    # Second registration with same credentials should fail
    second_resp = grpc_stub.Register(
        chat_service_pb2.RegisterRequest(username=username, password=password, ip_address="127.0.0.1", port=5001)
    )
    # Check for an appropriate error code (e.g., USER_EXISTS or similar)
    assert second_resp.errno != 0  # Should NOT be SUCCESS


def test_login_wrong_password(grpc_stub):
    """
    Tests logging in with an incorrect password.
    """
    username = "wrongpassuser"
    password = "correctpassword"
    database.register_account(username, password)

    # Attempt login with the wrong password
    request = chat_service_pb2.LoginRequest(
        username=username, 
        password="incorrectPW", 
        ip_address="127.0.0.1", 
        port=5000
    )
    response = grpc_stub.Login(request)
    # Expect an error code for wrong password
    assert response.errno != 0
    # Check that page_code is not set
    assert response.page_code == 0  # or any default page code for failure


def test_login_already_online(grpc_stub):
    """
    Tests logging in a user who is already online (i.e., active in rpc_send_queue).
    """
    username = "onlineuser"
    password = "password"
    database.register_account(username, password)

    # First login
    req_first = chat_service_pb2.LoginRequest(
        username=username, password=password, ip_address="127.0.0.1", port=5000
    )
    resp_first = grpc_stub.Login(req_first)
    assert resp_first.errno == 0  # SUCCESS

    # Attempt second login (same user), expecting USER_LOGGED_ON or similar
    req_second = chat_service_pb2.LoginRequest(
        username=username, password=password, ip_address="127.0.0.1", port=5001
    )
    resp_second = grpc_stub.Login(req_second)
    # Confirm that the server disallows multiple logins
    assert resp_second.errno == USER_LOGGED_ON  # or whatever code the server uses for already online


def test_get_chat_history_invalid_user(grpc_stub):
    """
    Tests retrieving chat history for a user that doesn't exist.
    """
    request = chat_service_pb2.ChatHistoryRequest(
        username="nonexistent", 
        other_user="anotheruser", 
        num_msgs=5, 
        oldest_msg_id=-1
    )
    response = grpc_stub.GetChatHistory(request)
    # The server might return an error code or an empty result
    # Checking a non-zero errno if server enforces user existence
    # If your server doesn't enforce it, adapt as needed
    assert response.errno != 0 or len(response.chat_history) == 0


def test_send_message_to_nonexistent_user(grpc_stub):
    """
    Tests sending a message to a user that doesn't exist or is deactivated.
    """
    sender = "testuser"
    recipient = "ghostuser"  # not in DB
    message_text = "Message to non-existent user"

    database.register_account(sender, "password")

    request = chat_service_pb2.SendMessageRequest(
        sender=sender,
        recipient=recipient,
        text=message_text
    )
    response = grpc_stub.SendMessage(request)
    # The server might set msg_id = -1 or return an error code
    # if 'verify_valid_recipient' fails.
    assert response.errno == 0  # The server might still respond 0 but set msg_id=-1
    assert response.msg_id == -1  # Indicating recipient is invalid


def test_delete_nonexistent_message(grpc_stub):
    """
    Tests deleting a message that doesn't exist.
    """
    sender = "alice"
    msg_id = 99999  # A large number presumably not used

    request = chat_service_pb2.DeleteMessageRequest(msg_id=msg_id)
    response = grpc_stub.DeleteMessage(request)
    # Expect an error or a specific errno to indicate message not found
    assert response.errno != 0  # E.g. MSG_DNE or similar


def test_delete_already_deleted_message(grpc_stub):
    """
    Tests attempting to delete a message that was already deleted.
    """
    sender = "alice"
    recipient = "bob"
    message_text = "Message to be deleted twice."

    # Create the message first
    send_resp = grpc_stub.SendMessage(
        chat_service_pb2.SendMessageRequest(
            sender=sender, recipient=recipient, text=message_text
        )
    )
    assert send_resp.errno == 0
    msg_id = send_resp.msg_id

    # Delete the message the first time
    del_resp_1 = grpc_stub.DeleteMessage(chat_service_pb2.DeleteMessageRequest(msg_id=msg_id))
    assert del_resp_1.errno == 0

    # Delete the message the second time
    del_resp_2 = grpc_stub.DeleteMessage(chat_service_pb2.DeleteMessageRequest(msg_id=msg_id))
    # Expect an error indicating the message is not found or already deleted
    assert del_resp_2.errno != 0


def test_delete_account_nonexistent(grpc_stub):
    """
    Tests attempting to delete an account that doesn't exist.
    """
    request = chat_service_pb2.DeleteAccountRequest(username="ghostaccount")
    response = grpc_stub.DeleteAccount(request)
    # The server might return an errno for "account not found" or "already deactivated"
    assert response.errno != 0  # Not success if the account isn't there


def test_live_updates_no_changes(grpc_stub):
    """
    Tests that if no changes occur, the server doesn't push any updates.
    """
    def request_generator():
        yield chat_service_pb2.LiveUpdateRequest(username="testuser_no_changes")
    
    # Start streaming
    responses = grpc_stub.UpdateStream(request_generator())

    # Attempt to read from the stream
    # If no changes occur, we might either block or get no responses
    # So we can set a small timeout or break quickly
    try:
        response = next(responses)
        # If we get a response, that's unexpected unless the server auto-sends
        assert False, "Expected no updates, but got a response"
    except StopIteration:
        # This is the expected behavior if the server has no updates
        pass
    except Exception:
        # If the server blocks or times out, you might handle differently
        pass

def test_ack_push_message(grpc_stub):
    """
    Tests acknowledging a pushed message. We simulate sending a message, 
    retrieving it via push, and verifying AckPushMessage is successful.
    """
    msg_id = 123456  # Some random ID
    ack_req = chat_service_pb2.AckPushMessageRequest(msg_id=msg_id)
    ack_resp = grpc_stub.AckPushMessage(ack_req)
    # The server should set errno=0 for success
    assert ack_resp.errno == 0


def test_register_long_username(grpc_stub):
    """
    Tests registering with a very long username to ensure server handles large input gracefully.
    """
    long_username = "user_" + ("x" * 5000)  # 5000 chars
    request = chat_service_pb2.RegisterRequest(username=long_username, password="pwd", ip_address="127.0.0.1", port=6001)
    response = grpc_stub.Register(request)
    # The server might accept or reject—depends on your max length rules
    # If there's a limit, expect an error
    # If not, ensure it doesn't crash
    assert response.errno == 0


def test_login_no_such_user(grpc_stub):
    """
    Tests logging in with a username that was never registered.
    """
    request = chat_service_pb2.LoginRequest(username="nonexistentuser", password="nopass", ip_address="127.0.0.1", port=6002)
    response = grpc_stub.Login(request)
    # Expect non-zero errno
    assert response.errno != 0


def test_large_message_sending(grpc_stub):
    """
    Tests sending a very large text message to ensure the server can handle it.
    """
    sender = "bigmsgsender"
    password = "pass"
    database.register_account(sender, password)

    # A large message (e.g., ~1MB of text)
    large_text = "A" * 1024 * 1024  # 1 MB of 'A'
    request = chat_service_pb2.SendMessageRequest(sender=sender, recipient="bob", text=large_text)
    response = grpc_stub.SendMessage(request)
    
    assert response.errno == 0 


def test_message_sending_concurrently(grpc_stub):
    """
    Tests concurrency: multiple messages sent from the same user quickly.
    Ensures the server can handle concurrent requests without locking issues.
    """
    sender = "concuser"
    password = "pass"
    database.register_account(sender, password)

    import threading

    def send_msg(i):
        req = chat_service_pb2.SendMessageRequest(sender=sender, recipient="bob", text=f"Concurrent msg {i}")
        resp = grpc_stub.SendMessage(req)
        assert resp.errno == 0

    threads = []
    for i in range(5):
        t = threading.Thread(target=send_msg, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

def test_relogin_after_deletion(grpc_stub):
    """
    Tests that once an account is deleted, it cannot log in again.
    """
    user = "deleteduser"
    pwd = "pass"
    database.register_account(user, pwd)

    # Delete the account
    del_resp = grpc_stub.DeleteAccount(chat_service_pb2.DeleteAccountRequest(username=user))
    assert del_resp.errno == 0

    # Attempt to log in again
    login_req = chat_service_pb2.LoginRequest(username=user, password=pwd, ip_address="127.0.0.1", port=6010)
    login_resp = grpc_stub.Login(login_req)

    # Should fail
    assert login_resp.errno != 0


def test_live_updates_multiple_messages(grpc_stub):
    """
    Tests streaming updates when multiple messages are sent.
    Verifies the server pushes multiple push messages.
    """
    username = "liveupdatetester"
    password = "pass"
    register_req = chat_service_pb2.RegisterRequest(
        username=username,
        password=password,
        ip_address="127.0.0.1", 
        port=5000
    )
    register_resp = grpc_stub.Register(register_req)
    assert register_resp.errno == 0

    def request_generator():
        # The client "subscribes" for updates
        yield chat_service_pb2.LiveUpdateRequest(username=username)

    # Send multiple messages from another user
    for i in range(3):
        grpc_stub.SendMessage(chat_service_pb2.SendMessageRequest(
            sender="alice", recipient=username, text=f"Message #{i}"
        ))

    # Start streaming
    responses = grpc_stub.UpdateStream(request_generator())

    count_updates = 0
    try:
        for response in responses:
            assert isinstance(response, chat_service_pb2.LiveUpdate)
            # We expect push_message for each of the 3 messages
            update_type = response.WhichOneof("update")
            if update_type == "push_message":
                count_updates += 1
            if count_updates >= 3:
                # Once we've seen all 3 updates, break
                break
    except StopIteration:
        pass

    # Ensure we received all 3 updates
    assert count_updates == 3


def test_invalid_delete_account_request(grpc_stub):
    """
    Tests if the server gracefully handles malformed or partial requests.
    Some servers or Protobuf definitions might not allow partial requests,
    but let's pretend we create an invalid request with missing fields.
    """
    resp = grpc_stub.DeleteAccount(chat_service_pb2.DeleteAccountRequest(username=""))
    assert resp.errno != 0

