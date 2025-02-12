# """
# Module Name: test_server.py
# Description: Unit tests for the server module. These tests simulate client connections
#              (with custom protocol, JSON protocol, unsupported protocol, disconnection, and
#              write events) by using dummy socket objects and fake selector keys.
# Author: Henry Huang and Bridget Ma
# Date: 2024-2-6
# """

# import json
# import selectors
# import socket
# import types
# import pytest

# from server import server
# from server import protocols
# from server.protocols import custom_protocol, json_protocol
# from server.utils import active_clients
# from configs.config import UNSUPPORTED_VERSION, debug

# # ------------------------------------------------------------------
# # DummySocket class to simulate a client socket.
# # ------------------------------------------------------------------
# class DummySocket:
#     def __init__(self, recv_data=b""):
#         # recv_data: bytes to be returned once on recv() call.
#         self.recv_data = recv_data
#         self.sent_data = b""
#         self.closed = False

#     def recv(self, bufsize):
#         # Return the preset recv_data once, then empty bytes.
#         if self.recv_data:
#             data = self.recv_data
#             self.recv_data = b""
#             return data
#         return b""

#     def send(self, data):
#         self.sent_data += data
#         return len(data)

#     def setblocking(self, flag):
#         pass

#     def close(self):
#         self.closed = True

# # ------------------------------------------------------------------
# # Fixture to clear active_clients and reset the selector between tests.
# # ------------------------------------------------------------------
# @pytest.fixture(autouse=True)
# def clear_active_clients_and_selector():
#     active_clients.clear()
#     # Reset the global selector used in the server.
#     server.sel.close()
#     server.sel = selectors.DefaultSelector()
#     yield
#     active_clients.clear()

# # ------------------------------------------------------------------
# # Test: Custom Protocol LOGIN via service_connection (EVENT_READ then EVENT_WRITE)
# # ------------------------------------------------------------------
# def test_service_connection_custom_login():
#     # Prepare a custom protocol LOGIN message.
#     # (Assumes "alice" is a registered account with password "hash1".)
#     msg = "1.0 LOGIN alice hash1\n".encode("utf-8")
#     dummy_sock = DummySocket(recv_data=msg)
#     key = types.SimpleNamespace(
#         fileobj=dummy_sock,
#         data=types.SimpleNamespace(addr=("127.0.0.1", 12345), inb=b"", outb=b"", username=None)
#     )
    
#     # Process the incoming message.
#     server.service_connection(key, selectors.EVENT_READ)
    
#     # After processing, the custom protocol handler should have set the username.
#     assert key.data.username == "alice", "Username should be set to 'alice' after LOGIN."
#     # The socket should be registered in active_clients.
#     assert "alice" in active_clients and active_clients["alice"] == dummy_sock
    
#     # A response should be queued in outb.
#     assert key.data.outb != b"", "A response should be placed in outb."
    
#     # Now simulate a write event: send the queued data.
#     server.service_connection(key, selectors.EVENT_WRITE)
#     # After writing, outb should be empty.
#     assert key.data.outb == b"", "After sending, outb should be empty."
#     # And the dummy socket should have recorded the sent data.
#     assert dummy_sock.sent_data != b"", "Data should have been sent via the dummy socket."

# # ------------------------------------------------------------------
# # Test: JSON Protocol LOGIN via service_connection.
# # ------------------------------------------------------------------
# def test_service_connection_json_login():
#     # Prepare a JSON protocol LOGIN message.
#     login_data = {"opcode": "LOGIN", "data": ["alice", "hash1"]}
#     msg = f"2.0 {json.dumps(login_data)}\n".encode("utf-8")
#     dummy_sock = DummySocket(recv_data=msg)
#     key = types.SimpleNamespace(
#         fileobj=dummy_sock,
#         data=types.SimpleNamespace(addr=("127.0.0.1", 23456), inb=b"", outb=b"", username=None)
#     )
    
#     server.service_connection(key, selectors.EVENT_READ)
    
#     assert key.data.username == "alice", "Username should be set to 'alice' for JSON LOGIN."
#     assert "alice" in active_clients and active_clients["alice"] == dummy_sock
#     assert key.data.outb != b"", "A JSON response should be queued in outb."
    
#     # Simulate writing the response.
#     server.service_connection(key, selectors.EVENT_WRITE)
#     assert key.data.outb == b"", "After write, outb should be empty."
#     assert dummy_sock.sent_data != b"", "Dummy socket should have recorded sent data."

# # ------------------------------------------------------------------
# # Test: Unsupported protocol version should return an error message.
# # ------------------------------------------------------------------
# def test_service_connection_unsupported_protocol():
#     # A message with an unsupported protocol version (e.g., "3.0 ...").
#     msg = "3.0 SOMETHING\n".encode("utf-8")
#     dummy_sock = DummySocket(recv_data=msg)
#     key = types.SimpleNamespace(
#         fileobj=dummy_sock,
#         data=types.SimpleNamespace(addr=("127.0.0.1", 34567), inb=b"", outb=b"", username=None)
#     )
    
#     server.service_connection(key, selectors.EVENT_READ)
    
#     # The server should reply with an error using the JSON protocol wrapper.
#     expected_error = json_protocol.wrap_message("ERROR", [str(UNSUPPORTED_VERSION)]).encode("utf-8") + b"\n"
#     assert expected_error in key.data.outb, "Expected error message for unsupported protocol not found."

# # ------------------------------------------------------------------
# # Test: Connection disconnection (simulate recv() returning empty bytes).
# # ------------------------------------------------------------------
# def test_service_connection_disconnect(monkeypatch):
#     # Simulate a connected user ("alice") who then disconnects.
#     dummy_sock = DummySocket(recv_data=b"")
#     key = types.SimpleNamespace(
#         fileobj=dummy_sock,
#         data=types.SimpleNamespace(addr=("127.0.0.1", 45678), inb=b"", outb=b"", username="alice")
#     )
#     active_clients["alice"] = dummy_sock

#     # Monkeypatch the selector's unregister to capture its call.
#     unregister_called = False
#     def fake_unregister(sock):
#         nonlocal unregister_called
#         unregister_called = True
#     monkeypatch.setattr(server.sel, "unregister", fake_unregister)
    
#     server.service_connection(key, selectors.EVENT_READ)
    
#     # Since recv() returned empty, the connection should be closed.
#     assert dummy_sock.closed, "Socket should be closed on disconnect."
#     # The user should be removed from active_clients.
#     assert "alice" not in active_clients, "User 'alice' should be removed from active_clients on disconnect."
#     # The selector's unregister should have been called.
#     assert unregister_called, "Selector.unregister should have been called on disconnect."

# # ------------------------------------------------------------------
# # Test: Write event processing.
# # ------------------------------------------------------------------
# def test_service_connection_write_event():
#     # Create a dummy key where data.outb is pre-populated with a test message.
#     dummy_sock = DummySocket()
#     test_message = b"Test message"
#     key = types.SimpleNamespace(
#         fileobj=dummy_sock,
#         data=types.SimpleNamespace(addr=("127.0.0.1", 56789), inb=b"", outb=test_message, username="bob")
#     )
    
#     server.service_connection(key, selectors.EVENT_WRITE)
    
#     # The dummy socket should have sent the test message.
#     assert test_message in dummy_sock.sent_data, "Dummy socket should have sent the test message."
#     # After sending, outb should be empty.
#     assert key.data.outb == b"", "After write event, outb should be empty."
