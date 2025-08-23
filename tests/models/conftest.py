"""Model tests fixtures and DB helpers for analytics session methods.

This module defines reusable pytest fixtures and helper functions to create
temporary databases, users, keyboards, sessions, and related rows used by
tests under `tests/models/`.
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from helpers.debug_util import DebugUtil
from models.category import Category
from models.category_manager import CategoryManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.snippet_manager import SnippetManager
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
def temp_db() -> Generator[DatabaseManager, None, None]:
    """Create a temporary DatabaseManager for testing.

    Yields:
        DatabaseManager: A DatabaseManager instance pointing to a temp file DB (LOCAL)

    Ensures the connection is closed and the temp file removed after the test.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    # Create DebugUtil in loud mode for tests
    debug_util = DebugUtil()
    debug_util._mode = "loud"
    
    db = DatabaseManager(db_path, connection_type=ConnectionType.LOCAL, debug_util=debug_util)
    # Ensure all tables exist for tests that rely on temp_db directly
    db.init_tables()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass
        # Clean up the temporary file
        try:
            os.unlink(db_path)
        except (OSError, PermissionError):
            pass


@pytest.fixture(scope="function")
def db_manager(temp_db: DatabaseManager) -> DatabaseManager:
    """Create a DatabaseManager instance with a temporary database using LOCAL connection type.

    Args:
        temp_db: DatabaseManager instance (provided by temp_db fixture)

    Returns:
        DatabaseManager: A new DatabaseManager instance with LOCAL connection type
    """
    return temp_db


@pytest.fixture(scope="function")
def db_with_tables(db_manager: DatabaseManager) -> DatabaseManager:
    """Create a database with all tables initialized.

    Args:
        db_manager: DatabaseManager instance (provided by db_manager fixture)

    Returns:
        DatabaseManager: The same DatabaseManager instance with tables initialized
    """
    db_manager.init_tables()
    return db_manager


def create_connection_error_db() -> str:
    """Create a database path that will cause a connection error.

    Returns:
        str: A path that will cause a connection error when used
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        return str(Path(temp_dir) / "nonexistent" / "database.db")


@pytest.fixture(scope="function")
def test_user(db_with_tables: DatabaseManager) -> User:
    """Creates and saves a test user, returning the User object.

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
    """Creates and saves a test keyboard associated with the test_user.

    Returns the Keyboard object. This fixture is function-scoped for test
    isolation.
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
        ms_per_keystroke: float = 150.0,
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
                session_id,
                user_id,
                keyboard_id,
                snippet_id,
                0,
                10,
                "test content",
                start_time,
                start_time,
                10,
                1,
                ms_per_keystroke,
            ),
        )

        return session_id

    @staticmethod
    def create_session_ngram_speed(
        db: DatabaseManager, session_id: str, ngram_data: List[Dict[str, Any]]
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
                    str(uuid.uuid4()),
                    session_id,
                    data["ngram_size"],
                    data["ngram_text"],
                    data["ngram_time_ms"],
                    data["ms_per_keystroke"],
                ),
            )

    @staticmethod
    def create_session_ngram_errors(
        db: DatabaseManager, session_id: str, error_data: List[Dict[str, Any]]
    ) -> None:
        """Create session ngram error entries."""
        for data in error_data:
            db.execute(
                """
                INSERT INTO session_ngram_errors (
                    ngram_error_id, session_id, ngram_size, ngram_text
                ) VALUES (?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), session_id, data["ngram_size"], data["ngram_text"]),
            )

    @staticmethod
    def create_session_keystrokes(
        db: DatabaseManager, session_id: str, keystroke_data: List[Dict[str, Any]]
    ) -> None:
        """Create session keystroke entries."""
        for i, data in enumerate(keystroke_data):
            db.execute(
                """
                INSERT INTO session_keystrokes (
                    keystroke_id, session_id, keystroke_time, keystroke_char, 
                    expected_char, is_error, time_since_previous, text_index
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    session_id,
                    data["keystroke_time"],
                    data["keystroke_char"],
                    data["expected_char"],
                    data["is_error"],
                    data["time_since_previous"],
                    int(data.get("text_index", i)),
                ),
            )

    @staticmethod
    def create_snippet(db: DatabaseManager, category_id: str) -> str:
        """Create a test snippet and return snippet_id."""
        snippet_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO snippets (snippet_id, category_id, snippet_name)
            VALUES (?, ?, ?)
            """,
            (snippet_id, category_id, "Test Snippet"),
        )

        return snippet_id

    @staticmethod
    def create_category(db: DatabaseManager) -> str:
        """Create a test category and return category_id."""
        category_id = str(uuid.uuid4())

        db.execute(
            """
            INSERT INTO categories (category_id, category_name)
            VALUES (?, ?)
            """,
            (category_id, "Test Category"),
        )

        return category_id


@pytest.fixture
def analytics_service(db_with_tables: DatabaseManager) -> NGramAnalyticsService:
    """Create NGramAnalyticsService with required dependencies."""
    ngram_manager = NGramManager()
    return NGramAnalyticsService(db_with_tables, ngram_manager)


# ---------------------------------------------------------------------------
# Additional fixtures and type aliases used by analytics tests
# ---------------------------------------------------------------------------

# Simple aliases to satisfy type hints in tests
MockSessionData = Dict[str, Any]
MockNGramSpeedData = Dict[str, Any]


@pytest.fixture
def mock_sessions() -> List[MockSessionData]:
    """Provide a small set of mock practice sessions used in analytics tests."""
    return [
        {
            "session_id": f"session_{i}",
            "user_id": "user_1",
            "keyboard_id": "keyboard_1",
            "start_time": f"2024-01-01 10:0{i}:00",
            "target_ms_per_keystroke": 150.0 + i * 10.0,
        }
        for i in range(1, 3)
    ]


@pytest.fixture
def mock_ngram_data(mock_sessions: List[MockSessionData]) -> List[MockNGramSpeedData]:
    """Provide a small set of mock ngram speed rows spanning the mock sessions."""
    sids = [s["session_id"] for s in mock_sessions]
    return [
        {
            "ngram_speed_id": f"ng_{i}",
            "session_id": sids[i % len(sids)],
            "ngram_size": 2 + (i % 2),
            "ngram_text": ["th", "he"][i % 2],
            "ngram_time_ms": 200.0 + i * 5.0,
            "ms_per_keystroke": 100.0 + i * 2.5,
        }
        for i in range(4)
    ]


@pytest.fixture
def ngram_speed_test_data(
    db_with_tables: DatabaseManager,
    mock_sessions: List[MockSessionData],
    mock_ngram_data: List[MockNGramSpeedData],
) -> Tuple[DatabaseManager, NGramAnalyticsService, str, str, str]:
    """Create a DB with mock data and return (db, service, session_id, user_id, keyboard_id)."""
    user_id = "user_1"
    keyboard_id = "keyboard_1"

    # minimal FK deps
    db_with_tables.execute(
        "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        (user_id, "Test", "User", "test@example.com"),
    )
    db_with_tables.execute(
        "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
        (keyboard_id, user_id, "Test Keyboard"),
    )
    db_with_tables.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        ("cat_1", "Test Category"),
    )
    db_with_tables.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        ("snippet_1", "cat_1", "Snippet"),
    )

    for s in mock_sessions:
        db_with_tables.execute(
            """
            INSERT INTO practice_sessions (
                session_id, user_id, keyboard_id, snippet_id, snippet_index_start,
                snippet_index_end, content, start_time, end_time, actual_chars,
                errors, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s["session_id"],
                user_id,
                keyboard_id,
                "snippet_1",
                0,
                10,
                "content",
                s["start_time"],
                s["start_time"],
                10,
                0,
                s["target_ms_per_keystroke"],
            ),
        )

    for row in mock_ngram_data:
        db_with_tables.execute(
            """
            INSERT INTO session_ngram_speed (
                ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["ngram_speed_id"],
                row["session_id"],
                row["ngram_size"],
                row["ngram_text"],
                row["ngram_time_ms"],
                row["ms_per_keystroke"],
            ),
        )

    service = NGramAnalyticsService(db_with_tables, NGramManager())
    # return first session id as representative id
    return db_with_tables, service, mock_sessions[0]["session_id"], user_id, keyboard_id


# ---------------------------------------------------------------------------
# Additional fixtures required by tests in tests/models/test_snippet.py
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def category_manager(db_with_tables: DatabaseManager) -> CategoryManager:
    """CategoryManager bound to the function-scoped test database."""
    return CategoryManager(db_with_tables)


@pytest.fixture(scope="function")
def snippet_manager(db_with_tables: DatabaseManager) -> SnippetManager:
    """SnippetManager bound to the function-scoped test database."""
    return SnippetManager(db_with_tables)


@pytest.fixture(scope="function")
def snippet_category_fixture(category_manager: CategoryManager) -> str:
    """Create a fresh category and return its ID as string for snippet tests."""
    cat = Category(category_name=f"Test Category {uuid.uuid4().hex[:8]}")
    category_manager.save_category(cat)
    return str(cat.category_id)


@pytest.fixture(scope="function")
def valid_snippet_data(snippet_category_fixture: str) -> Dict[str, str]:
    """Provide a valid set of snippet data used in multiple tests."""
    return {
        "category_id": snippet_category_fixture,
        "snippet_name": "ValidName",
        "content": "Valid content",
    }
