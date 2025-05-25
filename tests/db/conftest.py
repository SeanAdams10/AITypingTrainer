"""
Pytest configuration for database tests.

This file imports fixtures from the db_helpers module to make them available to all
test files in the db directory without explicit imports.
"""

import pytest

# Import the fixtures from db_helpers
from tests.helpers.db_helpers import temp_db, db_manager, db_with_tables  # noqa

# By importing these fixtures here, they will be available to all test files
# in this directory without requiring explicit imports in each test file.
