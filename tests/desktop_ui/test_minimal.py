"""
A minimal test to isolate PySide6/pytest hanging issues.
"""
import pytest
from unittest.mock import MagicMock
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

def test_minimal(qtbot):
    """A minimal test that creates a simple widget."""
    widget = QtWidgets.QLabel("Test")
    widget.show()
    qtbot.addWidget(widget)
    assert widget.text() == "Test"
