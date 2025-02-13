"""
Module Name: test_client.py
Description: Unit tests for the client module. These tests simulate receiving
             messages from the server (using both 1.0 and 2.0 protocols as well as
             unsupported versions), sending requests, closing the connection, and
             running the client's event loop. Extended tests include random message 
             generation, multiple messages, and partial message delivery.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import json
import random
import selectors
import socket
import string
import types
import pytest

from client import client
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
# Existing tests...
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

def test_client_send_request(client_instance):
    test_request = "1.0 TEST REQUEST"
    client_instance.sock.sent_data = b""
    client_instance.send_request(test_request)
    assert test_request.encode("utf-8") in client_instance.sock.sent_data, \
           "The request should be sent via the socket"

def test_client_close(monkeypatch, client_instance):
    from client import client as client_module
    monkeypatch.setattr(client_module.sel, "unregister", lambda sock: None)
    client_instance.close()
    assert client_instance.sock.closed, "Socket should be closed after calling close()"

def test_client_run(monkeypatch):
    parent_sock, child_sock = socket.socketpair()
    parent_sock.setblocking(False)
    child_sock.setblocking(False)

    cl = client.Client(host="127.0.0.1", port=9999)
    cl.sock = child_sock
    cl.inb = ""
    events = [(types.SimpleNamespace(fileobj=child_sock, data=cl), selectors.EVENT_READ)]
    monkeypatch.setattr(client.sel, "select", lambda timeout: events)

    run_called = False
    def dummy_service_connection(key, mask):
        nonlocal run_called
        run_called = True
    monkeypatch.setattr(cl, "service_connection", dummy_service_connection)

    cl.run()
    assert run_called, "run() should call service_connection on events"
    parent_sock.close()
    child_sock.close()

# ------------------------------------------------------------------
# Additional Randomized Tests for Custom Protocol Messages
# ------------------------------------------------------------------
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def test_client_receive_random_custom_messages(monkeypatch, client_instance):
    # Generate 5 random custom messages.
    messages = []
    for _ in range(5):
        msg = "1.0 RANDOM " + random_string(12)
        messages.append(msg)
    combined = "\n".join(messages) + "\n"
    call_count = 0
    processed_msgs = []
    def dummy_custom_process(msg, cl):
        nonlocal call_count, processed_msgs
        call_count += 1
        processed_msgs.append(msg.strip())
    monkeypatch.setattr(custom_protocol, "process_message", dummy_custom_process)
    
    client_instance.sock.recv_data = combined.encode("utf-8")
    client_instance.inb = ""
    client_instance.receive_message()
    assert call_count == 5, f"Should process 5 random custom messages, got {call_count}"
    for orig, proc in zip(messages, processed_msgs):
        assert orig.strip() == proc, "Random custom message mismatch"

def test_client_receive_random_json_messages(monkeypatch, client_instance):
    messages = []
    for _ in range(5):
        data = {"opcode": "RANDOM", "data": [random_string(8)]}
        msg = "2.0 " + json.dumps(data)
        messages.append(msg)
    combined = "\n".join(messages) + "\n"
    call_count = 0
    processed_msgs = []
    def dummy_json_process(msg, cl):
        nonlocal call_count, processed_msgs
        call_count += 1
        processed_msgs.append(msg.strip())
    monkeypatch.setattr(json_protocol, "process_message", dummy_json_process)
    
    client_instance.sock.recv_data = combined.encode("utf-8")
    client_instance.inb = ""
    client_instance.receive_message()
    assert call_count == 5, f"Should process 5 random JSON messages, got {call_count}"
    for orig, proc in zip(messages, processed_msgs):
        assert orig.strip() == proc, "Random JSON message mismatch"

def test_client_receive_partial_random_message(monkeypatch, client_instance):
    # Generate one random custom message.
    full_message = "1.0 RANDOM " + random_string(15) + "\n"
    # Choose a random split point.
    split_point = random.randint(1, len(full_message)-1)
    part1 = full_message[:split_point]
    part2 = full_message[split_point:]
    
    call_count = 0
    processed_msgs = []
    def dummy_custom_process(msg, cl):
        nonlocal call_count, processed_msgs
        call_count += 1
        processed_msgs.append(msg.strip())
    monkeypatch.setattr(custom_protocol, "process_message", dummy_custom_process)
    
    client_instance.sock.recv_data = part1.encode("utf-8")
    client_instance.inb = ""
    client_instance.receive_message()
    # No complete message should be processed yet.
    assert call_count == 0, "No message should be processed until a newline is received"
    
    # Now simulate receiving the rest.
    client_instance.sock.recv_data = part2.encode("utf-8")
    client_instance.receive_message()
    assert call_count == 1, "Message should be processed after completing the partial input"
    assert processed_msgs[0] == full_message.strip(), "The reassembled message should match the full message"

# ------------------------------------------------------------------
# Additional Randomized Test for send_request
# ------------------------------------------------------------------
def test_client_send_request_random(client_instance):
    rand_request = "1.0 " + random_string(20)
    client_instance.sock.sent_data = b""
    client_instance.send_request(rand_request)
    assert rand_request.encode("utf-8") in client_instance.sock.sent_data, \
           "Randomly generated request should be sent via the socket"
