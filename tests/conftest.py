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
pytest_plugins = ['pytest-qt']


@pytest.fixture(scope="function")
def db_manager() -> Generator[DatabaseManager, None, None]:
    """Create a DatabaseManager instance with a PostgreSQL Docker database.

    Yields:
        DatabaseManager: A DatabaseManager instance connected to Docker Postgres

    The Docker container is automatically cleaned up after the test completes.
    """
    try:
        db = DatabaseManager(connection_type=ConnectionType.POSTGRESS_DOCKER)
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass
