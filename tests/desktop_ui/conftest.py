"""
Pytest configuration for desktop UI tests.
"""
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def app():
    """Create a QApplication instance for testing without flask interference."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    
    # Add a attribute to prevent pytest-flask from trying to modify it
    app.response_class = None
