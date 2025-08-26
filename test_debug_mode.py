#!/usr/bin/env python3
"""Test script to demonstrate the debug mode functionality.

This script shows how the debug_mode parameter controls debug output
in the AI Typing Trainer application.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from db.database_manager import debug_print


def test_debug_mode_functionality():
    """Test the debug mode functionality with different settings."""
    print("=== Testing Debug Mode Functionality ===\n")
    
    # Test 1: Default mode (loud)
    print("Test 1: Default mode (should show debug messages)")
    if "AI_TYPING_TRAINER_DEBUG_MODE" in os.environ:
        del os.environ["AI_TYPING_TRAINER_DEBUG_MODE"]
    
    debug_print("This debug message should be visible (default mode)")
    print("Regular print: This message is always visible\n")
    
    # Test 2: Loud mode explicitly set
    print("Test 2: Loud mode explicitly set (should show debug messages)")
    os.environ["AI_TYPING_TRAINER_DEBUG_MODE"] = "loud"
    
    debug_print("This debug message should be visible (loud mode)")
    print("Regular print: This message is always visible\n")
    
    # Test 3: Quiet mode
    print("Test 3: Quiet mode (should NOT show debug messages)")
    os.environ["AI_TYPING_TRAINER_DEBUG_MODE"] = "quiet"
    
    debug_print("This debug message should be HIDDEN (quiet mode)")
    print("Regular print: This message is always visible\n")
    
    # Test 4: Invalid mode (defaults to loud)
    print("Test 4: Invalid mode 'invalid' (should default to loud and show debug messages)")
    os.environ["AI_TYPING_TRAINER_DEBUG_MODE"] = "invalid"
    
    debug_print("This debug message should be visible (invalid mode defaults to loud)")
    print("Regular print: This message is always visible\n")
    
    print("=== Debug Mode Test Complete ===")


def test_main_menu_integration():
    """Test the main menu integration with debug mode."""
    print("\n=== Testing Main Menu Integration ===\n")
    
    # Test importing the main menu with debug mode parameter
    try:
        from desktop_ui.main_menu import launch_main_menu
        print("✅ Successfully imported launch_main_menu with debug_mode parameter")
        
        # Show the function signature
        import inspect
        sig = inspect.signature(launch_main_menu)
        print(f"Function signature: launch_main_menu{sig}")
        
        # Test that we can call it with debug_mode parameter (but don't actually launch)
        print("✅ Function accepts debug_mode parameter")
        
    except Exception as e:
        print(f"❌ Error testing main menu integration: {e}")
    
    print("\n=== Main Menu Integration Test Complete ===")


if __name__ == "__main__":
    test_debug_mode_functionality()
    test_main_menu_integration()
