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
import pytest

# First-party imports
from db.database_manager import DatabaseManager
from models.snippet import SnippetManager

# Ensure project root is on sys.path first, then tests directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

@pytest.fixture
def database(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """
    Creates a temporary SQLite database, initializes schema using DatabaseManager,
    and cleans up after the test.
    """
    db_path = tmp_path / "test_snippet.db"
    dbm = DatabaseManager(str(db_path))
    dbm.init_tables()
    yield dbm
    dbm.close()
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def snippet_manager(database: DatabaseManager) -> SnippetManager:
    """
    Provides a SnippetManager using the central DatabaseManager for tests.
    
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
