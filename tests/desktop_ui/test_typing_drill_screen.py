"""
Test TypingDrillScreen UI logic and session persistence (TDD for desktop UI).
"""

import pytest
from PyQt5.QtWidgets import QApplication
from desktop_ui.typing_drill import TypingDrillScreen
from db.database_manager import DatabaseManager
from models.practice_session import PracticeSessionManager
import sys


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def db_manager(tmp_path):
    db_path = tmp_path / "test_ui_typing.db"
    dbm = DatabaseManager(str(db_path))
    dbm.initialize_tables()
    yield dbm
    dbm.close()


@pytest.fixture
def session_manager(db_manager):
    return PracticeSessionManager(db_manager)


def test_typing_drill_screen_session_persistence(app, session_manager):
    # Simulate launching the UI with params
    snippet_id = 2
    start = 0
    end = 5
    content = "hello world"
    dlg = TypingDrillScreen(snippet_id, start, end, content)
    # Simulate session completion (normally would be triggered by UI events)
    stats = {
        "total_time": 10,
        "wpm": 60.0,
        "cpm": 300.0,
        "expected_chars": len(content),
        "actual_chars": len(content),
        "errors": 0,
        "accuracy": 1.0,
    }
    # Add a method to TypingDrillScreen to persist session (to be implemented)
    dlg.save_session(stats, session_manager)
    # Check DB
    sessions = session_manager.list_sessions_for_snippet(snippet_id)
    assert len(sessions) == 1
    assert sessions[0].content == content
    assert sessions[0].snippet_id == snippet_id
    assert sessions[0].expected_chars == len(content)
    assert sessions[0].actual_chars == len(content)
    assert sessions[0].errors == 0
    assert sessions[0].accuracy == 1.0
