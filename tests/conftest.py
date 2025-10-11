"""Pytest configuration for the test suite."""

# Standard library imports
import sys
from pathlib import Path
from typing import Generator

# Third-party imports
import pytest

# Local application imports
from db.database_manager import ConnectionType, DatabaseManager

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add qtbot to all tests that need it
pytest_plugins = ["pytest-qt"]

# Test data constants for initialized_db fixture
TEST_TABLE_NAME = "test_table"
TEST_DATA = [
    (1, "Alice", 30, "alice@example.com"),
    (2, "Bob", 25, "bob@example.com"),
    (3, "Charlie", 35, "charlie@example.com"),
]


@pytest.fixture(scope="function")
def db_manager() -> Generator[DatabaseManager, None, None]:
    """Create a DatabaseManager instance with a PostgreSQL Docker database.

    Yields:
        DatabaseManager: A DatabaseManager instance connected to Docker Postgres

    The Docker container is automatically cleaned up after the test completes.
    """
    db = DatabaseManager(connection_type=ConnectionType.POSTGRESS_DOCKER)
    yield db


@pytest.fixture(scope="function")
def initialized_db() -> DatabaseManager:
    """Create a database with a test table and sample data.

    Args:
        db_manager: DatabaseManager instance

    Returns:
        DatabaseManager: The same DatabaseManager instance with test data
    """
    db_manager = DatabaseManager(connection_type=ConnectionType.POSTGRESS_DOCKER)
    # Create a test table
    db_manager.execute(
        f"""
        CREATE TABLE {TEST_TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT UNIQUE
        )
        """
    )

    # Insert test data
    for row in TEST_DATA:
        db_manager.execute(f"INSERT INTO {TEST_TABLE_NAME} VALUES (?, ?, ?, ?)", row)

    return db_manager


@pytest.fixture(scope="function")
def db_with_tables() -> DatabaseManager:
    """Create a database with all tables initialized.

    Args:
        db_manager: DatabaseManager instance (provided by db_manager fixture)

    Returns:
        DatabaseManager: The same DatabaseManager instance with tables initialized
    """
    db_manager = DatabaseManager(connection_type=ConnectionType.POSTGRESS_DOCKER)
    db_manager.init_tables()
    return db_manager
