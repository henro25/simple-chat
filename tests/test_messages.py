"""
Module Name: test_messages.py
Description: Extended unit tests for store_message(), delete_message(), and get_recent_messages() 
             to ensure messages table is updated correctly.
Author: Henry Huang and Bridget Ma
Date: 2024-2-9
"""

import os
import pytest
import sqlite3

# Change test directory to the server directory so that tests run with the proper configuration.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
server_dir = os.path.join(project_root, 'server')
os.chdir(server_dir)

from server import database
from configs.config import *

# Fixture to set up and tear down a temporary test database.
@pytest.fixture(autouse=True)
def setup_database():
    test_db = "test_chat.db"
    database.DATABASE_NAME = test_db  # Override the database name in the module

    # Remove test database file if it exists
    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize tables
    database.initialize_db()
    
    yield  # Run the tests

    # Teardown: Remove the test database after tests are finished
    if os.path.exists(test_db):
        os.remove(test_db)

# ----------------------------
# Tests for store_message
# ----------------------------

def test_store_message():
    """
    Test that store_message() correctly inserts a new message and returns its ID.
    """
    sender = "alice"
    recipient = "bob"
    message = "Hello, Bob!"
    
    msg_id = database.store_message(sender, recipient, message)

    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, sender, recipient, message FROM messages WHERE id = ?", (msg_id,))
    row = cur.fetchone()
    conn.close()

    assert row is not None, "Message should be stored in the database."
    assert row["id"] == msg_id
    assert row["sender"] == sender
    assert row["recipient"] == recipient
    assert row["message"] == message

# ----------------------------
# Tests for get_recent_messages
# ----------------------------

def test_get_recent_messages():
    """
    Test retrieving the most recent messages between two users.
    """
    sender = "alice"
    recipient = "bob"

    # Insert multiple messages
    msg1_id = database.store_message(sender, recipient, "Message 1")
    msg2_id = database.store_message(sender, recipient, "Message 2")
    msg3_id = database.store_message(recipient, sender, "Message 3")
    msg4_id = database.store_message(sender, recipient, "Message 4")

    num_unreads, messages = database.get_recent_messages(sender, recipient, limit=3)

    assert len(messages) == 3, "Should retrieve the 3 most recent messages."
    assert num_unreads == 1, "Should have 1 unread message."
    assert messages[0]["message"] == "Message 2"
    assert messages[1]["message"] == "Message 3"
    assert messages[2]["message"] == "Message 4"

def test_get_recent_messages_with_oldest_message_id():
    """
    Test fetching older messages using oldest_message_id.
    """
    sender = "alice"
    recipient = "bob"

    # Insert multiple messages
    msg1_id = database.store_message(sender, recipient, "Message A")
    msg2_id = database.store_message(sender, recipient, "Message B")
    msg3_id = database.store_message(sender, recipient, "Message C")
    msg4_id = database.store_message(sender, recipient, "Message D")

    # Fetch messages before msg3_id
    num_unreads, older_messages = database.get_recent_messages(sender, recipient, limit=2, oldest_msg_id=msg3_id)

    assert len(older_messages) == 2, "Should fetch 2 older messages."
    assert older_messages[0]["message"] == "Message A"
    assert older_messages[1]["message"] == "Message B"

def test_get_recent_messages_empty():
    """
    Test retrieving messages when no conversation exists.
    """
    num_unreads, messages = database.get_recent_messages("nonexistent_user", "other_user", limit=5)
    assert messages == [], "Should return an empty list when no messages exist."
    assert num_unreads == 0, "Should have 0 unread messages."

# ----------------------------
# Tests for delete_message
# ----------------------------

def test_delete_message():
    """
    Test that delete_message() removes a message from the database.
    """
    sender = "alice"
    recipient = "bob"
    message = "This message will be deleted."
    
    # Store a message
    msg_id = database.store_message(sender, recipient, message)

    # Ensure the message exists before deletion
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg_id,))
    assert cur.fetchone()[0] == 1, "Message should exist before deletion."
    conn.close()

    # Delete the message
    recp, sndr, unread_status, error_code = database.delete_message(msg_id)
    assert recp, "Message should be successfully deleted."
    assert recp == recipient, "Should return correct recipient"
    assert sndr == sender, "Should return correct sender"
    assert unread_status == 1, "Should return correct unread status"
    assert error_code == SUCCESS, "Should return correct message ID"

    # Ensure the message is removed
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg_id,))
    assert cur.fetchone()[0] == 0, "Message should be deleted from the database."
    conn.close()

def test_delete_nonexistent_message():
    """
    Test deleting a message that doesn't exist.
    """
    recipient, sender, unread_status, error_code = database.delete_message(99999)
    assert not recipient, "Should return False when deleting a nonexistent message."
    assert not sender, "Should return False when deleting a nonexistent message."
    assert not unread_status, "Should return False when deleting a nonexistent message."
    assert error_code == ID_DNE, "Should return correct error code for nonexistent ID."

def test_delete_multiple_messages():
    """
    Test deleting multiple messages one after another.
    """
    sender = "alice"
    recipient = "bob"

    msg1_id = database.store_message(sender, recipient, "Message 1")
    msg2_id = database.store_message(sender, recipient, "Message 2")
    msg3_id = database.store_message(sender, recipient, "Message 3")

    assert database.delete_message(msg1_id)[0], "Message 1 should be deleted."
    assert database.delete_message(msg2_id)[0], "Message 2 should be deleted."
    assert database.delete_message(msg3_id)[0], "Message 3 should be deleted."

    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE sender = ?", (sender,))
    assert cur.fetchone()[0] == 0, "All messages from sender should be deleted."
    conn.close()

# ----------------------------
# Additional Tests
# ----------------------------

def test_clear_accounts_does_not_affect_messages():
    """
    Ensure that clearing accounts does not delete messages.
    """
    sender = "alice"
    recipient = "bob"
    message = "Persistent message."

    msg_id = database.store_message(sender, recipient, message)

    database.clear_accounts()  # Clear accounts but messages should remain

    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg_id,))
    assert cur.fetchone()[0] == 1, "Messages should remain after clearing accounts."
    conn.close()

