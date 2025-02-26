import pytest
import uuid
import os
import grpc
import time
import threading
import chat_service_pb2
import chat_service_pb2_grpc
from concurrent import futures
from configs.config import SUCCESS, LGN_PG, REG_PG, USER_LOGGED_ON
from server import database, utils

from server.protocols.grpc_server_protocol import MyChatService

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
server_dir = os.path.join(project_root, 'server')
os.chdir(server_dir)

###################################
# Fixtures for Integration Testing
###################################

@pytest.fixture(scope="module")
def grpc_server():
    """
    Sets up a real gRPC server for integration tests, 
    then yields its address for the test to connect to.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_service_pb2_grpc.add_ChatServiceServicer_to_server(MyChatService(), server)
    port = server.add_insecure_port("[::]:50051")
    server.start()
    yield f"localhost:{port}"
    server.stop(None)


@pytest.fixture(scope="module")
def grpc_stub(grpc_server):
    """
    Creates a gRPC channel and stub for integration testing.
    """
    channel = grpc.insecure_channel(grpc_server)
    return chat_service_pb2_grpc.ChatServiceStub(channel)


###################################
# Database & Active Clients Reset
###################################

@pytest.fixture(autouse=True)
def setup_teardown_db():
    """
    Ensures each test uses a fresh database and empty active_clients dict.
    """
    test_db_name = "int_test_chat.db"
    database.DATABASE_NAME = test_db_name

    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    # Initialize DB
    database.initialize_db()

    # Pre-populate the accounts table.
    accounts = [
        ("workflow2", "secret"),
    ]
    for username, pwd in accounts:
        database.register_account(username, pwd)

    yield

    # Cleanup
    if os.path.exists(test_db_name):
        os.remove(test_db_name)

    utils.active_clients.clear()
    utils.rpc_send_queue.clear()


###################################
# Helper Functions
###################################

def do_register(stub, username, password, ip="127.0.0.1", port=5000):
    """
    Convenience function to register a user via gRPC.
    """
    req = chat_service_pb2.RegisterRequest(username=username, password=password, ip_address=ip, port=port)
    return stub.Register(req)

def do_login(stub, username, password, ip="127.0.0.1", port=5000):
    """
    Convenience function to log a user in via gRPC.
    """
    req = chat_service_pb2.LoginRequest(username=username, password=password, ip_address=ip, port=port)
    return stub.Login(req)

def do_send_message(stub, sender, recipient, text):
    """
    Send a message from 'sender' to 'recipient' via gRPC.
    """
    return stub.SendMessage(chat_service_pb2.SendMessageRequest(sender=sender, recipient=recipient, text=text))

def do_get_chat_history(stub, username, other_user, num_msgs=10, oldest_msg_id=-1):
    """
    Fetch chat history from 'username' perspective with 'other_user'.
    """
    req = chat_service_pb2.ChatHistoryRequest(
        username=username, other_user=other_user, num_msgs=num_msgs, oldest_msg_id=oldest_msg_id
    )
    return stub.GetChatHistory(req)

def do_delete_message(stub, msg_id):
    """
    Delete a message by its msg_id.
    """
    return stub.DeleteMessage(chat_service_pb2.DeleteMessageRequest(msg_id=msg_id))

def do_delete_account(stub, username):
    """
    Delete an account by username.
    """
    return stub.DeleteAccount(chat_service_pb2.DeleteAccountRequest(username=username))


###################################
# Actual Integration Tests
###################################

def test_full_workflow_register(grpc_stub):
    """
    Tests a full user workflow:
    1) Register user
    2) Send message
    3) Fetch chat history
    4) Delete message
    5) Delete account
    """
    username = "workflow_user"
    password = "secret"

    # Register
    reg_resp = do_register(grpc_stub, username, password)
    assert reg_resp.errno == 0
    assert reg_resp.page_code == REG_PG
    assert reg_resp.client_username == username

    # Send message to 'bob'
    database.register_account("bob", "hash2")
    send_resp = do_send_message(grpc_stub, username, "bob", "Hello Bob from Workflow Test!")
    assert send_resp.errno == 0
    assert send_resp.msg_id > 0

    # Fetch chat history
    hist_resp = do_get_chat_history(grpc_stub, username, "bob")
    assert hist_resp.errno == 0
    assert len(hist_resp.chat_history) == 1
    last_msg = hist_resp.chat_history[0]
    assert last_msg.text == "Hello Bob from Workflow Test!"

    # Delete message
    del_msg_resp = do_delete_message(grpc_stub, last_msg.msg_id)
    assert del_msg_resp.errno == 0

    # Delete account
    del_acc_resp = do_delete_account(grpc_stub, username)
    assert del_acc_resp.errno == 0

def test_full_workflow_login(grpc_stub):
    """
    Tests a full user workflow:
    1) Login user
    2) Send message
    3) Fetch chat history
    4) Delete message
    5) Delete account
    """
    username = "workflow2"
    password = "secret"

    # Register
    reg_resp = do_login(grpc_stub, username, password)
    assert reg_resp.errno == 0
    assert reg_resp.page_code == LGN_PG
    assert reg_resp.client_username == username

    # Send message to 'bob'
    database.register_account("charlie", "hash3")
    send_resp = do_send_message(grpc_stub, username, "charlie", "Hello Charlie from Workflow Test!")
    assert send_resp.errno == 0
    assert send_resp.msg_id > 0

    # Fetch chat history
    hist_resp = do_get_chat_history(grpc_stub, username, "charlie")
    assert hist_resp.errno == 0
    assert len(hist_resp.chat_history) == 1
    last_msg = hist_resp.chat_history[0]
    assert last_msg.text == "Hello Charlie from Workflow Test!"

    # Delete message
    del_msg_resp = do_delete_message(grpc_stub, last_msg.msg_id)
    assert del_msg_resp.errno == 0

    # Delete account
    del_acc_resp = do_delete_account(grpc_stub, username)
    assert del_acc_resp.errno == 0


def test_concurrent_users(grpc_stub):
    """
    Tests that multiple users can register, login, and send messages concurrently.
    """
    users = [("alice", "pw1"), ("bob", "pw2"), ("charlie", "pw3")]
    
    def register_and_login(username, password, port):
        reg_r = do_register(grpc_stub, username, password, port=port)
        assert reg_r.errno == 0

    threads = []
    for i, (u, p) in enumerate(users):
        t = threading.Thread(target=register_and_login, args=(u,p,5000+i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # All three should be in active_clients
    assert "alice" in utils.active_clients
    assert "bob" in utils.active_clients
    assert "charlie" in utils.active_clients

    # Let's have them send messages to each other
    do_send_message(grpc_stub, "alice", "bob", "Hello Bob!")
    do_send_message(grpc_stub, "bob", "charlie", "Hello Charlie!")
    do_send_message(grpc_stub, "charlie", "alice", "Hello Alice!")

    # Check chat histories
    hist_alice_bob = do_get_chat_history(grpc_stub, "alice", "bob")
    assert len(hist_alice_bob.chat_history) == 1
    assert hist_alice_bob.chat_history[0].text == "Hello Bob!"

    hist_bob_charlie = do_get_chat_history(grpc_stub, "bob", "charlie")
    assert len(hist_bob_charlie.chat_history) == 1
    assert hist_bob_charlie.chat_history[0].text == "Hello Charlie!"

    hist_charlie_alice = do_get_chat_history(grpc_stub, "charlie", "alice")
    assert len(hist_charlie_alice.chat_history) == 1
    assert hist_charlie_alice.chat_history[0].text == "Hello Alice!"


def test_invalid_login_after_registration(grpc_stub):
    """
    Tests logging in with the wrong password immediately after a successful registration.
    """
    username = "invloginuser"
    password = "correctpw"
    # Register
    reg_resp = do_register(grpc_stub, username, password)
    assert reg_resp.errno == 0

    # Attempt to login with wrong password
    bad_login_resp = do_login(grpc_stub, username, "wrongpw")
    # Should fail
    assert bad_login_resp.errno != 0


def test_send_message_nonexistent_recipient(grpc_stub):
    """
    Tests sending a message to a user that doesn't exist in DB or is deactivated.
    """
    # Register & login the sender
    sender = "sender"
    database.register_account(sender, "pw")
    login_r = do_login(grpc_stub, sender, "pw")
    assert login_r.errno == 0

    # Attempt to send to nonexistent user
    resp = do_send_message(grpc_stub, sender, "ghostuser", "Hi ghost!")
    # If the server sets msg_id=-1 or errno=0 but indicates failure some other way,
    # adapt these checks to your actual behavior.
    assert resp.errno == 0  # Server might be returning 0
    assert resp.msg_id == -1  # Usually a sign that recipient doesn't exist


def test_large_chat_history_fetch(grpc_stub):
    """
    Tests fetching a large chat history. We'll insert many messages manually 
    to ensure the server can handle large retrievals.
    """
    user = "bigHistoryUser"
    password = "pw"
    do_register(grpc_stub, user, password)
    do_login(grpc_stub, user, password)

    # Insert many messages from "alice" => "bigHistoryUser"
    database.register_account("alice", "pw2")
    for i in range(50):
        do_send_message(grpc_stub, "alice", user, f"Message number {i}")

    hist_resp = do_get_chat_history(grpc_stub, user, "alice", num_msgs=50)
    assert hist_resp.errno == 0
    # If your server returns only the last X messages, check accordingly
    assert len(hist_resp.chat_history) == 50


def test_delete_account_in_use(grpc_stub):
    """
    Tests attempting to delete an account that's actively in conversation.
    Ensures the server handle doesn't break any references 
    or push updates to a removed user.
    """
    user = "accInUse"
    pwd = "pw"
    do_register(grpc_stub, user, pwd)
    do_login(grpc_stub, user, pwd)

    # Another user that will talk to 'accInUse'
    database.register_account("another", "pw2")

    # Send message from another => 'accInUse'
    do_send_message(grpc_stub, "another", user, "Hello in-use user")

    # Now delete 'accInUse'
    del_acc_resp = do_delete_account(grpc_stub, user)
    assert del_acc_resp.errno == 0

    # Attempt to send message to 'accInUse' again
    msg_resp = do_send_message(grpc_stub, "another", user, "Should fail or produce msg_id=-1")
    # If your server sets msg_id = -1 for invalid recipients:
    assert msg_resp.msg_id == -1

    # Confirm 'accInUse' not in active_clients
    assert user not in utils.active_clients


def test_live_updates_multiuser(grpc_stub):
    """
    Integration test with multiple concurrent streaming clients. 
    Verifies that each user receives the correct updates for multiple messages.
    """
    # Register all users
    users = ["liveU1", "liveU2"]
    for u in users:
        do_register(grpc_stub, u, "pw")
        do_login(grpc_stub, u, "pw")

    # We'll store the results of each user's push updates
    user_updates = {u: 0 for u in users}

    def request_generator(username):
        # The client "subscribes" for updates
        yield chat_service_pb2.LiveUpdateRequest(username=username)

    def stream_updates(user):
        # Start streaming for this user
        resp_stream = grpc_stub.UpdateStream(request_generator(user))
        for resp in resp_stream:
            update_type = resp.WhichOneof("update")
            if update_type == "push_message":
                user_updates[user] += 1
                if user_updates[user] >= 2:
                    # For brevity, once we get 2 updates, break.
                    break

    # Start threads for each user
    threads = []
    for u in users:
        t = threading.Thread(target=stream_updates, args=(u,))
        threads.append(t)
        t.start()
        time.sleep(0.2)  # small delay to let them subscribe

    # Send messages to each user
    do_send_message(grpc_stub, "liveU1", "liveU2", "Hello from user1 -> user2 #1")
    do_send_message(grpc_stub, "liveU2", "liveU1", "Hello from user2 -> user1 #1")
    do_send_message(grpc_stub, "liveU1", "liveU2", "Hello from user1 -> user2 #2")
    do_send_message(grpc_stub, "liveU2", "liveU1", "Hello from user2 -> user1 #2")

    for t in threads:
        t.join(timeout=3.0)

    # Each user should have at least 2 updates
    assert user_updates["liveU1"] >= 2
    assert user_updates["liveU2"] >= 2
