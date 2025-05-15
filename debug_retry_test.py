"""
Debug script for the test_two_sessions_saved_on_retry test.
This will help us identify exactly what's failing.
"""
import sys
import os
import datetime
from unittest.mock import MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from desktop_ui.typing_drill import TypingDrillScreen
from models.practice_session import PracticeSession, PracticeSessionManager

def debug_test():
    print("Starting debug test for test_two_sessions_saved_on_retry")
    
    # Create a mock session manager
    mock_session_manager = MagicMock(spec=PracticeSessionManager)
    mock_session_manager.create_session.return_value = 1  # Return session ID 1
    
    # Create a screen with test parameters
    print("Creating TypingDrillScreen")
    screen = TypingDrillScreen(snippet_id=1, start=0, end=4, content="test")
    
    # Simulate first completion (perfect score)
    print("Simulating first session completion")
    stats1 = {
        "total_time": 10.0,
        "wpm": 24.0,
        "cpm": 120.0,
        "expected_chars": 4,
        "actual_chars": 4,
        "correct_chars": 4,
        "errors": 0,
        "accuracy": 100.0,
        "efficiency": 100.0,
        "correctness": 100.0,
        "total_keystrokes": 4,
        "backspace_count": 0
    }
    
    try:
        print("Saving first session")
        first_session_id = screen.save_session(stats1, mock_session_manager)
        print(f"First session saved with ID: {first_session_id}")
        
        # Get first session details
        first_session = mock_session_manager.create_session.call_args[0][0]
        print(f"First session accuracy: {first_session.accuracy}")
        print(f"First session efficiency: {first_session.efficiency}")
        print(f"First session correctness: {first_session.correctness}")
        
        # Simulate user clicking retry button
        print("Resetting session for retry")
        screen._reset_session()
        
        # Verify reset state
        print(f"After reset - typed_chars: {screen.typed_chars}")
        print(f"After reset - errors: {screen.errors}")
        print(f"After reset - keystrokes count: {len(screen.keystrokes)}")
        
        # Simulate second completion (with an error)
        print("Simulating second session completion")
        stats2 = {
            "total_time": 12.0,
            "wpm": 30.0,
            "cpm": 150.0,
            "expected_chars": 4,
            "actual_chars": 4,
            "errors": 1,
            "accuracy": 75.0,
            "efficiency": 95.0,
            "correctness": 80.0,
            "total_keystrokes": 5,  # Added for completeness
            "backspace_count": 0
        }
        
        print("Saving second session")
        second_session_id = screen.save_session(stats2, mock_session_manager)
        print(f"Second session saved with ID: {second_session_id}")
        
        # Get second session details
        second_session = mock_session_manager.create_session.call_args[0][0]
        print(f"Second session accuracy: {second_session.accuracy}")
        print(f"Second session efficiency: {second_session.efficiency}")
        print(f"Second session correctness: {second_session.correctness}")
        print(f"Second session errors: {second_session.errors}")
        print(f"Second session WPM: {second_session.session_wpm}")
        
        # Verify call count
        print(f"create_session call count: {mock_session_manager.create_session.call_count}")
        
        # Verify assertions
        assert second_session.accuracy == 75.0, "Second session should have 75% accuracy"
        assert second_session.errors == 1, "Second session should have 1 error"
        assert second_session.session_wpm == 30.0, "Second session should have WPM of 30"
        # Efficiency and correctness are converted from percentages to decimals
        assert second_session.efficiency == 0.95, "Second session should have efficiency of 0.95 (95%)"
        assert second_session.correctness == 0.80, "Second session should have correctness of 0.8 (80%)"
        assert mock_session_manager.create_session.call_count == 2, "Two distinct sessions should be saved"
        
        print("All assertions passed!")
        
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    debug_test()
