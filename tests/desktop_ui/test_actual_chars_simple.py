"""
Test for verifying actual_chars calculation in typing drill.

This test specifically validates that actual_chars is correctly calculated
as the count of all keystrokes excluding backspace keystrokes.
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

import pytest
from PySide6.QtWidgets import QApplication

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import required modules
from desktop_ui.typing_drill import TypingDrillScreen


def create_keystroke(
    position: int, char: str, timestamp: float = 1.0, is_error: int = 0
) -> Dict[str, Any]:
    """Helper to create a keystroke record for testing.

    Args:
        position: Cursor position for the keystroke
        char: Character typed
        timestamp: Time when keystroke occurred
        is_error: Whether this keystroke produced an error (1=yes, 0=no)

    Returns:
        Dict with keystroke data
    """
    return {
        "char_position": position,
        "char_typed": char,
        "expected_char": "x",  # Placeholder, will be updated as needed
        "timestamp": datetime.fromtimestamp(timestamp),
        "is_error": is_error,
        "is_backspace": char == "\b",
    }


@pytest.fixture(scope="module")
def app():
    """Create a QApplication instance for testing."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_actual_chars_basic_calculation(app):
    """Test the basic calculation of actual_chars in _calculate_stats method."""
    # app fixture initializes QApplication
    # Create a mock typing drill
    drill = TypingDrillScreen(
        snippet_id=-1,
        start=0,
        end=10,
        content="The",
        db_manager=None,  # Not needed for direct calculation
    )

    # Test Case 1: Simple typing (T-h-e)
    drill.keystrokes = [
        create_keystroke(0, "T"),
        create_keystroke(1, "h"),
        create_keystroke(2, "e"),
    ]
    drill.typed_chars = 3  # This is what would be set in the UI normally

    # Calculate stats
    stats = drill._calculate_stats()

    # Verify
    assert stats["actual_chars"] == 3, f"Expected actual_chars=3, got {stats['actual_chars']}"
    assert stats["backspace_count"] == 0, (
        f"Expected backspace_count=0, got {stats['backspace_count']}"
    )

    # Test Case 2: T-g-backspace-h-e (from requirements)
    drill.keystrokes = [
        create_keystroke(0, "T"),
        create_keystroke(1, "g", is_error=1),
        create_keystroke(1, "\b"),
        create_keystroke(1, "h"),
        create_keystroke(2, "e"),
    ]
    drill.typed_chars = 3  # Final text is "The"

    # Calculate stats
    stats = drill._calculate_stats()

    # Verify
    assert stats["actual_chars"] == 4, f"Expected actual_chars=4, got {stats['actual_chars']}"
    assert stats["backspace_count"] == 1, (
        f"Expected backspace_count=1, got {stats['backspace_count']}"
    )

    # Test Case 3: T-backspace-T-backspace-T-h-backspace-h-e (from requirements)
    drill.keystrokes = [
        create_keystroke(0, "T"),
        create_keystroke(0, "\b"),
        create_keystroke(0, "T"),
        create_keystroke(0, "\b"),
        create_keystroke(0, "T"),
        create_keystroke(1, "h"),
        create_keystroke(1, "\b"),
        create_keystroke(1, "h"),
        create_keystroke(2, "e"),
    ]
    drill.typed_chars = 3  # Final text is "The"

    # Calculate stats
    stats = drill._calculate_stats()

    # Verify
    assert stats["actual_chars"] == 6, f"Expected actual_chars=6, got {stats['actual_chars']}"
    assert stats["backspace_count"] == 3, (
        f"Expected backspace_count=3, got {stats['backspace_count']}"
    )

    # Edge Case 4: Multiple consecutive backspaces and restart
    drill.content = "test"
    drill.keystrokes = [
        create_keystroke(0, "t"),
        create_keystroke(1, "e"),
        create_keystroke(2, "s"),
        create_keystroke(3, "t"),
        create_keystroke(3, "\b"),
        create_keystroke(2, "\b"),
        create_keystroke(1, "\b"),
        create_keystroke(0, "\b"),
        create_keystroke(0, "t"),
        create_keystroke(1, "e"),
        create_keystroke(2, "s"),
        create_keystroke(3, "t"),
    ]
    drill.typed_chars = 4  # Final text is "test"

    # Calculate stats
    stats = drill._calculate_stats()

    # Verify
    assert stats["actual_chars"] == 8, f"Expected actual_chars=8, got {stats['actual_chars']}"
    assert stats["backspace_count"] == 4, (
        f"Expected backspace_count=4, got {stats['backspace_count']}"
    )

    print("All actual_chars calculation tests passed!")


if __name__ == "__main__":
    # When running directly, execute the tests with pytest
    sys.exit(pytest.main(["-xvs", __file__]))
