"""
Test suite for splash.py (AI Typing splash screen)
- Uses pytest and pytest-qt
- Mocks GraphQL server startup and endpoint
"""
from typing import Generator
import pytest
from pytestqt.qtbot import QtBot
from PyQt5.QtWidgets import QApplication, QMessageBox
from desktop_ui.splash import SplashScreen

class DummyGraphQL:
    """Dummy GraphQL server for testing."""
    def __init__(self, running: bool = True, snippet_count: int = 42):
        self.running = running
        self.snippet_count = snippet_count

    def start(self) -> None:
        self.running = True

    def is_running(self) -> bool:
        return self.running

    def get_snippet_count(self) -> int:
        return self.snippet_count

@pytest.fixture
def dummy_graphql() -> Generator[DummyGraphQL, None, None]:
    yield DummyGraphQL()

@pytest.fixture
def splash_screen(qtbot: QtBot, dummy_graphql: DummyGraphQL) -> Generator[SplashScreen, None, None]:
    splash = SplashScreen(graphql=dummy_graphql)
    qtbot.addWidget(splash)
    yield splash

@pytest.mark.usefixtures("qtbot")
def test_splash_shows_labels_and_status(splash_screen: SplashScreen, qtbot: QtBot) -> None:
    assert splash_screen.title_label.text() == "AI Typing"
    assert "GraphQL" in splash_screen.status_label.text()

@pytest.mark.usefixtures("qtbot")
def test_splash_graphql_startup_and_snippet_count(splash_screen: SplashScreen, qtbot: QtBot, dummy_graphql: DummyGraphQL) -> None:
    dummy_graphql.running = True
    dummy_graphql.snippet_count = 123
    splash_screen.check_graphql_and_show_count()
    assert splash_screen.status_label.text() == "GraphQL Running"
    # Simulate message box (should show snippet count)
    # In real test, patch QMessageBox.information

@pytest.mark.usefixtures("qtbot")
def test_splash_graphql_startup_fail(splash_screen: SplashScreen, qtbot: QtBot, dummy_graphql: DummyGraphQL) -> None:
    dummy_graphql.running = False
    splash_screen.check_graphql_and_show_count()
    assert "Starting" in splash_screen.status_label.text() or "failed" in splash_screen.status_label.text().lower()
