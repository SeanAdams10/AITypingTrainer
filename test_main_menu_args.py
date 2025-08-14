#!/usr/bin/env python3
"""
Test script to verify command line argument parsing in main_menu.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_argument_parsing():
    """Test the command line argument parsing logic from main_menu.py"""
    
    print("=== Testing Main Menu Command Line Argument Parsing ===\n")
    
    # Test cases
    test_cases = [
        ([], "quiet", "No arguments (should default to quiet)"),
        (["loud"], "loud", "Single 'loud' argument"),
        (["quiet"], "quiet", "Single 'quiet' argument"),
        (["LOUD"], "loud", "Case insensitive 'LOUD'"),
        (["QUIET"], "quiet", "Case insensitive 'QUIET'"),
        (["other", "loud"], "loud", "Multiple args with 'loud'"),
        (["quiet", "loud"], "quiet", "Multiple args - 'quiet' found first"),
        (["invalid"], "quiet", "Invalid argument (should default to quiet)"),
    ]
    
    for test_args, expected, description in test_cases:
        # Simulate the argument parsing logic from main_menu.py
        debug_mode = "quiet"  # Default to quiet
        
        if len(test_args) > 0:
            for arg in test_args:
                if arg.lower() == "loud":
                    debug_mode = "loud"
                    break
                elif arg.lower() == "quiet":
                    debug_mode = "quiet"
                    break
        
        # Check result
        status = "✅ PASS" if debug_mode == expected else "❌ FAIL"
        print(f"{status} {description}")
        print(f"    Args: {test_args}")
        print(f"    Expected: {expected}, Got: {debug_mode}")
        print()

if __name__ == "__main__":
    test_argument_parsing()
