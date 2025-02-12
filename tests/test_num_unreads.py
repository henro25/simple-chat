"""
Module Name: test_num_unreads.py
Description: Unit tests for get_conversations() and update_num_unread() to ensure num_unread_msgs table is updated correctly.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

import os
import pytest

# Change test directory to the server directory so that tests run with the proper configuration.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
server_dir = os.path.join(project_root, 'server')
os.chdir(server_dir)

from server import database
from configs.config import *

# Use a pytest fixture to set up and tear down a temporary test database.
@pytest.fixture(autouse=True)
def setup_database():
    test_db = "test_chat.db"
    # Override the database filename in the database module.
    database.DATABASE_NAME = test_db

    # Remove the test database file if it already exists.
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize the database (which creates both the accounts and num_unread_msgs tables).
    database.initialize_db()
    
    # Pre-populate the accounts table for testing get_conversations.
    # (This list should match the accounts you expect in your tests.)
    accounts = [
        ("alice", "hash1"),
        ("bob", "hash2"),
        ("charlie", "hash3"),
        ("david", "hash4")
    ]
    for username, pwd in accounts:
        database.register_account(username, pwd)
    
    yield  # run the tests
    
    # Teardown: Remove the test database after tests are finished.
    if os.path.exists(test_db):
        os.remove(test_db)
        
# ----------------------------
# Tests for get_num_unread
# ----------------------------
        
def test_get_num_unread_no_entries():
    """
    Test that get_num_unread() returns 0 when there are no unread messages for the recipient.
    """
    recipient = "alice"
    # Since no unread messages have been added, the total should be 0.
    unread_count = database.get_num_unread(recipient)
    print(unread_count)
    assert unread_count == 0, "Expected 0 unread messages when no entries exist."

def test_get_num_unread_with_multiple_senders():
    """
    Test that get_num_unread() returns the correct sum when there are unread messages from multiple senders.
    """
    recipient = "alice"
    
    # Insert unread messages from different senders.
    database.update_num_unread(recipient, "bob", 2)
    database.update_num_unread(recipient, "charlie", 3)
    
    # The total unread should be 2 + 3 = 5.
    unread_count = database.get_num_unread(recipient)
    assert unread_count == 5, f"Expected 5 unread messages, got {unread_count}"

def test_get_num_unread_after_updates():
    """
    Test that get_num_unread() reflects the updated total after multiple updates to the same conversation.
    """
    recipient = "alice"
    sender = "david"
    
    # Insert an entry and then update it.
    database.update_num_unread(recipient, sender, 1)
    database.update_num_unread(recipient, sender, 4)
    
    # The total unread for recipient 'alice' from 'david' should now be 1 + 4 = 5.
    unread_count = database.get_num_unread(recipient)
    assert unread_count == 5, f"Expected 5 unread messages, got {unread_count}"

# ----------------------------
# Tests for update_num_unread
# ----------------------------

def test_update_num_unread_insert():
    """
    Test that update_num_unread() correctly inserts a new row when none exists.
    """
    recipient = "alice"
    sender = "bob"
    
    # Call the function to insert a record with 3 unread messages.
    database.update_num_unread(recipient, sender, 3)

    # Verify by querying the database directly.
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT unread_count FROM num_unread_msgs 
        WHERE recipient = ? AND sender = ?
    """, (recipient, sender))
    row = cur.fetchone()
    conn.close()
    
    assert row is not None, "A row should have been inserted for the conversation."
    assert row["unread_count"] == 3, "Unread count should be 3."

def test_update_num_unread_update():
    """
    Test that update_num_unread() updates an existing row by adding the new unread count.
    """
    recipient = "alice"
    sender = "charlie"
    
    # First, insert an entry with 2 unread messages.
    database.update_num_unread(recipient, sender, 2)
    
    # Now update by adding 4 more unread messages.
    database.update_num_unread(recipient, sender, 4)
    
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT unread_count FROM num_unread_msgs 
        WHERE recipient = ? AND sender = ?
    """, (recipient, sender))
    row = cur.fetchone()
    conn.close()
    
    assert row is not None, "A row should exist for the conversation."
    assert row["unread_count"] == 6, "Unread count should update to 6 (2 + 4)."

# ----------------------------
# Tests for get_conversations
# ----------------------------

def test_get_conversations_with_unread():
    """
    Test that get_conversations() returns:
      1. Unread conversations sorted by last_timestamp descending.
      2. Then, the rest of the accounts (with 0 unread messages) sorted alphabetically.
    """
    recipient = "alice"

    # Insert two unread entries for recipient "alice":
    # For conversation with "david" and "charlie".
    database.update_num_unread(recipient, "david", 2)
    database.update_num_unread(recipient, "charlie", 5)
    
    # To simulate different timestamps, update "david" so its timestamp is more recent.
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE num_unread_msgs 
        SET last_timestamp = datetime('now', '+1 minute') 
        WHERE recipient = ? AND sender = ?
    """, (recipient, "david"))
    conn.commit()
    conn.close()

    # When alice requests her conversations:
    conversations = database.get_conversations(recipient)
    
    # Expected ordering:
    # - Unread conversations first, ordered by last_timestamp descending:
    #   "david" (2 unread, more recent) then "charlie" (5 unread).
    # - Then all remaining accounts (except alice, david, and charlie) sorted alphabetically.
    # Given our accounts: ("alice", "bob", "charlie", "david"), the remaining account is "bob".
    expected = [
        ("david", 2),
        ("charlie", 5),
        ("bob", 0)
    ]
    assert conversations == expected

def test_get_conversations_with_no_previous_messages():
    """
    Test that get_conversations() returns all accounts (except the recipient)
    with an unread count of 0 when the recipient has no previous messages with anyone.
    """
    recipient = "alice"
    conversations = database.get_conversations(recipient)
    
    # Expected: All accounts except "alice", sorted alphabetically,
    # with unread count of 0.
    # Given our accounts ("alice", "bob", "charlie", "david"):
    expected = [
        ("bob", 0),
        ("charlie", 0),
        ("david", 0)
    ]
    assert conversations == expected
