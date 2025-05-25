import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from db.database_manager import DatabaseManager

"""
Pytest configuration for model tests.

This makes fixtures from helpers available to all tests in this directory.
"""

# Removed pytest_plugins as per pytest deprecation warning.
# Fixtures should be imported in the top-level conftest.py or tests/conftest.py for global use.
"""
Database testing helpers and fixtures.

This module provides reusable fixtures and helper functions for testing database operations.
It includes fixtures for creating temporary databases and handling database connections.
"""


@pytest.fixture(scope="function")
def temp_db() -> Generator[str, None, None]:
    """
    Create a temporary database file for testing.

    Yields:
        str: Path to the temporary database file

    The database file is automatically deleted after the test completes.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    yield db_path

    # Clean up the temporary file
    try:
        os.unlink(db_path)
    except (OSError, PermissionError):
        pass


@pytest.fixture(scope="function")
def db_manager(temp_db: str) -> DatabaseManager:
    """
    Create a DatabaseManager instance with a temporary database.

    Args:
        temp_db: Path to the temporary database file (provided by temp_db fixture)

    Returns:
        DatabaseManager: A new DatabaseManager instance
    """
    return DatabaseManager(temp_db)


@pytest.fixture(scope="function")
def db_with_tables(db_manager: DatabaseManager) -> DatabaseManager:
    """
    Create a database with all tables initialized.

    Args:
        db_manager: DatabaseManager instance (provided by db_manager fixture)

    Returns:
        DatabaseManager: The same DatabaseManager instance with tables initialized
    """
    db_manager.init_tables()
    return db_manager


def create_connection_error_db() -> str:
    """
    Create a database path that will cause a connection error.

    Returns:
        str: A path that will cause a connection error when used
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        return str(Path(temp_dir) / "nonexistent" / "database.db")
