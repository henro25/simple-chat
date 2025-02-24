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
    recipient = "anotheruser"
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
    request = chat_service_pb2.SendMessageRequest(sender="testuser", recipient="anotheruser", text="Hello!")
    response = grpc_stub.SendMessage(request)
    assert response.errno == 0  # SUCCESS
    assert response.msg_id > 0  # Valid message ID

def test_delete_message(grpc_stub):
    """Tests deleting a message by ensuring a message exists before attempting deletion."""
    sender = "testuser"
    recipient = "anotheruser"
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

