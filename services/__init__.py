"""Service initialization module.

Factory helpers to create and wire services with their dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from db.database_manager import DatabaseManager

if TYPE_CHECKING:  # Avoid import cycles at runtime
    from models.session_manager import SessionManager
    from models.snippet_manager import SnippetManager


def init_services(db_path: str) -> Tuple[DatabaseManager, "SnippetManager", "SessionManager"]:
    """Initialize and return core service instances.

    Example:
        db, snippets, sessions = init_services("path/to/db.sqlite").
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
