"""
Module Name: config.py
Description: Configuration settings for the server (e.g., port numbers, database file location, logging settings).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

# Define host and port for the server.
HOST = 'localhost'
PORT = 65432  # Choose an available TCP port

PROTOCOL = "custom"  # Options: "custom" or "json"
SUPPORTED_VERSIONS = ["1.0"]

DATABASE_NAME = "chat.db"

# Error Codes
SUCCESS     = 0
USER_TAKEN  = 1 # when client creates a new username, username is already taken
USER_DNE    = 2 # when client logs in, the requested username does not exist
WRONG_PASS  = 3 # when client logs in, the password is incorrect
DB_ERROR    = 4 # when server experiences a database error
UNSUPPORTED_VERSION = 5 # when client sends a message with an unsupported version