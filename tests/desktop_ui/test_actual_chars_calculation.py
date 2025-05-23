"""
Test objective: Verify that actual_chars is correctly calculated as the count of keystrokes excluding backspace keystrokes.

This test directly tests the _calculate_stats method to ensure it correctly calculates actual_chars
according to the requirements.
"""
import os
import sys
import unittest
from datetime import datetime
from typing import Any, Dict

from PyQt5.QtWidgets import QApplication

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import relevant classes/functions for testing
from desktop_ui.typing_drill import TypingDrillScreen


class TestActualCharsCalculation(unittest.TestCase):
    """Test that actual_chars is correctly calculated as the count of keystrokes excluding backspace keystrokes."""
    
    @classmethod
    def setUpClass(cls):
        # Create QApplication instance before any tests
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication([])
    
    def test_calculate_stats_actual_chars(self):
        """Test objective: Verify actual_chars calculation in _calculate_stats method.
        
        This test checks that:
        1. For a simple backspace correction, actual_chars counts all non-backspace keystrokes
        2. With multiple backspaces, actual_chars is calculated correctly
        3. With consecutive backspaces, actual_chars remains correctly calculated
        """
        # Create a TypingDrillScreen instance for testing
        drill = TypingDrillScreen(
            snippet_id=-1,
            start=0,
            end=0,
            content="The",
            db_manager=None  # No need for DB connection in this test
        )
        
        # Test Case 1: T-g-backspace-h-e
        # Expected actual_chars = 4 (T, g, h, e - excluding backspace)
        drill.keystrokes = [
            self._create_keystroke(0, 'T', is_backspace=False, is_error=False),
            self._create_keystroke(1, 'g', is_backspace=False, is_error=True),
            self._create_keystroke(1, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(1, 'h', is_backspace=False, is_error=False),
            self._create_keystroke(2, 'e', is_backspace=False, is_error=False)
        ]
        
        # Set typed_chars to match the current text length (this would be "The")
        drill.typed_chars = 3
        
        # Calculate stats and check actual_chars
        stats = drill._calculate_stats()
        self.assertEqual(stats["actual_chars"], 4, 
                        "actual_chars should be 4 (T, g, h, e - excluding backspace)")
        self.assertEqual(stats["backspace_count"], 1, 
                        "backspace_count should be 1")
        
        # Test Case 2: T-backspace-T-backspace-T-h-backspace-h-d
        # Expected actual_chars = 6 (T, T, T, h, h, d - excluding backspaces)
        drill.keystrokes = [
            self._create_keystroke(0, 'T', is_backspace=False, is_error=False),
            self._create_keystroke(0, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(0, 'T', is_backspace=False, is_error=False),
            self._create_keystroke(0, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(0, 'T', is_backspace=False, is_error=False),
            self._create_keystroke(1, 'h', is_backspace=False, is_error=False),
            self._create_keystroke(1, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(1, 'h', is_backspace=False, is_error=False),
            self._create_keystroke(2, 'd', is_backspace=False, is_error=True)
        ]
        
        # Set typed_chars to match the current text length (this would be "Thd")
        drill.typed_chars = 3
        
        # Calculate stats and check actual_chars
        stats = drill._calculate_stats()
        self.assertEqual(stats["actual_chars"], 6, 
                        "actual_chars should be 6 (T, T, T, h, h, d - excluding backspaces)")
        self.assertEqual(stats["backspace_count"], 3, 
                        "backspace_count should be 3")
        
        # Test Case 3: Multiple consecutive backspaces
        drill.content = "test"
        drill.keystrokes = [
            self._create_keystroke(0, 't', is_backspace=False, is_error=False),
            self._create_keystroke(1, 'e', is_backspace=False, is_error=False),
            self._create_keystroke(2, 's', is_backspace=False, is_error=False),
            self._create_keystroke(3, 't', is_backspace=False, is_error=False),
            self._create_keystroke(3, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(2, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(1, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(0, '\b', is_backspace=True, is_error=True),
            self._create_keystroke(0, 't', is_backspace=False, is_error=False),
            self._create_keystroke(1, 'e', is_backspace=False, is_error=False),
            self._create_keystroke(2, 's', is_backspace=False, is_error=False),
            self._create_keystroke(3, 't', is_backspace=False, is_error=False)
        ]
        
        # Set typed_chars to match the current text length (this would be "test")
        drill.typed_chars = 4
        
        # Calculate stats and check actual_chars
        stats = drill._calculate_stats()
        self.assertEqual(stats["actual_chars"], 8, 
                        "actual_chars should be 8 (t, e, s, t, t, e, s, t - excluding backspaces)")
        self.assertEqual(stats["backspace_count"], 4, 
                        "backspace_count should be 4")
    
    def _create_keystroke(self, position: int, char: str, is_backspace: bool = False, 
                          is_error: bool = False) -> Dict[str, Any]:
        """Helper method to create a keystroke record for testing.
        
        Args:
            position: Character position
            char: The character typed
            is_backspace: Whether this is a backspace keystroke
            is_error: Whether this is an error
            
        Returns:
            A keystroke record dict
        """
        return {
            'char_position': position,
            'char_typed': char,
            'expected_char': 'x',  # Dummy value for testing
            'timestamp': datetime.now(),
            'is_error': 1 if is_error else 0,
            'is_backspace': is_backspace
        }


if __name__ == "__main__":
    unittest.main()
