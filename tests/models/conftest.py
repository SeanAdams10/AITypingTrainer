import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, Tuple

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.ngram_manager import Keystroke, NGramManager
from models.session_manager import SessionManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager
from models.user import User
from models.user_manager import UserManager

# These constants are exported for use by tests that import from conftest.py
__all__ = ["Keystroke", "NGramManager"]

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

# Timestamp helpers for brevity - commonly used in n-gram tests
BASE_TIME = datetime(2023, 1, 1, 12, 0, 0, 0)
T0 = BASE_TIME
T10K_US = BASE_TIME + timedelta(microseconds=10000)
T100K_US = BASE_TIME + timedelta(microseconds=100000)
T200K_US = BASE_TIME + timedelta(microseconds=200000)
T300K_US = BASE_TIME + timedelta(microseconds=300000)
T400K_US = BASE_TIME + timedelta(microseconds=400000)
T500K_US = BASE_TIME + timedelta(microseconds=500000)
T600K_US = BASE_TIME + timedelta(microseconds=600000)
T700K_US = BASE_TIME + timedelta(microseconds=700000)


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
    Create a DatabaseManager instance with a temporary database using LOCAL connection type.

    Args:
        temp_db: Path to the temporary database file (provided by temp_db fixture)

    Returns:
        DatabaseManager: A new DatabaseManager instance with LOCAL connection type
    """
    return DatabaseManager(temp_db, connection_type=ConnectionType.LOCAL)


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


@pytest.fixture(scope="function")
def test_user(db_with_tables: DatabaseManager) -> User:
    """
    Creates and saves a test user, returning the User object.
    This fixture is function-scoped to ensure a fresh user for each test,
    preventing side effects between tests.
    """
    user_manager = UserManager(db_with_tables)
    user = User(
        first_name="Test",
        surname="User",
        email_address=f"test.user.{uuid.uuid4()}@example.com",
    )
    user_manager.save_user(user)
    return user


@pytest.fixture(scope="function")
def test_keyboard(db_with_tables: DatabaseManager, test_user: User) -> Keyboard:
    """
    Creates and saves a test keyboard associated with the test_user,
    returning the Keyboard object.
    This fixture is function-scoped for test isolation.
    """
    keyboard_manager = KeyboardManager(db_with_tables)
    keyboard = Keyboard(
        user_id=str(test_user.user_id),
        keyboard_name="Test Keyboard",
    )
    keyboard_manager.save_keyboard(keyboard)
    return keyboard


@pytest.fixture(scope="function")
def category_manager_fixture(db_with_tables: DatabaseManager) -> CategoryManager:
    """
    Creates and returns a CategoryManager instance.
    """
    return CategoryManager(db_with_tables)


@pytest.fixture(scope="function")
def test_category(
    db_with_tables: DatabaseManager,
    category_manager_fixture: CategoryManager
) -> Category:
    """
    Creates and saves a test category, returning the Category object.
    """
    category = Category(
        category_name=f"Test Category {uuid.uuid4()}",
        description="Test category for unit tests"
    )
    category_manager_fixture.save_category(category)
    return category


@pytest.fixture(scope="function")
def snippet_manager_fixture(db_with_tables: DatabaseManager) -> SnippetManager:
    """
    Creates and returns a SnippetManager instance.
    """
    return SnippetManager(db_with_tables)


@pytest.fixture(scope="function")
def test_snippet(
    db_with_tables: DatabaseManager,
    snippet_manager_fixture: SnippetManager,
    test_category: Category
) -> Snippet:
    """
    Creates and saves a test snippet, returning the Snippet object.
    """
    # Ensure category_id is a string (not None) before creating the snippet
    category_id = str(test_category.category_id) if test_category.category_id else str(uuid.uuid4())
    
    snippet = Snippet(
        snippet_name=f"Test Snippet {uuid.uuid4()}",
        content="This is a test snippet for typing practice.",
        category_id=category_id,
        description="Test snippet for unit tests"
    )
    snippet_manager_fixture.save_snippet(snippet)
    return snippet


@pytest.fixture(scope="function")
def session_manager_fixture(db_with_tables: DatabaseManager) -> SessionManager:
    """
    Creates and returns a SessionManager instance.
    """
    return SessionManager(db_with_tables)


@pytest.fixture(scope="function")
def test_session_setup(
    test_category: Category,
    test_snippet: Snippet,
    test_user: User
) -> Tuple[str, str, str]:
    """
    Creates a complete test setup with category, snippet, and user.
    Returns tuple of (category_id, snippet_id, user_id).
    """
    # Convert to str to ensure consistent typing - IDs should be strings in most contexts
    return (
        str(test_category.category_id),
        str(test_snippet.snippet_id),
        str(test_user.user_id)
    )
