"""
Service initialization module.

This module provides factory functions for creating and initializing service instances
with their required dependencies.
"""

from typing import Tuple

from db.database_manager import DatabaseManager


def init_services(db_path: str) -> Tuple[DatabaseManager, object, object]:
    """
    Initialize and return all service instances with their dependencies.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        A tuple containing (db_manager, snippet_manager, session_manager)

    Example:
        db, snippets, sessions = init_services("path/to/db.sqlite")
    """
    # Initialize database manager
    db_manager = DatabaseManager(db_path)

    # Lazy imports to avoid circular dependencies
    try:
        from models.session_manager import SessionManager
        from models.snippet_manager import SnippetManager

        # Initialize managers with dependencies
        snippet_manager = SnippetManager(db_manager)
        session_manager = SessionManager(db_manager)

        return db_manager, snippet_manager, session_manager

    except ImportError as e:
        # Close the database connection if initialization fails
        db_manager.close()
        raise ImportError(
            "Failed to initialize services. Please ensure all required modules are available."
        ) from e
