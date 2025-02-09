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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create the num_unread_msgs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS num_unread_msgs (
            recipient TEXT NOT NULL,
            sender TEXT NOT NULL,
            last_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            unread_count INTEGER DEFAULT 0,
            PRIMARY KEY (recipient, sender)
        )
    """)
    
    # Create the messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    cur.execute("SELECT password_hash FROM accounts WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    
    if row is None:
        return False, USER_DNE
    
    stored_hash = row["password_hash"]
    
    # Compare the provided password with the stored hash.
    if password == stored_hash:
        return True, SUCCESS
    else:
        return False, WRONG_PASS

# ----------------------------
# Query and Update Number of Unread Messages
# ----------------------------

def get_conversations(recipient):
    """
    Retrieve a list of conversations for the given recipient.
    The result is a list of tuples in the form: (sender, unread_count).
    
    The ordering is as follows:
      1. Conversations with unread messages (queried from num_unread_msgs) sorted by last_timestamp (most recent first).
      2. The rest of the users (from accounts) that are not in the unread list, with unread_count set to 0, sorted alphabetically.
    
    Parameters:
      recipient (str): The username of the recipient requesting conversations.
    
    Returns:
      list: A list of tuples (sender, unread_count).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Query conversations with unread messages from num_unread_msgs
    cur.execute("""
        SELECT sender, unread_count 
        FROM num_unread_msgs 
        WHERE recipient = ? 
        ORDER BY last_timestamp DESC
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
    
    # Combine results: unread conversations first, then other users with 0 unread messages
    conversations = [(row["sender"], row["unread_count"]) for row in unread_rows]
    conversations.extend([(row["username"], 0) for row in other_rows])
    
    return conversations

def update_num_unread(recipient, sender, num_unread):
    """
    Update the num_unread_msgs table for a new message from sender to recipient.
    If an entry exists, update the unread_count and update the timestamp.
    Otherwise, create a new entry with unread_count set to num_unread.
    
    Parameters:
      recipient (str): The recipient of the message.
      sender (str): The sender of the message.
      num_unread (int): The number of unread messages.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if an entry exists for this conversation
    cur.execute("""
        SELECT unread_count FROM num_unread_msgs
        WHERE recipient = ? AND sender = ?
    """, (recipient, sender))
    row = cur.fetchone()
    
    if row:
        new_count = row["unread_count"] + num_unread
        cur.execute("""
            UPDATE num_unread_msgs
            SET unread_count = ?, last_timestamp = CURRENT_TIMESTAMP
            WHERE recipient = ? AND sender = ?
        """, (new_count, recipient, sender))
    else:
        cur.execute("""
            INSERT INTO num_unread_msgs (recipient, sender, unread_count)
            VALUES (?, ?, ?)
        """, (recipient, sender, num_unread))
    
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

def get_recent_messages(user1, user2, limit=20):
    """
    Retrieve the most recent messages exchanged between two users.

    Parameters:
        user1 (str): First username.
        user2 (str): Second username.
        limit (int): Number of messages to fetch (default 20).

    Returns:
        list: A list of dictionaries containing messages.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, sender, recipient, message, timestamp 
        FROM messages 
        WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
        ORDER BY id DESC 
        LIMIT ?
    """, (user1, user2, user2, user1, limit))
    
    messages = cur.fetchall()
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
        bool: True if deletion was successful, False otherwise.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get message to verify existence
    cur.execute(f"""
        SELECT id, sender, recipient FROM messages WHERE id = ?""", (message_id,))

    message = cur.fetchall()

    if not message:
        conn.close()
        return False, ID_DNE  # ID DNE

    # Delete the message
    try:
        cur.execute("""DELETE FROM messages WHERE id = ?""", (message_id,))
    except Exception as e:
        conn.close()
        return False, DB_ERROR

    conn.commit()
    conn.close()
    
    return True, SUCCESS  # Deletion successful
    
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
