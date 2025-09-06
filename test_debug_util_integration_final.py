#!/usr/bin/env python3
"""Quick test script to verify DebugUtil integration with DatabaseManager."""

import os
import sys

# Add project root to path
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import DatabaseManager
from helpers.debug_util import DebugUtil


def test_debug_util_integration():
    """Test that DatabaseManager properly requires DebugUtil."""
    print("Testing DebugUtil integration with DatabaseManager...")
    
    # Test 1: Creating DatabaseManager without DebugUtil should raise exception
    try:
        db = DatabaseManager(":memory:")
        print("ERROR: Expected MissingDebugUtilError but got none!")
        return False
    except Exception as e:
        if "MissingDebugUtilError" in str(type(e)):
            print("✓ Correctly raised MissingDebugUtilError when no DebugUtil provided")
        else:
            print(f"ERROR: Expected MissingDebugUtilError but got: {type(e).__name__}: {e}")
            return False
    
    # Test 2: Creating DatabaseManager with DebugUtil should work
    try:
        debug_util = DebugUtil()
        debug_util._mode = "loud"
        db = DatabaseManager(":memory:", debug_util=debug_util)
        print("✓ Successfully created DatabaseManager with DebugUtil")
        db.close()
    except Exception as e:
        print(f"ERROR: Failed to create DatabaseManager with DebugUtil: {type(e).__name__}: {e}")
        return False
    
    print("All tests passed!")
    return True

if __name__ == "__main__":
    success = test_debug_util_integration()
    sys.exit(0 if success else 1)
