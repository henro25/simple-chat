"""
Module Name: test_server.py
Description: Unit tests for the server module. These tests simulate client connections
             and verify that responses (both success and failure) are returned when
             the server (via its service_connection function) calls various database
             functions (registration, login, sending messages, reading history,
             deleting messages, and deactivating accounts).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import json
import os
import selectors
import types
import pytest

from server import server
from server import protocols
from server.protocols import custom_protocol, json_protocol
from server.utils import active_clients
from configs.config import UNSUPPORTED_VERSION, SUCCESS, USER_TAKEN, USER_DNE, WRONG_PASS, DB_ERROR, ID_DNE, debug

# ------------------------------------------------------------------
# Fixture to initialize the test database (accounts, messages, etc.)
# ------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_database_for_server_tests():
    test_db = "test_chat.db"
    server.database.DATABASE_NAME = test_db
    if os.path.exists(test_db):
        os.remove(test_db)
    # Create necessary tables: accounts and messages.
    server.database.initialize_db()
    # Pre-populate the accounts table.
    accounts = [
        ("alice", "hash1"),
        ("bob", "hash2"),
        ("charlie", "hash3"),
        ("david", "hash4")
    ]
    for username, pwd in accounts:
        server.database.register_account(username, pwd)
    
    yield  # run tests

    if os.path.exists(test_db):
        os.remove(test_db)

# ------------------------------------------------------------------
# DummySocket class to simulate a client socket.
# ------------------------------------------------------------------
class DummySocket:
    def __init__(self, recv_data=b""):
        # recv_data: bytes to be returned once on recv() call.
        self.recv_data = recv_data
        self.sent_data = b""
        self.closed = False
        # For selector compatibility, assign a dummy fileno.
        self._fileno = 10000

    def fileno(self):
        return self._fileno

    def recv(self, bufsize):
        if self.recv_data:
            data = self.recv_data
            self.recv_data = b""
            return data
        return b""

    def send(self, data):
        self.sent_data += data
        return len(data)
    
    def sendall(self, data):
        return self.send(data)

    def setblocking(self, flag):
        pass

    def close(self):
        self.closed = True

# ------------------------------------------------------------------
# Fixture to clear active_clients and reset the selector between tests.
# ------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clear_active_clients_and_selector():
    active_clients.clear()
    server.sel.close()
    server.sel = selectors.DefaultSelector()
    yield
    active_clients.clear()

# =========================
# Additional Custom Protocol Tests
# =========================

def test_custom_parse_message_valid():
    message = "1.0 LOGIN alice hash1"
    version, command, args = custom_protocol.parse_message(message)
    assert version == "1.0"
    assert command == "LOGIN"
    assert args == ["alice", "hash1"]

def test_custom_parse_message_invalid():
    message = "1.0"
    version, command, args = custom_protocol.parse_message(message)
    assert version is None
    assert command is None
    assert args == []

def test_custom_login_failure():
    # Simulate a login with the wrong password.
    # "alice" is registered with "hash1", so using "wrong_hash" should fail.
    msg = "1.0 LOGIN alice wrong_hash\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 10000), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    # Expect an error response.
    assert response.startswith("1.0 ERROR"), "LOGIN failure should return an error response due to wrong password"

def test_custom_unknown_command():
    # Test that an unrecognized command returns an error.
    msg = "1.0 FOOBAR arg1 arg2\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 10001), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 ERROR"), "Unknown command should return an error response"

def test_custom_get_conversations_no_messages():
    # Test get_conversations for a user with no messages.
    # Pre-populated accounts are: alice, bob, charlie, david.
    convos = server.database.get_conversations("alice")
    expected = [("bob", 0), ("charlie", 0), ("david", 0)]
    assert convos == expected, f"Expected {expected}, got {convos}"

def test_mark_message_as_read():
    # Test that marking a message as read updates the unread count.
    # Store a message from alice to bob.
    msg_id = server.database.store_message("alice", "bob", "Test message")
    unread_before = server.database.get_num_unread("bob")
    server.database.mark_message_as_read(msg_id)
    unread_after = server.database.get_num_unread("bob")
    # Since one unread message was marked as read, unread_after should be unread_before - 1 (or 0 if it was 1)
    expected = max(0, unread_before - 1)
    assert unread_after == expected, "Unread count should decrease by 1 after marking a message as read"

def test_verify_valid_recipient_deactivated():
    # Test that a deactivated account is not a valid recipient.
    # Deactivate "david" and then verify.
    server.database.deactivate_account("david")
    valid = server.database.verify_valid_recipient("david")
    assert valid == 0, "Deactivated account should not be a valid recipient"

# --- (Existing tests for CREATE, SEND, READ, DEL_MSG, and DEL_ACC follow below) ---

def test_service_connection_create_success_custom():
    # "newuser" is not pre-registered so registration should succeed.
    msg = "1.0 CREATE newuser secret\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 23456), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    # Expected response is from handle_get_conversations: "1.0 USERS <page_code> newuser ..."
    assert response.startswith("1.0 USERS"), "CREATE success response should start with '1.0 USERS'"
    parts = response.split()
    # The response format is: "1.0 USERS <page_code> newuser ..." 
    assert parts[3] == "newuser", "Response should include 'newuser' as the registered account"

def test_service_connection_create_failure_custom():
    # Attempt to create an account using an existing username ("alice").
    msg = "1.0 CREATE alice secret\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 22222), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 ERROR"), "CREATE failure should return an error"

def test_service_connection_create_success_json():
    # Test the JSON protocol CREATE command for a new account.
    msg_data = {"opcode": "CREATE", "data": ["newjson", "secret"]}
    msg = f"2.0 {json.dumps(msg_data)}\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 33333), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    version, opcode, data_resp = json_protocol.parse_message(response)
    assert version == "2.0"
    assert opcode == "USERS"
    # Expect data format: [page_code, "newjson", ...]
    assert data_resp[1] == "newjson", "Response should include 'newjson' as the registered account"

def test_service_connection_create_failure_json():
    # Try to register an account that already exists ("alice") via JSON.
    msg_data = {"opcode": "CREATE", "data": ["alice", "secret"]}
    msg = f"2.0 {json.dumps(msg_data)}\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 44444), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    version, opcode, data_resp = json_protocol.parse_message(response)
    assert opcode == "ERROR", "JSON CREATE failure should return an ERROR response"

def test_service_connection_send_message_success_custom():
    # Set up a dummy socket for the recipient "bob" to capture PUSH_MSG.
    recipient_sock = DummySocket()
    active_clients["bob"] = recipient_sock

    # Construct a SEND command where "alice" sends "Hello Bob" to "bob".
    msg = "1.0 SEND alice bob Hello Bob\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 55555), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    # Expected response: "1.0 ACK <msg_id>"
    assert response.startswith("1.0 ACK"), "SEND command should return ACK"
    # Verify that "bob" received a PUSH_MSG.
    assert b"PUSH_MSG" in recipient_sock.sent_data, "Recipient 'bob' should receive a PUSH_MSG"

def test_service_connection_send_message_success_json():
    recipient_sock = DummySocket()
    active_clients["bob"] = recipient_sock

    msg_data = {"opcode": "SEND", "data": ["alice", "bob", "Hello", "JSON"]}
    msg = f"2.0 {json.dumps(msg_data)}\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 66666), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    version, opcode, data_resp = json_protocol.parse_message(response)
    assert opcode == "ACK", "JSON SEND command should return ACK"
    # Check that "bob" received a PUSH_MSG.
    assert b"PUSH_MSG" in recipient_sock.sent_data, "Recipient 'bob' should receive a PUSH_MSG in JSON send"

def test_service_connection_read_chat_history_custom():
    # Pre-store a message from "bob" to "alice".
    server.database.store_message("bob", "alice", "Chat message")
    # Construct a READ command: "1.0 READ alice bob -1 20\n"
    msg = "1.0 READ alice bob -1 20\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 77777), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 MSGS"), "READ command should return MSGS response"
    assert "Chat message" in response, "Response should include the chat message text"

def test_service_connection_read_chat_history_json():
    # Pre-store a message from "bob" to "alice".
    server.database.store_message("bob", "alice", "JSON chat message")
    msg_data = {"opcode": "READ", "data": ["alice", "bob", "-1", "20"]}
    msg = f"2.0 {json.dumps(msg_data)}\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 88888), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    version, opcode, data_resp = json_protocol.parse_message(response)
    assert opcode == "MSGS", "JSON READ command should return MSGS response"
    # Ensure the response data contains the chat message.
    assert any("JSON chat message" in s for s in data_resp), "Response should include the chat message text"

def test_service_connection_delete_message_success_custom():
    # Pre-store a message from "alice" to "bob".
    msg_id = server.database.store_message("alice", "bob", "To be deleted")
    msg = f"1.0 DEL_MSG {msg_id}\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 23456), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 DEL_MSG"), "DEL_MSG command should return DEL_MSG response"
    assert str(msg_id) in response, "Response should include the message ID"

def test_service_connection_delete_message_failure_custom():
    # Attempt to delete a non-existent message (id 999999).
    msg = "1.0 DEL_MSG 999999\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 23456), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 ERROR"), "DEL_MSG failure should return an ERROR response"

def test_service_connection_deactivate_account_success_custom(monkeypatch):
    # Simulate that "alice" is online.
    dummy_sock = DummySocket()
    active_clients["alice"] = dummy_sock
    
    # Monkeypatch sel.unregister so that it does nothing (avoiding the lookup error).
    monkeypatch.setattr(server.sel, "unregister", lambda sock: None)
    
    msg = "1.0 DEL_ACC alice\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 23456), inb=b"", outb=b"", username="alice")
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 DEL_ACC"), "DEL_ACC command should return DEL_ACC response"
    assert "alice" not in active_clients, "'alice' should be removed from active_clients after deletion"

def test_service_connection_deactivate_account_failure_custom():
    # Attempt to deactivate a non-existent account ("nonuser").
    msg = "1.0 DEL_ACC nonuser\n".encode("utf-8")
    dummy_sock = DummySocket(recv_data=msg)
    key = types.SimpleNamespace(
        fileobj=dummy_sock,
        data=types.SimpleNamespace(addr=("127.0.0.1", 23456), inb=b"", outb=b"", username=None)
    )
    server.service_connection(key, selectors.EVENT_READ)
    response = key.data.outb.decode("utf-8")
    assert response.startswith("1.0 ERROR"), "DEL_ACC for non-existent account should return an ERROR response"
