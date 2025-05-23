"""
Test for verifying actual_chars calculation in typing drill.

This test specifically validates that actual_chars is correctly calculated
as the count of all keystrokes excluding backspace keystrokes.
"""
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, NamedTuple

import pytest

# Import PyQt5 classes required for the test
from PyQt5.QtWidgets import QApplication

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import required modules from the project
from desktop_ui.typing_drill import TypingDrillScreen


# Named tuple for keystroke test scenarios
class KeystrokeScenario(NamedTuple):
    """Represents a test scenario for typing drill keystrokes."""
    name: str
    content: str
    keystrokes: List[Dict[str, Any]]
    expected_accuracy: float
    expected_efficiency: float = 100.0
    expected_correctness: float = 100.0
    expected_errors: int = 0
    expected_actual_chars: int = 0
    expected_backspace_count: int = 0

def create_keystroke(position: int, character: str, timestamp: float = 1.0, is_error: int = 0) -> Dict[str, Any]:
    """Helper to create a keystroke record.
    
    Args:
        position: Cursor position for the keystroke
        character: Character typed
        timestamp: Time when keystroke occurred
        is_error: Whether this keystroke produced an error (1=yes, 0=no)
        
    Returns:
        Dict with keystroke data
    """
    # Ensure timestamp is properly handled
    try:
        timestamp_dt = datetime.fromtimestamp(timestamp)
    except (ValueError, OverflowError, OSError):
        # If there's any issue with the timestamp, use current time
        timestamp_dt = datetime.now()
        
    return {
        'char_position': position,
        'char_typed': character,  # This is the key the application looks for
        'expected_char': 'x',  # Placeholder, will be filled as needed
        'timestamp': timestamp_dt,
        'is_error': is_error,
        'is_backspace': character == '\b'
    }

