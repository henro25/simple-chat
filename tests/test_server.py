"""
Module Name: test_server.py
Description: Contains tests for server functionality. This may include testing database operations, protocol parsing, and correct handling of multiple client requests.
Author: Henry Huang and Bridget Ma
Date: 2024-2-6
"""

import os
import pytest

# Change test directory to the server directory to run tests with config
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
server_dir = os.path.join(project_root, 'server')
os.chdir(server_dir)

from server import database
from server.server import process_message
from server.config import *

# Fixture to set up a temporary test database.
@pytest.fixture(autouse=True)
def setup_test_db():
    test_db = "test_chat.db"
    # Override the database filename so tests don't touch production data.
    database.DATABASE_FILENAME = test_db
    
    # Remove any existing test DB file.
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize the database (create tables, etc.)
    database.initialize_db()
    
    yield # run the tests
    
    # Teardown: remove the test database after each test.
    if os.path.exists(test_db):
        os.remove(test_db)

def test_unsupported_version():
    """
    Test that an unsupported version returns an error.
    """
    assert process_message("10.0 LOGIN user pass") == f"1.0 ERROR {UNSUPPORTED_VERSION}"

def test_create_account_success():
    """
    Test that creating a new account succeeds.
    """
    assert process_message("1.0 CREATE testuser hashed123") == "1.0 SUCCESS Registration complete"

def test_create_account_duplicate():
    """
    Test that attempting to create an account with an existing username fails.
    """
    response1 = process_message("1.0 CREATE testuser hashed123")
    assert "SUCCESS" in response1  # First registration succeeds.
    
    response2 = process_message("1.0 CREATE testuser hashed456")
    assert response2 == f"1.0 ERROR {USER_TAKEN}"

def test_login_success():
    """
    Test that login succeeds with the correct credentials.
    """
    # First, register an account.
    process_message("1.0 CREATE testuser hashed123")
    response = process_message("1.0 LOGIN testuser hashed123")
    assert response == "1.0 SUCCESS Login successful"

def test_login_wrong_password():
    """
    Test that login fails with a wrong password.
    """
    process_message("1.0 CREATE testuser hashed123")
    response = process_message("1.0 LOGIN testuser wrongpass")
    assert response == f"1.0 ERROR {WRONG_PASS}"

def test_login_nonexistent():
    """
    Test that login fails for a username that does not exist.
    """
    response = process_message("1.0 LOGIN nonuser hashedpass")
    assert response == f"1.0 ERROR {USER_DNE}"
