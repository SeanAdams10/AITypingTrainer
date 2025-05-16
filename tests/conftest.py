"""
Pytest configuration for the test suite.
"""
import os
import sys
import tempfile
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest

from db.database_manager import DatabaseManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Create the database and initialize tables
    db = DatabaseManager(db_path)
    db.init_tables()
    
    yield db
    
    # Clean up
    db.close()
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except OSError:
        pass
