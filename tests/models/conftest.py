import os
import random
import string
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Generator, List, Tuple, TypedDict, Union

import pytest
from _pytest.monkeypatch import MonkeyPatch

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
from models.ngram_analytics_service import NGramAnalyticsService

# These constants are exported for use by tests that import from conftest.py
__all__ = ["Keystroke", "NGramManager"]


class MockSessionData(TypedDict):
    """Test data structure for mock sessions."""
    session_id: str
    user_id: str
    keyboard_id: str
    start_time: str
    target_ms_per_keystroke: int


class MockNGramSpeedData(TypedDict):
    """Test data structure for mock n-gram speed data."""
    ngram_speed_id: str
    session_id: str
    ngram_size: int
    ngram_text: str
    ngram_time_ms: float
    ms_per_keystroke: float


class MockNGramErrorData(TypedDict):
    """Test data structure for mock n-gram error data."""
    ngram_error_id: str
    session_id: str
    ngram_size: int
    ngram_text: str
    error_count: int

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
T800K_US = BASE_TIME + timedelta(microseconds=800000)
T900K_US = BASE_TIME + timedelta(microseconds=900000)
T1000K_US = BASE_TIME + timedelta(microseconds=1000000)
T1100K_US = BASE_TIME + timedelta(microseconds=1100000)
T1200K_US = BASE_TIME + timedelta(microseconds=1200000)
T1300K_US = BASE_TIME + timedelta(microseconds=1300000)
T1400K_US = BASE_TIME + timedelta(microseconds=1400000)
T1500K_US = BASE_TIME + timedelta(microseconds=1500000)
T1600K_US = BASE_TIME + timedelta(microseconds=1600000)
T1700K_US = BASE_TIME + timedelta(microseconds=1700000)
T1800K_US = BASE_TIME + timedelta(microseconds=1800000)
T1900K_US = BASE_TIME + timedelta(microseconds=1900000)
T2000K_US = BASE_TIME + timedelta(microseconds=2000000)
T2100K_US = BASE_TIME + timedelta(microseconds=2100000)


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


@pytest.fixture(scope="function")
def mock_sessions() -> List[MockSessionData]:
    """
    Test objective: Provide mock session data for testing.

    Returns a list of mock session data with different timestamps
    for testing historical analysis and decaying averages.
    """
    base_time = datetime.now() - timedelta(days=30)
    return [
        {
            "session_id": str(uuid.uuid4()),
            "user_id": "user_1",
            "keyboard_id": "keyboard_1",
            "start_time": (base_time + timedelta(days=i)).isoformat(),
            "target_ms_per_keystroke": 200,
        }
        for i in range(20)
    ]


@pytest.fixture(scope="function")
def mock_ngram_data() -> List[MockNGramSpeedData]:
    """
    Test objective: Provide mock n-gram speed data for testing.

    Returns a list of mock n-gram speed data with varying performance
    for testing decaying average calculations and analytics.
    """
    return [
        {
            "ngram_speed_id": str(uuid.uuid4()),
            "session_id": "session_1",
            "ngram_size": 2,
            "ngram_text": "th",
            "ngram_time_ms": 400.0,
            "ms_per_keystroke": 200.0,
        },
        {
            "ngram_speed_id": str(uuid.uuid4()),
            "session_id": "session_2",
            "ngram_size": 2,
            "ngram_text": "th",
            "ngram_time_ms": 350.0,
            "ms_per_keystroke": 175.0,
        },
        {
            "ngram_speed_id": str(uuid.uuid4()),
            "session_id": "session_3",
            "ngram_size": 2,
            "ngram_text": "th",
            "ngram_time_ms": 300.0,
            "ms_per_keystroke": 150.0,
        },
    ]


