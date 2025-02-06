"""
Module Name: config.py
Description: Contains configuration settings for the client (e.g., server IP/port, timeout settings, etc.).
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

PROTOCOL = "custom"  # Options: "custom" or "json"
DEBUG = True

def debug(message):
    """Print debug messages if DEBUG is True."""
    if DEBUG:
        print(f"[DEBUG] {message}")