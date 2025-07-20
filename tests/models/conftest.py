import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.user import User
from models.user_manager import UserManager

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


class TestSessionMethodsFixtures:
    """Helper class to create test data fixtures for session analytics tests."""
    
    @staticmethod
    def create_practice_session(
        db: DatabaseManager, 
        user_id: str, 
        keyboard_id: str, 
        snippet_id: str,
        start_time: str,
        ms_per_keystroke: float = 150.0
    ) -> str:
        """Create a practice session and return session_id."""
        session_id = str(uuid.uuid4())
        
        db.execute(
            """
            INSERT INTO practice_sessions (
                session_id, user_id, keyboard_id, snippet_id, snippet_index_start, 
                snippet_index_end, content, start_time, end_time, actual_chars, 
                errors, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, user_id, keyboard_id, snippet_id, 0, 10, 
                "test content", start_time, start_time, 10, 1, ms_per_keystroke
            )
        )
        
        return session_id
    
    @staticmethod
    def create_session_ngram_speed(
        db: DatabaseManager, 
        session_id: str, 
        ngram_data: List[Dict[str, Any]]
    ) -> None:
        """Create session ngram speed entries."""
        for data in ngram_data:
            db.execute(
                """
                INSERT INTO session_ngram_speed (
                    ngram_speed_id, session_id, ngram_size, ngram_text, 
                    ngram_time_ms, ms_per_keystroke
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), session_id, data['ngram_size'], 
                    data['ngram_text'], data['ngram_time_ms'], data['ms_per_keystroke']
                )
            )
    
    @staticmethod
    def create_session_ngram_errors(
        db: DatabaseManager, 
        session_id: str, 
        error_data: List[Dict[str, Any]]
    ) -> None:
        """Create session ngram error entries."""
        for data in error_data:
            db.execute(
                """
                INSERT INTO session_ngram_errors (
                    ngram_error_id, session_id, ngram_size, ngram_text
                ) VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), session_id, data['ngram_size'], data['ngram_text'])
            )
    
    @staticmethod
    def create_session_keystrokes(
        db: DatabaseManager, 
        session_id: str, 
        keystroke_data: List[Dict[str, Any]]
    ) -> None:
        """Create session keystroke entries."""
        for data in keystroke_data:
            db.execute(
                """
                INSERT INTO session_keystrokes (
                    keystroke_id, session_id, keystroke_time, keystroke_char, 
                    expected_char, is_error, time_since_previous
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), session_id, data['keystroke_time'], 
                    data['keystroke_char'], data['expected_char'], 
                    data['is_error'], data['time_since_previous']
                )
            )
    
    @staticmethod
    def create_snippet(db: DatabaseManager, category_id: str) -> str:
        """Create a test snippet and return snippet_id."""
        snippet_id = str(uuid.uuid4())
        
        db.execute(
            """
            INSERT INTO snippets (snippet_id, category_id, title, content, difficulty_level)
            VALUES (?, ?, ?, ?, ?)
            """,
            (snippet_id, category_id, "Test Snippet", "test content for typing", 1)
        )
        
        return snippet_id
    
    @staticmethod
    def create_category(db: DatabaseManager) -> str:
        """Create a test category and return category_id."""
        category_id = str(uuid.uuid4())
        
        db.execute(
            """
            INSERT INTO categories (category_id, category_name, description)
            VALUES (?, ?, ?)
            """,
            (category_id, "Test Category", "Test category for testing")
        )
        
        return category_id


@pytest.fixture
def analytics_service(db_with_tables: DatabaseManager) -> NGramAnalyticsService:
    """Create NGramAnalyticsService with required dependencies."""
    ngram_manager = NGramManager(db_with_tables)
    return NGramAnalyticsService(db_with_tables, ngram_manager)
