#!/usr/bin/env python
"""
Test cases for TypingDrillScreen UI component.

This module contains tests for the TypingDrillScreen class, focusing on
session persistence and database interactions.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.database_manager import DatabaseManager  # noqa: E402
from desktop_ui.typing_drill import TypingDrillScreen  # noqa: E402
from models.session_manager import SessionManager  # noqa: E402


class QtBot:
    """Simple QtBot class to replace pytest-qt's qtbot when it's not available.

    This class provides basic functionality for testing Qt applications without
    requiring the full pytest-qt package.
    """

    def __init__(self, app: QApplication) -> None:
        """Initialize the QtBot with a QApplication instance."""
        self.app = app
        self.widgets = []

    def addWidget(self, widget: Any) -> Any:
        """Keep track of widgets to prevent garbage collection.

        Args:
            widget: The widget to track

        Returns:
            The same widget for method chaining
        """
        self.widgets.append(widget)
        return widget

    def mouseClick(
        self, widget: Any, button: Qt.MouseButton = Qt.LeftButton, pos: Any = None
    ) -> None:
        """Simulate a mouse click on a widget.

        Args:
            widget: The widget to click
            button: The mouse button to use
            pos: Optional position to click (defaults to widget center)
        """
        if pos is None and hasattr(widget, "rect"):
            pos = widget.rect().center()
        if hasattr(widget, "click"):
            widget.click()
        self.app.processEvents()

    def waitUntil(self, callback: Any, timeout: int = 1000) -> bool:
        """Wait until the callback returns True or timeout occurs.

        Args:
            callback: Function to call that returns a boolean
            timeout: Timeout in milliseconds (unused in this implementation)

        Returns:
            The result of the callback
        """
        return callback()

    def wait(self, ms: int) -> None:
        """Wait for the specified number of milliseconds.

        Args:
            ms: Milliseconds to wait
        """
        self.app.processEvents()


@pytest.fixture(scope="module")
def qtapp() -> Generator[QApplication, None, None]:
    """Fixture to create a QApplication instance.

    Using qtapp name to avoid conflicts with pytest-flask.

    Yields:
        QApplication: The application instance
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def qtbot(qtapp: QApplication) -> QtBot:
    """Create a QtBot instance for testing.

    Args:
        qtapp: The QApplication fixture

    Returns:
        QtBot: A test helper for Qt applications
    """
    return QtBot(qtapp)


@pytest.fixture
def db_manager(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    """Create a temporary database with test data.

    Args:
        tmp_path: Pytest fixture for temporary directory

    Yields:
        DatabaseManager: Configured database manager with test data
    """
    db_path = tmp_path / "test_ui_typing.db"
    dbm = DatabaseManager(str(db_path))
    dbm.init_tables()

    # Create test data
    cursor = dbm.conn.cursor()

    # Test category
    cursor.execute(
        """
        INSERT INTO categories (category_name)
        VALUES (?)
        """,
        ("Test Category",),
    )
    category_id = cursor.lastrowid

    # Test snippet with ID=2
    cursor.execute(
        """
        INSERT INTO snippets (snippet_id, category_id, snippet_name)
        VALUES (?, ?, ?)
        """,
        (2, category_id, "Test Snippet"),
    )

    # Add snippet content
    cursor.execute(
        """
        INSERT INTO snippet_parts (snippet_id, part_number, content)
        VALUES (?, ?, ?)
        """,
        (2, 1, "hello world"),
    )

    yield dbm
    dbm.close()


@pytest.fixture
def session_manager(db_manager: DatabaseManager) -> SessionManager:
    """Create a SessionManager instance.

    Args:
        db_manager: Database manager fixture

    Returns:
        SessionManager: Configured session manager
    """
    return SessionManager(db_manager)


def create_mock_keystrokes(text: str) -> List[Dict[str, Any]]:
    """Create mock keystroke data for testing.

    Args:
        text: The text that was typed

    Returns:
        List of keystroke dictionaries
    """
    now = datetime.now()
    return [
        {
            "char_position": i,
            "char_typed": char,
            "expected_char": char,
            "timestamp": now + timedelta(seconds=i),
            "time_since_previous": 100,  # ms
            "is_error": 0,
        }
        for i, char in enumerate(text)
    ]


def test_typing_drill_screen_session_persistence(
    qtapp: QApplication, session_manager: SessionManager
) -> None:
    """Test objective: Verify session data is correctly saved to the database.

    This test verifies that:
    - Session data is properly saved to the database
    - Basic session properties match expected values
    - The session can be retrieved from the database

    Args:
        qtapp: QApplication fixture
        session_manager: SessionManager fixture
    """
    # Setup test parameters
    snippet_id = 2
    start = 0
    end = 5
    content = "hello"  # Shorter content for testing

    # Create mock keystrokes
    keystrokes = create_mock_keystrokes(content)

    # Mock UI components to run headlessly
    with patch("desktop_ui.typing_drill.TypingDrillScreen.exec_", return_value=QDialog.Accepted):
        with patch("desktop_ui.typing_drill.CompletionDialog"):
            # Create the dialog (won't actually show due to patches)
            dlg = TypingDrillScreen(
                snippet_id, start, end, content, db_manager=session_manager.db_manager
            )

            # Set the keystrokes on the dialog
            dlg.keystrokes = keystrokes

            # Set session start and end times
            dlg.session_start_time = datetime.now()
            dlg.session_end_time = datetime.now() + timedelta(seconds=10)

            # Simulate session completion
            stats = {
                "total_time": 10.0,
                "wpm": 60.0,
                "cpm": 300.0,
                "expected_chars": len(content),
                "actual_chars": len(content),
                "errors": 0,
                "accuracy": 100.0,
                "efficiency": 100.0,
                "correctness": 100.0,
            }

            # Save the session data
            dlg.save_session(stats, session_manager)

            # Verify database entries
            sessions = session_manager.list_sessions_for_snippet(snippet_id)
            assert len(sessions) == 1, "Expected exactly one session"

            # Check basic properties match
            session = sessions[0]
            assert session.content == content, "Content mismatch"
            assert session.snippet_id == snippet_id, "Snippet ID mismatch"
            assert session.expected_chars == len(content), (
                f"Expected {len(content)} chars, got {session.expected_chars}"
            )
            assert session.actual_chars == len(content), (
                f"Expected {len(content)} chars, got {session.actual_chars}"
            )
            assert session.errors == 0, f"Expected 0 errors, got {session.errors}"
            # Check accuracy with a small delta for floating point comparison
            assert abs(session.accuracy - 1.0) < 0.01, (
                f"Expected ~100% accuracy, got {session.accuracy}"
            )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
