"""
Module Name: database.py
Description: Contains functions and classes to manage the SQLite database, including connection management, schema initialization, and query functions (e.g., user creation, message insertion, fetching chat history and conversation lists).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import os
import sqlite3
from datetime import datetime
from configs.config import *

# Ensure that database is opened inside the /server directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_db_connection():
    """Establish and return a connection to the SQLite database."""
    conn = sqlite3.connect(os.path.join(BASE_DIR, DATABASE_NAME))
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    return conn

def initialize_db():
    """
    Create the necessary tables if they don't exist.
    This function should be called at startup.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create the accounts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deactivated INTEGER DEFAULT 0
        )
    """)
    
    # Create the messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            unread INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()

# ----------------------------
# Authentication Functions
# ----------------------------

def register_account(username, password):
    """
    Attempt to register a new account.
    
    Parameters:
      username (str): The username to register.
      password (str): The already-hashed password.
    
    Returns:
      tuple: (success: bool, errno: int)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if the username already exists.
    cur.execute("SELECT * FROM accounts WHERE username = ?", (username,))
    if cur.fetchone() is not None:
        conn.close()
        return False, USER_TAKEN
    
    # Insert the new account into the database.
    try:
        cur.execute("INSERT INTO accounts (username, password_hash) VALUES (?, ?)",
                    (username, password))
        conn.commit()
        conn.close()
        return True, SUCCESS
    except Exception as e:
        conn.close()
        return False, DB_ERROR

def verify_login(username, password):
    """
    Verify login credentials for a user.
    
    Parameters:
      username (str): The username.
      password (str): The hashed password provided by the client.
    
    Returns:
      tuple: (success: bool, errno: int)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, deactivated FROM accounts WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    
    if row is None or row["deactivated"]:
        return False, USER_DNE
    
    stored_hash = row["password_hash"]
    
    # Compare the provided password with the stored hash.
    if password == stored_hash:
        return True, SUCCESS
    else:
        return False, WRONG_PASS

def verify_valid_recipient(recipient):
    """
    Verify that the recipient's account has not been deactivated

    Parameters:
      recipient (str): The username of recipient
    
    Returns:
      int: (1 if valid recipient, 0 otherwise)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT deactivated FROM accounts WHERE username = ?", (recipient,))
    row = cur.fetchone()
    conn.close()
    
    return abs(1-row["deactivated"])

def deactivate_account(username):
    """
    Deactivate the given account

    Parameters:
      username (str): The username of the account to be deactivated
    
    Returns:
      int: errno
    """
    conn = get_db_connection()
    cur = conn.cursor()
     # Check if an entry exists for this account
    cur.execute("SELECT deactivated FROM accounts WHERE username = ?", (username,))
    row = cur.fetchone()
    error_code = SUCCESS
    if row:
        # update the deactivated column of account
        cur.execute("""
            UPDATE accounts
            SET deactivated = ? 
            WHERE username = ?
        """, (1, username))
    else:
        error_code = USER_DNE
    conn.commit()
    conn.close()
    return error_code

# ----------------------------
# Query and Update Number of Unread Messages
# ----------------------------

def get_conversations(recipient):
    """
    Retrieve a list of conversations for the given recipient.
    The result is a list of tuples in the form: (sender, unread_count).

    The ordering is as follows:
      1. Conversations with unread messages (sorted by last message timestamp, most recent first).
      2. Read conversations (sorted alphabetically by sender).
      3. Other registered accounts that haven't sent messages (sorted alphabetically).

    Parameters:
      recipient (str): The username of the recipient requesting conversations.

    Returns:
      list: A list of tuples (sender, unread_count).
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch unread conversations (sorted by last message timestamp)
    cur.execute("""
        SELECT sender, COUNT(CASE WHEN unread = 1 THEN 1 END) AS unread_count,
               MAX(timestamp) AS last_msg_time
        FROM messages
        WHERE recipient = ?
        GROUP BY sender
        HAVING unread_count > 0
        ORDER BY last_msg_time DESC
    """, (recipient,))

    unread_rows = cur.fetchall()
    unread_senders = {row["sender"] for row in unread_rows}
    # Query all other accounts (excluding the recipient and any senders already in unread_rows)
    if unread_senders:
        placeholders = ','.join('?' for _ in unread_senders)
        query = f"""
            SELECT username FROM accounts 
            WHERE username != ? 
              AND username NOT IN ({placeholders})
            ORDER BY username ASC
        """
        params = [recipient] + list(unread_senders)
    else:
        query = """
            SELECT username FROM accounts 
            WHERE username != ? 
            ORDER BY username ASC
        """
        params = [recipient]
        
    cur.execute(query, params)
    other_rows = cur.fetchall()
    conn.close()

    conversations = [(row["sender"], row["unread_count"]) for row in unread_rows]
    conversations.extend([(row["username"], 0) for row in other_rows])
    
    return conversations

def get_num_unread(user):
    """
    Get the total number of unread messages for a specific user.

    Parameters:
      user (str): The user whose unread messages should be counted.
    
    Returns:
      int: The total number of unread messages.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Sum all unread counts for the given user
    cur.execute("""
        SELECT SUM(unread) AS total_unread
        FROM messages
        WHERE recipient = ?
    """, (user,))
    row = cur.fetchone()
    conn.close()
    
    # If there are no unread messages, SUM returns None, so we return 0.
    return row["total_unread"] if row["total_unread"] is not None else 0


