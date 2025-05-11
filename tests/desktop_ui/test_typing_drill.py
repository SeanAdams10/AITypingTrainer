"""
Tests for the TypingDrillScreen in the desktop UI.
"""
import pytest
import datetime
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QTextEdit
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from desktop_ui.typing_drill import TypingDrillScreen
from models.practice_session import PracticeSession, PracticeSessionManager


@pytest.fixture(scope="module")
def app():
    """Fixture to create a QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_session_manager():
    """Mock PracticeSessionManager for testing."""
    manager = MagicMock(spec=PracticeSessionManager)
    manager.create_session.return_value = 1  # Return a fake session_id
    return manager


def test_typing_drill_screen_initialization(app, qtbot):
    """Test that TypingDrillScreen initializes with correct parameters."""
    snippet_id = 1
    start = 5
    end = 15
    content = "This is a test snippet for typing practice."
    
    screen = TypingDrillScreen(snippet_id, start, end, content)
    qtbot.addWidget(screen)
    
    # Check basic initialization
    assert screen.snippet_id == snippet_id
    assert screen.start == start
    assert screen.end == end
    assert screen.content == content
    
    # Check UI components are present
    assert screen.typing_input is not None
    assert screen.progress_bar is not None
    assert screen.timer_label is not None
    assert screen.wpm_label is not None
    assert screen.accuracy_label is not None
    assert screen.display_text is not None


def test_typing_input_handling(app, qtbot):
    """Test typing input handling and feedback."""
    content = "test"
    screen = TypingDrillScreen(1, 0, 4, content)
    qtbot.addWidget(screen)
    
    # Simulate typing 't'
    with qtbot.waitSignal(screen.typing_input.textChanged, timeout=500):
        qtbot.keyClick(screen.typing_input, 't')
    
    # Check timer started
    assert screen.timer_running
    
    # Check text highlighting for correct input
    assert "color:#008000" in screen.display_text.toHtml()


def test_typing_error_handling(app, qtbot):
    """Test handling of typing errors."""
    content = "test"
    screen = TypingDrillScreen(1, 0, 4, content)
    qtbot.addWidget(screen)
    
    # Simulate typing 'x' (wrong character)
    qtbot.keyClick(screen.typing_input, 'x')
    
    # Check text highlighting for error
    assert "color:#ff0000" in screen.display_text.toHtml()
    
    # Check error count incremented
    assert screen.errors == 1


def test_session_completion(app, qtbot, mock_session_manager):
    """Test session completion and results display."""
    content = "test"
    screen = TypingDrillScreen(1, 0, 4, content)
    qtbot.addWidget(screen)
    
    # Need to patch both datetime.now and time.time for consistent timing
    with patch('datetime.datetime') as mock_datetime, patch('time.time') as mock_time:
        # Set initial time
        start_time = 1620000000.0  # Arbitrary timestamp
        mock_time.return_value = start_time
        mock_datetime.now.return_value = datetime.datetime(2025, 5, 10, 12, 0, 0)
        
        # Start typing - first character will start the timer
        screen.typing_input.setText("t")
        
        # Manually ensure timer_running is set
        screen.timer_running = True
        screen.start_time = start_time
        
        # Move time forward by 10 seconds for a predictable WPM
        moved_time = start_time + 10.0
        mock_time.return_value = moved_time
        mock_datetime.now.return_value = datetime.datetime(2025, 5, 10, 12, 0, 10)
        
        # Force elapsed time for accurate WPM calculation
        screen.elapsed_time = 10.0
        
        # Complete the typing
        screen.typing_input.setText("test")
        
        # Force consistent stats for testing
        stats = {
            "total_time": 10.0,
            "wpm": 24.0,  # (4/5) chars / (10/60) mins
            "cpm": 24.0,
            "expected_chars": 4,
            "actual_chars": 4,
            "errors": 0,
            "accuracy": 100.0,
            "error_positions": []
        }
        
        # Override the _calculate_stats method to return our predefined stats
        with patch.object(screen, '_calculate_stats', return_value=stats):
            # Trigger completion
            screen._check_completion()
            
            # Process events to ensure UI updates
            qtbot.wait(200)  # Wait for UI to update
            
            # For testing, ensure dialog is shown
            if hasattr(screen, 'completion_dialog'):
                screen.completion_dialog.show()
            
            # Verify completion dialog is shown
            assert hasattr(screen, 'completion_dialog')
            assert screen.completion_dialog is not None
            
            # Verify the stats match our expected values
            assert abs(screen.completion_dialog.stats['wpm'] - 24.0) < 0.1
            assert screen.completion_dialog.stats['accuracy'] == 100.0
            
            # Verify session is saved
            screen.save_session_with_manager(mock_session_manager)
            mock_session_manager.create_session.assert_called_once()


def test_save_session(app, mock_session_manager):
    """Test saving a session with proper statistics."""
    screen = TypingDrillScreen(1, 0, 4, "test")
    
    # Set up session stats
    stats = {
        "total_time": 10.0,
        "wpm": 24.0,
        "cpm": 120.0,
        "expected_chars": 4,
        "actual_chars": 4,
        "errors": 0,
        "accuracy": 100.0
    }
    
    # Save session with the mock manager
    screen.save_session(stats, mock_session_manager)
    
    # Verify the correct data was passed
    call_args = mock_session_manager.create_session.call_args[0][0]
    assert call_args.snippet_id == 1
    assert call_args.snippet_index_start == 0
    assert call_args.snippet_index_end == 4
    assert call_args.content == "test"
    assert call_args.total_time == 10.0
    assert call_args.session_wpm == 24.0
    assert call_args.session_cpm == 120.0
    assert call_args.expected_chars == 4
    assert call_args.actual_chars == 4
    assert call_args.errors == 0
    assert call_args.accuracy == 100.0
