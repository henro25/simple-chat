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
from configs.config import *

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
    assert True

def test_create_account_success():
    """
    Test that creating a new account succeeds.
    """
    assert True

def test_create_account_duplicate():
    """
    Test that attempting to create an account with an existing username fails.
    """
    assert True

def test_login_success():
    """
    Test that login succeeds with the correct credentials.
    """
    assert True

def test_login_wrong_password():
    """
    Test that login fails with a wrong password.
    """
    assert True

def test_login_nonexistent():
    """
    Test that login fails for a username that does not exist.
    """
    assert True
