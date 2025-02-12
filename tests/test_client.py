"""
Module Name: test_client.py
Description: Unit tests for the client module. These tests simulate receiving
             messages from the server (using both 1.0 and 2.0 protocols as well as
             unsupported versions), sending requests, closing the connection, and
             running the client's event loop.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import json
import selectors
import socket
import sys
import types
import pytest

from client import client
from client import protocols
from client.protocols import custom_protocol, json_protocol
from configs.config import UNSUPPORTED_VERSION, debug

# ------------------------------------------------------------------
# DummySocket for client tests (for tests not requiring real OS sockets)
# ------------------------------------------------------------------
class DummySocket:
    _fileno_counter = 20000

    def __init__(self, recv_data=b""):
        self.recv_data = recv_data
        self.sent_data = b""
        self.closed = False
        self._fileno = DummySocket._fileno_counter
        DummySocket._fileno_counter += 1

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
# Fixture: Create a client instance with a dummy socket (for most tests).
# ------------------------------------------------------------------
@pytest.fixture
def client_instance(monkeypatch):
    # Create a Client instance. It will try to connect, but we then replace its socket.
    cl = client.Client(host="127.0.0.1", port=9999)
    dummy_sock = DummySocket()
    cl.sock = dummy_sock
    cl.inb = ""
    return cl

# ------------------------------------------------------------------
# Test: Client receives a custom protocol (1.0) message.
# ------------------------------------------------------------------
def test_client_receive_message_custom(monkeypatch, client_instance):
    custom_called = False
    def dummy_custom_process(msg, cl):
        nonlocal custom_called
        custom_called = True
        cl.processed_msg = msg.strip()
    monkeypatch.setattr(custom_protocol, "process_message", dummy_custom_process)

    test_msg = "1.0 TEST custom message\n"
    client_instance.sock.recv_data = test_msg.encode("utf-8")
    client_instance.inb = ""
    client_instance.receive_message()
    assert custom_called, "custom_protocol.process_message should be called for a 1.0 message"
    assert client_instance.processed_msg == "1.0 TEST custom message", "Processed message should match input"

# ------------------------------------------------------------------
# Test: Client receives a JSON protocol (2.0) message.
# ------------------------------------------------------------------
def test_client_receive_message_json(monkeypatch, client_instance):
    json_called = False
    def dummy_json_process(msg, cl):
        nonlocal json_called
        json_called = True
        cl.processed_msg = msg.strip()
    monkeypatch.setattr(json_protocol, "process_message", dummy_json_process)

    test_data = {"opcode": "TEST", "data": ["json message"]}
    test_msg = f"2.0 {json.dumps(test_data)}\n"
    client_instance.sock.recv_data = test_msg.encode("utf-8")
    client_instance.inb = ""
    client_instance.receive_message()
    assert json_called, "json_protocol.process_message should be called for a 2.0 message"
    assert client_instance.processed_msg is not None, "Processed message should be recorded"

# ------------------------------------------------------------------
# Test: Client receives an unsupported protocol message.
# ------------------------------------------------------------------
def test_client_receive_message_unsupported(monkeypatch, client_instance):
    error_called = False
    error_msg = ""
    def dummy_wrap_message(op, data):
        nonlocal error_called, error_msg
        error_called = True
        error_msg = f"2.0 ERROR {data[0]}"
        return error_msg
    monkeypatch.setattr(json_protocol, "wrap_message", dummy_wrap_message)

    test_msg = "3.0 SOME MESSAGE\n"
    client_instance.sock.recv_data = test_msg.encode("utf-8")
    client_instance.inb = ""
    client_instance.receive_message()
    assert error_called, "json_protocol.wrap_message should be called for unsupported protocol"

# ------------------------------------------------------------------
# Test: Client send_request sends correct data.
# ------------------------------------------------------------------
def test_client_send_request(client_instance):
    test_request = "1.0 TEST REQUEST"
    client_instance.sock.sent_data = b""
    client_instance.send_request(test_request)
    assert test_request.encode("utf-8") in client_instance.sock.sent_data, \
           "The request should be sent via the socket"

# ------------------------------------------------------------------
# Test: Client close unregisters socket and closes it.
# ------------------------------------------------------------------
def test_client_close(monkeypatch, client_instance):
    from client import client as client_module
    monkeypatch.setattr(client_module.sel, "unregister", lambda sock: None)
    client_instance.close()
    assert client_instance.sock.closed, "Socket should be closed after calling close()"

# ------------------------------------------------------------------
# Test: Client run processes one event using a real socket.
# ------------------------------------------------------------------
def test_client_run(monkeypatch):
    # Create a pair of connected sockets (which have valid file descriptors).
    parent_sock, child_sock = socket.socketpair()
    parent_sock.setblocking(False)
    child_sock.setblocking(False)

    # Create a Client instance and assign child_sock as its socket.
    cl = client.Client(host="127.0.0.1", port=9999)
    cl.sock = child_sock
    cl.inb = ""

    # Override the selector's select method to return an event with our socket.
    events = [(types.SimpleNamespace(fileobj=child_sock, data=cl), selectors.EVENT_READ)]
    monkeypatch.setattr(client.sel, "select", lambda timeout: events)

    # Override service_connection to simply record that it was called.
    run_called = False
    def dummy_service_connection(key, mask):
        nonlocal run_called
        run_called = True
    monkeypatch.setattr(cl, "service_connection", dummy_service_connection)

    cl.run()
    assert run_called, "run() should call service_connection on events"

    parent_sock.close()
    child_sock.close()
