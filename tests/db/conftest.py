"""Pytest configuration for database tests.

All database fixtures are now provided globally in tests/conftest.py:
- db_manager (session scope)
- db_with_tables (session scope) 
- initialized_db (session scope)

This file is kept for any future db-specific fixtures if needed.
"""

# Note: All database fixtures have been moved to tests/conftest.py for global availability
