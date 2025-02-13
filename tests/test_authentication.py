"""
Module Name: test_authentication.py
Description: Tests to ensure that the authentication functions (registering accounts, verifying logins) work correctly.
Author: Henry Huang and Bridget Ma
Date: 2024-2-7
"""

import os
import pytest

# Change test directory to the server directory to run tests with config
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
server_dir = os.path.join(project_root, 'server')
os.chdir(server_dir)

# Add the root directory to sys.path
from server import database
from configs.config import *

# Use a pytest fixture to set up and tear down a temporary test database.
@pytest.fixture(autouse=True)
def setup_database():
    test_db = "test_chat.db"
    # Override the database filename in your module
    database.DATABASE_NAME = test_db

    # Remove the test database file if it already exists
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize the database (create tables, etc.)
    database.initialize_db()
    
    yield  # run the tests
    
    # Teardown: Remove the test database after tests are finished
    if os.path.exists(test_db):
        os.remove(test_db)

def test_register_account_success():
    """Test that a new account can be registered successfully."""
    success, errno = database.register_account("user1", "hashed_pass_1")
    assert success, "Registration should succeed for a new username."
    assert errno == SUCCESS
    
    # Verify that the account exists in the database.
    accounts = database.get_all_accounts()
    assert len(accounts) == 1
    assert accounts[0]["username"] == "user1"

def test_register_account_duplicate():
    """Test that duplicate registration fails."""
    success, errno = database.register_account("user1", "hashed_pass_1")
    assert success, SUCCESS
    
    success, errno = database.register_account("user1", "hashed_pass_2")
    assert not success, "Duplicate registration should fail."
    assert errno == USER_TAKEN

def test_verify_login_success():
    """Test that login succeeds with the correct hashed password."""
    database.register_account("user1", "hashed_pass_1")
    success, errno = database.verify_login("user1", "hashed_pass_1")
    assert success, "Login should succeed with the correct hashed password."
    assert errno == SUCCESS

def test_verify_login_wrong_password():
    """Test that login fails with an incorrect hashed password."""
    database.register_account("user1", "hashed_pass_1")
    success, errno = database.verify_login("user1", "wrong_hash")
    assert not success, "Login should fail with an incorrect password."
    assert errno == WRONG_PASS

def test_verify_login_nonexistent():
    """Test that login fails for a username that does not exist."""
    success, errno = database.verify_login("nonexistent", "any_pass")
    assert not success, "Login should fail for a nonexistent username."
    assert errno == USER_DNE

def test_clear_accounts():
    """Test that clear_accounts() removes all account entries."""
    database.register_account("user1", "hashed_pass_1")
    database.register_account("user2", "hashed_pass_2")
    accounts = database.get_all_accounts()
    assert len(accounts) == 2, "There should be 2 accounts registered."
    
    database.clear_accounts()
    accounts = database.get_all_accounts()
    assert len(accounts) == 0, "All accounts should be cleared."