@pytest.fixture(scope="function")
def ngram_test_setup(
    db_with_tables: DatabaseManager,
    test_user: User,
    test_keyboard: Keyboard,
    test_category: Category,
    test_snippet: Snippet,
    mock_sessions: List[MockSessionData],
    mock_ngram_data: List[MockNGramSpeedData],
) -> Dict[str, str]:
    """
    Test objective: Set up complete database with practice sessions and ngram data.

    Creates all necessary database entries for ngram analytics testing,
    including practice sessions and ngram speed data.
    
    Returns:
        Dict with user_id, keyboard_id, category_id, snippet_id for test use
    """
    user_id = str(test_user.user_id)
    keyboard_id = str(test_keyboard.keyboard_id)
    category_id = str(test_category.category_id)
    snippet_id = str(test_snippet.snippet_id)

    # Insert practice sessions
    for session in mock_sessions:
        db_with_tables.execute(
            "INSERT INTO practice_sessions "
            "(session_id, user_id, keyboard_id, snippet_id, "
            "snippet_index_start, snippet_index_end, content, "
            "start_time, end_time, actual_chars, errors, ms_per_keystroke) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session["session_id"],
                user_id,
                keyboard_id,
                snippet_id,
                0,
                10,
                "test content",
                session["start_time"],
                session["start_time"],
                10,
                0,
                session["target_ms_per_keystroke"],
            ),
        )

    # Insert ngram speed data
    for ngram in mock_ngram_data:
        db_with_tables.execute(
            "INSERT INTO ngram_speed "
            "(ngram_speed_id, session_id, ngram_size, ngram_text, "
            "ngram_time_ms, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?)",
            (
                ngram["ngram_speed_id"],
                ngram["session_id"],
                ngram["ngram_size"],
                ngram["ngram_text"],
                ngram["ngram_time_ms"],
                ngram["ms_per_keystroke"],
            ),
        )

    return {
        "user_id": user_id,
        "keyboard_id": keyboard_id,
        "category_id": category_id,
        "snippet_id": snippet_id,
    }


@pytest.fixture(scope="function")
def ngram_speed_test_data(
    db_with_tables: DatabaseManager,
    test_user: User,
    test_keyboard: Keyboard,
    test_snippet: Snippet,
) -> Tuple[DatabaseManager, NGramAnalyticsService, str, str, str]:
    """
    Test objective: Set up test data for ngram speed analysis.

    Creates test sessions and ngram speed data with different performance levels
    for testing slowest_n and similar analytics methods.
    
    Returns:
        Tuple containing (db, service, user_id, keyboard_id, snippet_id)
    """
    user_id = str(test_user.user_id)
    keyboard_id = str(test_keyboard.keyboard_id)
    snippet_id = str(test_snippet.snippet_id)
    session_id = "test_session_1"

    # Insert test session
    db_with_tables.execute(
        "INSERT INTO practice_sessions "
        "(session_id, user_id, keyboard_id, snippet_id, "
        "snippet_index_start, snippet_index_end, content, "
        "start_time, end_time, actual_chars, errors, ms_per_keystroke) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            user_id,
            keyboard_id,
            snippet_id,
            0,
            10,
            "test content",
            "2024-01-01 10:00:00",
            "2024-01-01 10:05:00",
            10,
            0,
            150.0,
        ),
    )

    # Insert test data with different performance levels
    test_data = [
        ("session_1", "user_1", "keyboard_1", 2, "th", 400.0, 200.0),  # Slowest
        ("session_2", "user_1", "keyboard_1", 2, "he", 350.0, 175.0),  # Medium
        ("session_3", "user_1", "keyboard_1", 2, "er", 300.0, 150.0),  # Fastest
        ("session_4", "user_1", "keyboard_1", 3, "the", 450.0, 150.0),  # Different size
        ("session_5", "user_2", "keyboard_1", 2, "an", 500.0, 250.0),  # Different user
    ]

    for (
        sess_id,
        _,  # u_id unused
        _,  # k_id unused
        ngram_size,
        ngram_text,
        ngram_time_ms,
        ms_per_keystroke,
    ) in test_data:
        db_with_tables.execute(
            "INSERT INTO session_ngram_speed "
            "(session_id, ngram_text, ngram_size, ngram_time_ms, ms_per_keystroke) VALUES (?, ?, ?, ?, ?)",
            (
                sess_id,
                ngram_text,
                ngram_size,
                ngram_time_ms,
                ms_per_keystroke,
            ),
        )

    return {"user_id": user_id, "keyboard_id": keyboard_id}


