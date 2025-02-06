"""
Module Name: database.py
Description: Contains functions and classes to manage the SQLite database, including connection management, schema initialization, and query functions (e.g., user creation, message insertion, fetching chat history).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import sqlite3
from datetime import datetime
from .config import *

def get_db_connection():
    """Establish and return a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enable dictionary-like access to rows
    return conn

def initialize_db():
    """
    Create the accounts table if it doesn't exist.
    This function should be called at startup.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

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
