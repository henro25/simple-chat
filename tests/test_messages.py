"""
Module Name: test_messages.py
Description: Unit tests for store_message(), delete_message(), and get_recent_messages() 
             to ensure messages table is updated correctly.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
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

# ----------------------------
# Setup and Teardown
# ----------------------------

@pytest.fixture(autouse=True)
def setup_database():
    """
    Pytest fixture to set up and tear down a temporary test database.
    """
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
    Test that store_message() correctly inserts a new message.
    """
    sender = "alice"
    recipient = "bob"
    message = "Hello, Bob!"
    
    database.store_message(sender, recipient, message)

    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT sender, recipient, message FROM messages WHERE sender = ? AND recipient = ?", (sender, recipient))
    row = cur.fetchone()
    conn.close()

    assert row is not None, "Message should be stored in the database."
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
    database.store_message(sender, recipient, "Message 1")
    database.store_message(sender, recipient, "Message 2")
    database.store_message(recipient, sender, "Message 3")
    database.store_message(sender, recipient, "Message 4")

    messages = database.get_recent_messages(sender, recipient, limit=3)
    print(messages)

    assert len(messages) == 3, "Should retrieve the 3 most recent messages."
    assert messages[0]["message"] == "Message 2"
    assert messages[1]["message"] == "Message 3"
    assert messages[2]["message"] == "Message 4"

# ----------------------------
# Tests for delete_message
# ----------------------------

def test_delete_messages():
    """
    Test that delete_message() removes a message from the database.
    """
    sender = "alice"
    recipient = "bob"
    message = "This message will be deleted."
    
    # Store a message
    database.store_message(sender, recipient, message)

    # Retrieve the message ID
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM messages WHERE sender = ? AND message = ?", (sender, message))
    msg_id = cur.fetchone()["id"]
    conn.close()

    # Ensure the message exists before deletion
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg_id,))
    assert cur.fetchone()[0] == 1, "Message should exist before deletion."
    conn.close()

    # Delete the message
    assert database.delete_message(msg_id), "Message should be successfully deleted."

    # Ensure the message is removed
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM messages WHERE id = ?", (msg_id,))
    assert cur.fetchone()[0] == 0, "Message should be deleted from the database."
    conn.close()