@pytest.fixture(scope="function")
def ngram_error_test_data(
    db_with_tables: DatabaseManager,
    test_user: User,
    test_keyboard: Keyboard,
) -> Dict[str, str]:
    """
    Test objective: Set up test data for ngram error analysis.

    Creates test sessions and ngram error data with different error rates
    for testing error_n and similar analytics methods.
    
    Returns:
        Dict with user_id, keyboard_id for test use
    """
    user_id = str(test_user.user_id)
    keyboard_id = str(test_keyboard.keyboard_id)

    # Insert test data with different error rates
    test_data = [
        ("session_1", "user_1", "keyboard_1", 2, "th", 5),  # Highest
        ("session_2", "user_1", "keyboard_1", 2, "he", 3),  # Medium
        ("session_3", "user_1", "keyboard_1", 2, "er", 1),  # Lowest
        ("session_4", "user_1", "keyboard_1", 3, "the", 4),  # Diff size
        ("session_5", "user_2", "keyboard_1", 2, "an", 6),  # Diff user
    ]

    for (
        session_id,
        _,  # u_id unused
        _,  # k_id unused
        ngram_size,
        ngram_text,
        error_count,
    ) in test_data:
        db_with_tables.execute(
            "INSERT INTO ngram_error "
            "(ngram_error_id, session_id, ngram_size, ngram_text, "
            "error_count) VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                session_id,
                ngram_size,
                ngram_text,
                error_count,
            ),
        )

    return {"user_id": user_id, "keyboard_id": keyboard_id}
# ================ COMMON TEST FIXTURES ================
# These fixtures are used across multiple test files

import random
import string
from pathlib import Path
from typing import Dict, Union
import uuid
import pytest
from _pytest.monkeypatch import MonkeyPatch
from typing import Generator

from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager
from models.snippet_manager import SnippetManager


@pytest.fixture
def random_id() -> str:
    """Generate a random ID string for testing."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=10))


@pytest.fixture(autouse=True)
def setup_and_teardown_db(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> Generator[None, None, None]:
    """
    Setup and teardown for all tests.
    Creates a temporary database for each test.
    """
    db_file = tmp_path / "test_db.sqlite3"
    monkeypatch.setenv("AITR_DB_PATH", str(db_file))
    yield


@pytest.fixture
def category_manager(db_with_tables: DatabaseManager) -> CategoryManager:
    """Create a CategoryManager instance (alias for category_manager_fixture)."""
    return CategoryManager(db_with_tables)


@pytest.fixture
def snippet_manager(db_with_tables: DatabaseManager) -> SnippetManager:
    """Create a SnippetManager instance (alias for snippet_manager_fixture)."""
    return SnippetManager(db_with_tables)


@pytest.fixture
def snippet_category_fixture(category_manager: CategoryManager) -> str:
    """Create a test category and return its ID for snippet tests."""
    cat = Category(category_name="TestCategory")
    category_manager.save_category(cat)
    return cat.category_id


@pytest.fixture
def valid_snippet_data(
    snippet_category_fixture: str,
) -> Dict[str, Union[str, str]]:
    """Provide valid snippet data for testing."""
    return {
        "category_id": snippet_category_fixture,
        "snippet_name": "TestSnippet",
        "content": "This is test content for the snippet.",
    }


@pytest.fixture(scope="function")
def category_mgr(db_with_tables: DatabaseManager) -> CategoryManager:
    """Fixture to provide a CategoryManager instance (alias)."""
    return CategoryManager(db_with_tables)


@pytest.fixture(scope="function")
def snippet_mgr(db_with_tables: DatabaseManager) -> SnippetManager:
    """Fixture to provide a SnippetManager instance (alias)."""
    return SnippetManager(db_with_tables)


@pytest.fixture(scope="function")
def sample_category(category_mgr: CategoryManager) -> Category:
    """Fixture to create and provide a sample category for snippet tests."""
    from models.category_manager import CategoryNotFound
    
    try:
        # Attempt to retrieve if it exists from a previous failed test run
        return category_mgr.get_category_by_name("Test Category for Snippets")
    except CategoryNotFound:
        category = Category(
            category_id=str(uuid.uuid4()),
            category_name="Test Category for Snippets",
            description="",
        )
        category_mgr.save_category(category)
        return category
