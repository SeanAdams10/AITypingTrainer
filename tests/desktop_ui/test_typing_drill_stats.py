"""
Test objective: Verify typing drill statistics calculations for efficiency, correctness, and accuracy.

This module tests the stat calculation logic in TypingDrillScreen to ensure:
- Efficiency = expected characters / total keystroke count (excluding backspaces)
- Correctness = correct characters in final text / expected characters
- Accuracy = efficiency × correctness

All tests use temporary databases and do not affect production data.
"""

import datetime
import os
import sys
from unittest.mock import Mock

# Add parent directory to path to find modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from PySide6.QtWidgets import QApplication

from db.database_manager import DatabaseManager
from desktop_ui.typing_drill import TypingDrillScreen


class TestTypingDrillStats:
    """Test class for typing drill statistics calculations."""

    @pytest.fixture
    def app(self, qtapp: QApplication) -> QApplication:
        """Test objective: Provide Qt application instance for UI tests."""
        return qtapp

    @pytest.fixture
    def mock_db_manager(self) -> Mock:
        """Test objective: Provide mock database manager for isolated testing."""
        return Mock(spec=DatabaseManager)

    @pytest.fixture
    def typing_drill(self, app: QApplication, mock_db_manager: Mock) -> TypingDrillScreen:
        """Test objective: Create a typing drill instance for testing."""
        drill = TypingDrillScreen(
            snippet_id=1,
            start=0,
            end=10,
            content="hello test",
            db_manager=mock_db_manager,
            user_id="test_user",
            keyboard_id="test_keyboard",
        )
        return drill

    def test_efficiency_calculation_perfect_typing(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify efficiency calculation when typing perfectly without extra keystrokes.

        Expected: efficiency = 100% when expected_chars equals keystrokes (excluding backspaces)
        """
        # Setup: 10 expected characters, 10 keystrokes, no backspaces
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

        # 10 keystrokes, no backspaces
        typing_drill.keystrokes = [
            {"char": "h"},
            {"char": "e"},
            {"char": "l"},
            {"char": "l"},
            {"char": "o"},
            {"char": " "},
            {"char": "t"},
            {"char": "e"},
            {"char": "s"},
            {"char": "t"},
        ]

        stats = typing_drill._calculate_stats()

        # Expected chars = 10, total keystrokes excluding backspaces = 10
        # Efficiency = 10 / 10 * 100 = 100%
        assert stats["efficiency"] == 100.0
        assert stats["expected_chars"] == 10
        assert stats["total_keystrokes"] == 10
        assert stats["backspace_count"] == 0

    def test_efficiency_calculation_with_extra_keystrokes(
        self, typing_drill: TypingDrillScreen
    ) -> None:
        """
        Test objective: Verify efficiency calculation when extra keystrokes are made.

        Expected: efficiency < 100% when more keystrokes than expected characters
        """
        # Setup: 10 expected characters, 15 keystrokes, no backspaces
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

        # 15 keystrokes, no backspaces (extra keystrokes due to corrections)
        typing_drill.keystrokes = [
            {"char": "h"},
            {"char": "e"},
            {"char": "l"},
            {"char": "l"},
            {"char": "o"},
            {"char": " "},
            {"char": "t"},
            {"char": "e"},
            {"char": "s"},
            {"char": "t"},
            {"char": "x"},
            {"char": "y"},
            {"char": "z"},
            {"char": "a"},
            {"char": "b"},
        ]

        stats = typing_drill._calculate_stats()

        # Expected chars = 10, total keystrokes excluding backspaces = 15
        # Efficiency = 10 / 15 * 100 = 66.67%
        expected_efficiency = 10 / 15 * 100
        assert abs(stats["efficiency"] - expected_efficiency) < 0.01
        assert stats["total_keystrokes"] == 15
        assert stats["backspace_count"] == 0

    def test_efficiency_calculation_with_backspaces(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify efficiency calculation excludes backspaces from keystroke count.

        Expected: backspaces are not counted in the efficiency calculation denominator
        """
        # Setup: 10 expected characters, 15 total keystrokes (3 backspaces), 12 non-backspace keystrokes
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

        # 15 total keystrokes: 12 regular + 3 backspaces
        typing_drill.keystrokes = [
            {"char": "h"},
            {"char": "e"},
            {"char": "l"},
            {"char": "l"},
            {"char": "o"},
            {"char": " "},
            {"char": "t"},
            {"char": "e"},
            {"char": "s"},
            {"char": "t"},
            {"char": "x"},
            {"char": "y"},
            {"is_backspace": True},
            {"is_backspace": True},
            {"is_backspace": True},
        ]

        stats = typing_drill._calculate_stats()

        # Expected chars = 10, total keystrokes excluding backspaces = 12
        # Efficiency = 10 / 12 * 100 = 83.33%
        expected_efficiency = 10 / 12 * 100
        assert abs(stats["efficiency"] - expected_efficiency) < 0.01
        assert stats["total_keystrokes"] == 15
        assert stats["backspace_count"] == 3

    def test_correctness_calculation_perfect_typing(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify correctness calculation when typing perfectly without errors.

        Expected: correctness = 100% when correct_chars equals expected_chars
        """
        # Setup: 10 expected characters, 10 correct characters, 0 errors
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        typing_drill.keystrokes = [{"char": "h"}] * 10  # Simple keystroke data

        stats = typing_drill._calculate_stats()

        # Correct chars = actual_chars - errors = 10 - 0 = 10
        # Correctness = 10 / 10 * 100 = 100%
        assert stats["correctness"] == 100.0
        assert stats["correct_chars"] == 10
        assert stats["expected_chars"] == 10
        assert stats["errors"] == 0

    def test_correctness_calculation_with_errors(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify correctness calculation when typing with errors.

        Expected: correctness < 100% when errors are present
        """
        # Setup: 10 expected characters, 8 correct characters, 2 errors
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 2
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        typing_drill.keystrokes = [{"char": "h"}] * 10  # Simple keystroke data

        stats = typing_drill._calculate_stats()

        # Correct chars = actual_chars - errors = 10 - 2 = 8
        # Correctness = 8 / 10 * 100 = 80%
        assert stats["correctness"] == 80.0
        assert stats["correct_chars"] == 8
        assert stats["expected_chars"] == 10
        assert stats["errors"] == 2

    def test_accuracy_calculation_perfect_performance(
        self, typing_drill: TypingDrillScreen
    ) -> None:
        """
        Test objective: Verify accuracy calculation with perfect efficiency and correctness.

        Expected: accuracy = 100% when both efficiency and correctness are 100%
        """
        # Setup: Perfect typing scenario
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        typing_drill.keystrokes = [{"char": "h"}] * 10  # 10 keystrokes, no backspaces

        stats = typing_drill._calculate_stats()

        # Efficiency = 10 / 10 * 100 = 100%
        # Correctness = 10 / 10 * 100 = 100%
        # Accuracy = 100 * 100 / 100 = 100%
        assert stats["efficiency"] == 100.0
        assert stats["correctness"] == 100.0
        assert stats["accuracy"] == 100.0

    def test_accuracy_calculation_mixed_performance(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify accuracy calculation with mixed efficiency and correctness.

        Expected: accuracy = efficiency × correctness
        """
        # Setup: Mixed performance scenario
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 10
        typing_drill.session.errors = 2  # 2 errors, so 8 correct
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        # 15 keystrokes including 3 backspaces = 12 non-backspace keystrokes
        typing_drill.keystrokes = [{"char": "h"}] * 12 + [{"is_backspace": True}] * 3

        stats = typing_drill._calculate_stats()

        # Efficiency = 10 / 12 * 100 = 83.33%
        # Correctness = 8 / 10 * 100 = 80%
        # Accuracy = 83.33 * 80 / 100 = 66.67%
        expected_efficiency = 10 / 12 * 100
        expected_correctness = 8 / 10 * 100
        expected_accuracy = expected_efficiency * expected_correctness / 100

        assert abs(stats["efficiency"] - expected_efficiency) < 0.01
        assert abs(stats["correctness"] - expected_correctness) < 0.01
        assert abs(stats["accuracy"] - expected_accuracy) < 0.01

    def test_edge_case_zero_keystrokes(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify stats calculation handles edge case of zero keystrokes.

        Expected: efficiency defaults to 100% when no keystrokes are recorded
        """
        # Setup: No keystrokes scenario
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 0
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        typing_drill.keystrokes = []  # No keystrokes

        stats = typing_drill._calculate_stats()

        # When no keystrokes, efficiency should default to 100%
        assert stats["efficiency"] == 100.0
        assert stats["total_keystrokes"] == 0
        assert stats["backspace_count"] == 0

    def test_edge_case_zero_expected_chars(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify stats calculation handles edge case of zero expected characters.

        Expected: correctness defaults to 100% when no characters are expected
        """
        # Setup: Zero expected characters scenario
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 0  # No expected characters
        typing_drill.session.actual_chars = 0
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        typing_drill.keystrokes = []

        stats = typing_drill._calculate_stats()

        # When no expected characters, correctness should default to 100%
        assert stats["correctness"] == 100.0
        assert stats["expected_chars"] == 0

    def test_edge_case_only_backspaces(self, typing_drill: TypingDrillScreen) -> None:
        """
        Test objective: Verify stats calculation handles edge case of only backspace keystrokes.

        Expected: efficiency defaults to 100% when all keystrokes are backspaces
        """
        # Setup: Only backspaces scenario
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = 10
        typing_drill.session.actual_chars = 0
        typing_drill.session.errors = 0
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)
        typing_drill.keystrokes = [{"is_backspace": True}] * 5  # Only backspaces

        stats = typing_drill._calculate_stats()

        # When only backspaces, efficiency should default to 100%
        assert stats["efficiency"] == 100.0
        assert stats["total_keystrokes"] == 5
        assert stats["backspace_count"] == 5

    @pytest.mark.parametrize(
        "expected_chars,keystrokes,backspaces,errors,expected_efficiency,expected_correctness",
        [
            # Perfect typing scenarios
            (5, 5, 0, 0, 100.0, 100.0),
            (10, 10, 0, 0, 100.0, 100.0),
            # With extra keystrokes
            (5, 8, 0, 0, 62.5, 100.0),
            (10, 15, 0, 0, 66.67, 100.0),
            # With backspaces
            (5, 7, 2, 0, 100.0, 100.0),  # 5 expected, 5 non-backspace keystrokes
            (10, 15, 5, 0, 100.0, 100.0),  # 10 expected, 10 non-backspace keystrokes
            # With errors
            (10, 10, 0, 2, 100.0, 80.0),
            (10, 10, 0, 5, 100.0, 50.0),
            # Combined scenarios
            (10, 15, 3, 2, 83.33, 80.0),  # 10 expected, 12 non-backspace, 8 correct
        ],
    )
    def test_stats_calculation_parametrized(
        self,
        typing_drill: TypingDrillScreen,
        expected_chars: int,
        keystrokes: int,
        backspaces: int,
        errors: int,
        expected_efficiency: float,
        expected_correctness: float,
    ) -> None:
        """
        Test objective: Verify stats calculations across multiple parameter combinations.

        This parametrized test covers various combinations of typing scenarios.
        """
        # Setup session data
        typing_drill.session.snippet_index_start = 0
        typing_drill.session.snippet_index_end = expected_chars
        typing_drill.session.actual_chars = expected_chars
        typing_drill.session.errors = errors
        typing_drill.session.start_time = datetime.datetime.now()
        typing_drill.session.end_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

        # Create keystroke data
        regular_keystrokes = [{"char": "x"}] * (keystrokes - backspaces)
        backspace_keystrokes = [{"is_backspace": True}] * backspaces
        typing_drill.keystrokes = regular_keystrokes + backspace_keystrokes

        stats = typing_drill._calculate_stats()

        # Calculate expected accuracy
        expected_accuracy = expected_efficiency * expected_correctness / 100.0

        # Verify calculations with tolerance for floating point precision
        assert abs(stats["efficiency"] - expected_efficiency) < 0.01
        assert abs(stats["correctness"] - expected_correctness) < 0.01
        assert abs(stats["accuracy"] - expected_accuracy) < 0.01
        assert stats["total_keystrokes"] == keystrokes
        assert stats["backspace_count"] == backspaces


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