@pytest.fixture
def app():
    """Create a QApplication instance for testing."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app

@pytest.fixture
def mock_typing_drill(app):
    """Create a mock TypingDrillScreen for direct testing."""
    # Create the typing drill screen with no DB manager
    drill = TypingDrillScreen(
        snippet_id=-1,  # Manual text
        start=0,
        end=10,
        content="test content",
        db_manager=None
    )
    
    return drill

# Define all test scenarios once as module-level variables
# This makes them available to all test functions

# Test Case 1: Simple backspace correction (T-g-backspace-h-e)
# Expected: actual_chars = 4 (T, g, h, e - excluding backspace), backspace_count = 1
SCENARIO_1 = KeystrokeScenario(
    name="Simple Backspace Correction",
    content="The",
    keystrokes=[
        create_keystroke(0, 'T'),
        create_keystroke(1, 'g', is_error=1),
        create_keystroke(1, '\b'),
        create_keystroke(1, 'h'),
        create_keystroke(2, 'e')
    ],
    expected_accuracy=90.0,
    expected_errors=1,
    expected_actual_chars=4,  # T, g, h, e (excluding backspace)
    expected_backspace_count=1
)

# Test Case 2: Multiple backspaces (T-backspace-T-backspace-T-h-backspace-h-e)
# Expected: actual_chars = 6 (T, T, T, h, h, e - excluding backspaces), backspace_count = 3
SCENARIO_2 = KeystrokeScenario(
    name="Multiple Backspaces",
    content="The",
    keystrokes=[
        create_keystroke(0, 'T'),
        create_keystroke(0, '\b'),
        create_keystroke(0, 'T'),
        create_keystroke(0, '\b'),
        create_keystroke(0, 'T'),
        create_keystroke(1, 'h'),
        create_keystroke(1, '\b'),
        create_keystroke(1, 'h'),
        create_keystroke(2, 'e')
    ],
    expected_accuracy=75.0,
    expected_errors=3,
    expected_actual_chars=6,  # T, T, T, h, h, e (excluding backspaces)
    expected_backspace_count=3
)

# Edge Case 3: Backspaces at beginning and consecutive backspaces
SCENARIO_3 = KeystrokeScenario(
    name="Edge Case Backspaces",
    content="test",
    keystrokes=[
        create_keystroke(0, '\b'),  # Start with backspace
        create_keystroke(0, 't'),
        create_keystroke(1, 'e'),
        create_keystroke(2, 's'),
        create_keystroke(3, 't'),
        create_keystroke(3, '\b'),  # Consecutive backspaces
        create_keystroke(2, '\b'),
        create_keystroke(1, '\b'),
        create_keystroke(0, '\b'),
        create_keystroke(0, 't'),   # Start over
        create_keystroke(1, 'e'),
        create_keystroke(2, 's'),
        create_keystroke(3, 't')
    ],
    expected_accuracy=60.0,
    expected_errors=5,
    expected_actual_chars=8,  # t, e, s, t, t, e, s, t (excluding backspaces)
    expected_backspace_count=5
)

# Edge Case 4: Special characters and longer input
SCENARIO_4 = KeystrokeScenario(
    name="Special Characters",
    content="Hello, world!",
    keystrokes=[
        create_keystroke(0, 'H'),
        create_keystroke(1, 'e'),
        create_keystroke(2, 'l'),
        create_keystroke(3, 'l'),
        create_keystroke(4, 'o'),
        create_keystroke(5, ','),
        create_keystroke(6, ' '),
        create_keystroke(7, 'w'),
        create_keystroke(8, 'e'),  # Error, should be 'o'
        create_keystroke(8, '\b'),
        create_keystroke(8, 'o'),
        create_keystroke(9, 'r'),
        create_keystroke(10, 'l'),
        create_keystroke(11, 'd'),
        create_keystroke(12, '!')
    ],
    expected_accuracy=93.3,
    expected_errors=1,
    expected_actual_chars=14,  # All keystrokes excluding the backspace
    expected_backspace_count=1
)

# Edge Case 5: Perfect typing with no backspaces
SCENARIO_5 = KeystrokeScenario(
    name="Perfect Typing",
    content="Python",
    keystrokes=[
        create_keystroke(0, 'P'),
        create_keystroke(1, 'y'),
        create_keystroke(2, 't'),
        create_keystroke(3, 'h'),
        create_keystroke(4, 'o'),
        create_keystroke(5, 'n')
    ],
    expected_accuracy=100.0,
    expected_errors=0,
    expected_actual_chars=6,  # All characters, no backspaces
    expected_backspace_count=0
)


def test_scenario_1_simple_backspace(mock_typing_drill):
    """Test simple backspace correction scenario."""
    scenario = SCENARIO_1
    print(f"\nTesting {scenario.name}")
    
    # Setup the drill with scenario data
    mock_typing_drill.content = scenario.content
    mock_typing_drill.keystrokes = scenario.keystrokes
    mock_typing_drill.typed_chars = len(scenario.content)
    
    # Calculate stats directly
    stats = mock_typing_drill._calculate_stats()
    
    # Check actual_chars
    assert stats["actual_chars"] == scenario.expected_actual_chars
    # Check backspace_count
    assert stats["backspace_count"] == scenario.expected_backspace_count
    print(f"Test passed for {scenario.name}")


def test_scenario_2_multiple_backspaces(mock_typing_drill):
    """Test scenario with multiple backspaces."""
    scenario = SCENARIO_2
    print(f"\nTesting {scenario.name}")
    
    # Setup the drill with scenario data
    mock_typing_drill.content = scenario.content
    mock_typing_drill.keystrokes = scenario.keystrokes
    mock_typing_drill.typed_chars = len(scenario.content)
    
    # Calculate stats directly
    stats = mock_typing_drill._calculate_stats()
    
    # Check actual_chars
    assert stats["actual_chars"] == scenario.expected_actual_chars
    # Check backspace_count
    assert stats["backspace_count"] == scenario.expected_backspace_count
    print(f"Test passed for {scenario.name}")


def test_scenario_3_edge_case_backspaces(mock_typing_drill):
    """Test edge case with backspaces at beginning and consecutive backspaces."""
    scenario = SCENARIO_3
    print(f"\nTesting {scenario.name}")
    
    # Setup the drill with scenario data
    mock_typing_drill.content = scenario.content
    mock_typing_drill.keystrokes = scenario.keystrokes
    mock_typing_drill.typed_chars = len(scenario.content)
    
    # Calculate stats directly
    stats = mock_typing_drill._calculate_stats()
    
    # Check actual_chars
    assert stats["actual_chars"] == scenario.expected_actual_chars
    # Check backspace_count
    assert stats["backspace_count"] == scenario.expected_backspace_count
    print(f"Test passed for {scenario.name}")


def test_scenario_4_special_characters(mock_typing_drill):
    """Test scenario with special characters and longer input."""
    scenario = SCENARIO_4
    print(f"\nTesting {scenario.name}")
    
    # Setup the drill with scenario data
    mock_typing_drill.content = scenario.content
    mock_typing_drill.keystrokes = scenario.keystrokes
    mock_typing_drill.typed_chars = len(scenario.content)
    
    # Calculate stats directly
    stats = mock_typing_drill._calculate_stats()
    
    # Check actual_chars
    assert stats["actual_chars"] == scenario.expected_actual_chars
    # Check backspace_count
    assert stats["backspace_count"] == scenario.expected_backspace_count
    print(f"Test passed for {scenario.name}")


def test_scenario_5_perfect_typing(mock_typing_drill):
    """Test scenario with perfect typing (no backspaces)."""
    scenario = SCENARIO_5
    print(f"\nTesting {scenario.name}")
    
    # Setup the drill with scenario data
    mock_typing_drill.content = scenario.content
    mock_typing_drill.keystrokes = scenario.keystrokes
    mock_typing_drill.typed_chars = len(scenario.content)
    
    # Calculate stats directly
    stats = mock_typing_drill._calculate_stats()
    
    # Check actual_chars
    assert stats["actual_chars"] == scenario.expected_actual_chars
    # Check backspace_count
    assert stats["backspace_count"] == scenario.expected_backspace_count
    print(f"Test passed for {scenario.name}")


if __name__ == "__main__":
    # When running directly, execute the tests with pytest
    sys.exit(pytest.main(["-xvs", __file__]))
