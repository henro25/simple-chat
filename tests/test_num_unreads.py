"""
Module Name: test_num_unreads.py
Description: Unit tests for get_conversations(), get_num_unread(), and mark_message_as_read()
             to ensure that the messages table and unread counts are handled correctly.
Author: Henry Huang and Bridget Ma (extended by ChatGPT)
Date: 2024-2-7 (extended 2025-02-12)
"""

import os
import random
import time
import pytest

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
    # Override the database filename in the database module.
    database.DATABASE_NAME = test_db

    # Remove the test database file if it already exists.
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize the database (this should create the accounts and messages tables).
    database.initialize_db()
    
    # Pre-populate the accounts table for testing.
    accounts = [
        ("alice", "hash1"),
        ("bob", "hash2"),
        ("charlie", "hash3"),
        ("david", "hash4")
    ]
    for username, pwd in accounts:
        database.register_account(username, pwd)
    
    yield  # Run the tests.
    
    # Teardown: Remove the test database after tests are finished.
    if os.path.exists(test_db):
        os.remove(test_db)

# ===============================
# Tests for get_num_unread
# ===============================

def test_get_num_unread_no_entries():
    """
    Test that get_num_unread() returns 0 when there are no messages.
    """
    recipient = "alice"
    # No messages inserted, so total unread should be 0.
    unread_count = database.get_num_unread(recipient)
    assert unread_count == 0, "Expected 0 unread messages when no messages exist."

def test_get_num_unread_with_multiple_senders():
    """
    Test that get_num_unread() returns the correct sum when there are messages from multiple senders.
    """
    recipient = "alice"
    # Simulate 2 messages from bob and 3 messages from charlie.
    for _ in range(2):
        database.store_message("bob", recipient, "Hello from bob")
    for _ in range(3):
        database.store_message("charlie", recipient, "Hello from charlie")
    
    # get_num_unread() should sum the unread messages.
    unread_count = database.get_num_unread(recipient)
    assert unread_count == 5, f"Expected 5 unread messages, got {unread_count}"

def test_get_num_unread_after_multiple_messages_same_sender():
    """
    Test that get_num_unread() returns the correct count when multiple messages come from the same sender.
    """
    recipient = "alice"
    sender = "david"
    # Simulate 1 message and then 4 more messages from david.
    database.store_message(sender, recipient, "Message 1")
    for _ in range(4):
        database.store_message(sender, recipient, "Another message")
    
    unread_count = database.get_num_unread(recipient)
    assert unread_count == 5, f"Expected 5 unread messages, got {unread_count}"

def test_mark_message_as_read():
    """
    Test that marking a message as read properly reduces the unread count.
    """
    recipient = "alice"
    sender = "bob"
    
    # Insert one message from bob to alice.
    msg_id = database.store_message(sender, recipient, "Please read me")
    # Unread count should be 1.
    assert database.get_num_unread(recipient) == 1, "Expected unread count of 1."
    
    # Mark the message as read.
    database.mark_message_as_read(msg_id)
    # Now the unread count should be 0.
    assert database.get_num_unread(recipient) == 0, "Expected unread count of 0 after marking as read."

def test_mark_message_as_read_nonexistent():
    """
    Test that attempting to mark a nonexistent message as read does not cause an error.
    """
    # Try marking a message id that doesn't exist.
    try:
        database.mark_message_as_read(9999)
    except Exception as e:
        pytest.fail(f"mark_message_as_read() raised an exception on a non-existent message: {e}")

# ====================================
# Randomized and Edge Case Tests
# ====================================

def test_get_num_unread_random():
    """
    Randomly insert messages from various senders to a recipient and randomly mark some as read.
    Verify that get_num_unread() returns the expected sum.
    """
    recipient = "alice"
    senders = ["bob", "charlie", "david"]
    expected_unread = {sender: 0 for sender in senders}
    # Keep a record of message ids per sender.
    message_ids = {sender: [] for sender in senders}
    iterations = 20

    # Randomly insert between 0 and 5 messages per iteration.
    for _ in range(iterations):
        sender = random.choice(senders)
        count = random.randint(0, 5)
        for _ in range(count):
            msg_id = database.store_message(sender, recipient, f"Random message from {sender}")
            message_ids[sender].append(msg_id)
            expected_unread[sender] += 1
        # Sleep a tiny bit to ensure different timestamps.
        time.sleep(0.01)
    
    # Now, randomly mark some messages as read.
    for sender in senders:
        # With 50% chance mark each message as read.
        for msg_id in message_ids[sender]:
            if random.random() < 0.5:
                database.mark_message_as_read(msg_id)
                expected_unread[sender] -= 1

    total_expected = sum(expected_unread.values())
    unread_count = database.get_num_unread(recipient)
    assert unread_count == total_expected, f"Expected total unread {total_expected}, got {unread_count}"

def test_get_conversations_with_unread():
    """
    Test that get_conversations() returns:
      1. Unread conversations (from messages table) sorted by last message timestamp descending.
      2. Then, all other accounts (with 0 unread) sorted alphabetically.
    """
    recipient = "alice"
    # Simulate unread messages from 'david' and 'charlie'.
    # Insert 2 messages from david and 5 from charlie.
    for _ in range(2):
        database.store_message("david", recipient, "Message from david")
    for _ in range(5):
        database.store_message("charlie", recipient, "Message from charlie")
    
    # To simulate different timestamps, update one sender's messages so that "david" appears more recent.
    conn = database.get_db_connection()
    cur = conn.cursor()
    # Update the latest message from david by setting its timestamp 1 minute in the future.
    cur.execute("""
        UPDATE messages 
        SET timestamp = datetime('now', '+1 minute')
        WHERE id = (SELECT MAX(id) FROM messages WHERE sender = ? AND recipient = ?)
    """, ("david", recipient))
    conn.commit()
    conn.close()
    
    # Now get conversations for alice.
    conversations = database.get_conversations(recipient)
    # The expected ordering:
    #   * Unread conversations first: "david" (with 2 unread, more recent) then "charlie" (with 5 unread).
    #   * Then remaining account "bob" (0 unread).
    expected = [
        ("david", 2),
        ("charlie", 5),
        ("bob", 0)
    ]
    assert conversations == expected, f"Expected conversations {expected}, got {conversations}"

def test_get_conversations_with_no_previous_messages():
    """
    Test that get_conversations() returns all accounts (except the recipient) with 0 unread messages
    when no messages have been sent.
    """
    recipient = "alice"
    conversations = database.get_conversations(recipient)
    # Expected: All accounts except "alice", sorted alphabetically, all with unread count 0.
    expected = [
        ("bob", 0),
        ("charlie", 0),
        ("david", 0)
    ]
    assert conversations == expected, f"Expected conversations {expected}, got {conversations}"

def test_get_num_unread_edge_case_read_messages():
    """
    Insert messages that are already marked as read and verify that they are not counted.
    """
    recipient = "alice"
    sender = "bob"
    # Insert a message.
    msg_id = database.store_message(sender, recipient, "Already read message")
    # Immediately mark it as read.
    database.mark_message_as_read(msg_id)
    
    # get_num_unread should not count this message.
    unread_count = database.get_num_unread(recipient)
    assert unread_count == 0, "Expected unread count of 0 for messages that are already read."