def mark_message_as_read(msg_id):
    """
    Update the messages table for a message to be marked as read.
    
    Parameters:
      msg_id (int): The id of message.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if an entry exists for this conversation
    cur.execute("""
        SELECT recipient FROM messages
        WHERE id = ?
    """, (msg_id,))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE messages
            SET unread = ?
            WHERE id = ?
        """, (0, msg_id))
            
    conn.commit()
    conn.close()


# ----------------------------
# Query and Update Messages
# ----------------------------

def store_message(sender, recipient, message):
    """
    Store a message in the database.

    Parameters:
        sender (str): The sender of the message.
        recipient (str): The recipient of the message
        message (str): The text content of the message.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO messages (sender, recipient, message) 
        VALUES (?, ?, ?)
    """, (sender, recipient, message))

    message_id = cur.lastrowid  # Retrieve the auto-incremented message ID
    
    conn.commit()
    conn.close()

    return message_id  # Return the message ID

def get_recent_messages(user1, user2, oldest_msg_id=-1, limit=20):
    """
    Retrieve the most recent messages exchanged between two users.

    Parameters:
        user1 (str): First username.
        user2 (str): Second username.
        oldest_msg_id (int): oldest message in client's local chat history between user1 and user2
        limit (int): Number of messages to fetch (default 20).

    Returns:
        list: A list of dictionaries containing messages.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    if oldest_msg_id == -1:
        cur.execute("""
            SELECT id, sender, recipient, message, timestamp 
            FROM messages 
            WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
            ORDER BY id DESC 
            LIMIT ?
        """, (user1, user2, user2, user1, limit))
    else:
        # Fetch older messages (before `oldest_message_id`)
        cur.execute("""
            SELECT id, sender, recipient, message, timestamp 
            FROM messages 
            WHERE ((sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?))
            AND id < ? 
            ORDER BY id DESC 
            LIMIT ?
        """, (user1, user2, user2, user1, oldest_msg_id, limit))
    
    messages = cur.fetchall()
    # Extract message IDs that need to be marked as read
    message_ids = [row["id"] for row in messages if row["recipient"] == user1]  # Only mark messages received by user1

    if message_ids:
        # Update unread status for fetched messages
        cur.execute(f"""
            UPDATE messages 
            SET unread = 0 
            WHERE id IN ({','.join(['?']*len(message_ids))})
        """, message_ids)

    conn.commit()
    conn.close()
    
    # Convert SQLite row objects to a list of dictionaries
    return [
        {"id": row["id"], "sender": row["sender"], "recipient": row["recipient"], "message": row["message"], "timestamp": row["timestamp"]}
        for row in reversed(messages)  # Reverse to show oldest first
    ]

def delete_message(message_id):
    """
    Deletes a message from the database if the user is either the sender or recipient.

    Parameters:
        message_id (int): The ID of the message to be deleted.

    Returns:
        (str, str, int, int): recipient, sender, and read status of message, error code at the end SUCCESS if deletion was successful, (None, ER_NO) otherwise.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get message to verify existence
    cur.execute(f"""
        SELECT id, sender, recipient, unread FROM messages WHERE id = ?""", (message_id,))

    message = cur.fetchone()

    if not message:
        conn.close()
        return None, None, None, ID_DNE  # ID DNE

    # Delete the message
    try:
        cur.execute("""DELETE FROM messages WHERE id = ?""", (message_id,))
    except Exception as e:
        conn.close()
        return None, None, None, DB_ERROR

    conn.commit()
    conn.close()
    
    return message["recipient"], message["sender"], message["unread"], SUCCESS  # Deletion successful
    
# ----------------------------
# Additional Utility Functions
# ----------------------------

def clear_accounts():
    """
    Delete all rows from the accounts table.
    Use with caution!
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM accounts")
    conn.commit()
    conn.close()

def get_all_accounts():
    """
    Retrieve all rows from the accounts table.
    
    Returns:
      list: A list of sqlite3.Row objects, each representing an account.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM accounts")
    rows = cur.fetchall()
    conn.close()
    return rows
