"""
Fixtures for snippet tests (core, API, UI).

This module provides pytest fixtures for snippet-related tests,
including database setup/teardown and test data generation.
"""
# Standard imports
import os
import sys
from pathlib import Path
from typing import Dict, Generator, Union

# Third-party imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from flask import Flask
# Only using unified GraphQL API
from api.unified_graphql import unified_graphql
from models.category import CategoryManager
from models.snippet import SnippetManager
import sqlite3

# First-party imports
from models.database_manager import DatabaseManager
from models.snippet import SnippetManager

# Ensure project root is on sys.path first, then tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

@pytest.fixture(scope="function")
def database(tmp_path):
    """
    Creates a temporary SQLite database with schema for categories, snippets, and snippet parts.
    Patches the CategoryManager.DB_PATH to use this test database.
    Returns the DatabaseManager instance for the test database.
    """
    db_path = str(tmp_path / "test.db")
    # Patch the CategoryManager DB_PATH
    CategoryManager.DB_PATH = db_path
    
    # Create schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(category_id) ON DELETE CASCADE
        );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snippet_parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY(snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()
    
    # Create a DatabaseManager instance that points to test DB
    dbm = DatabaseManager(db_path)
    yield dbm

@pytest.fixture(scope="function")
def app(database, snippet_manager):
    """
    Provides a Flask app with REST and GraphQL blueprints registered for testing.
    Both category and snippet functionality is available via REST and GraphQL.
    Uses the provided database and snippet_manager fixtures.
    """
    app = Flask(__name__)
    app.config["TESTING"] = True
    
    # Register Unified GraphQL blueprint (handles both category and snippet operations)
    app.register_blueprint(unified_graphql, url_prefix="/api")
    
    app.app_context().push()
    # Store snippet_manager in app config for GraphQL access
    app.config['SNIPPET_MANAGER'] = snippet_manager
    yield app

@pytest.fixture
def snippet_manager(database) -> SnippetManager:
    """
    Provides a SnippetManager using the DatabaseManager fixture for tests.
    
    Args:
        database: The database manager fixture to use
        
    Returns:
        SnippetManager: A snippet manager connected to the test database
    """
    return SnippetManager(database)

@pytest.fixture
def valid_snippet_data() -> Dict[str, Union[str, int]]:
    """
    Provides standard valid snippet data for testing.
    
    Returns:
        Dict[str, Union[str, int]]: A dictionary with valid snippet data containing 
            category_id, snippet_name, and content
    """
    return {"category_id": 1, "snippet_name": "Sample", "content": "Hello world."}

from flask.testing import FlaskClient

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """
    Provides a Flask test client for API and GraphQL endpoint testing.
    Uses the Flask app fixture and yields a FlaskClient instance.
    """
    with app.test_client() as client:
        yield client
