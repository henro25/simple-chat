"""
Module Name: config.py
Description: Contains configuration settings for the client (e.g., server IP/port, timeout settings, etc.).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

# Default host and port for the server.
SERVER_HOST = 'localhost'
SERVER_PORT = 65432

CUR_PROTO_VERSION = "1.0"
SUPPORTED_VERSIONS = ["1.0", "2.0", "3.0"]

DATABASE_NAME = "chat.db"

# Error Codes
SUCCESS     = 0
USER_TAKEN  = 1 # when client creates a new username, username is already taken
USER_DNE    = 2 # when client logs in, the requested username does not exist
WRONG_PASS  = 3 # when client logs in, the password is incorrect
DB_ERROR    = 4 # when server experiences a database error
UNSUPPORTED_VERSION = 5 # when client sends a message with an unsupported version
UNKNOWN_COMMAND = 6 # when client sends a message with an unknown command
ID_DNE = 7 # when client tries to delete an entry that does not exist in db
USER_LOGGED_ON = 8 # when client tries to log into an active account

ERROR_MSGS = {
    1: "Username already exists.",
    2: "Username does not exist.",
    3: "Incorrect password.",
    4: "Database error.",
    5: "Unsupported protocol version.",
    6: "Unknown wire command reveived.",
    7: "Message does not exist.",
    8: "User already logged on"
}

DEBUG = True

def debug(message):
    """Print debug messages if DEBUG is True."""
    if DEBUG:
        print(f"[DEBUG] {message}")

# Codes for pages
REG_PG = 10
LGN_PG = 11
MSG_PG = 12
CONVO_PG = 13