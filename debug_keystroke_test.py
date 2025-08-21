#!/usr/bin/env python3
"""Debug script to identify keystroke manager test failures."""

import sys
import traceback
from unittest.mock import Mock
from datetime import datetime, timezone
import uuid

# Add current directory to path
sys.path.insert(0, '.')

try:
    from models.keystroke_manager import KeystrokeManager
    from models.keystroke import Keystroke
    from db.database_manager import DatabaseManager
    
    print("✓ Imports successful")
    
    # Test 1: Basic KeystrokeManager creation
    manager = KeystrokeManager(db_manager=Mock(spec=DatabaseManager))
    print("✓ KeystrokeManager creation with mock DB successful")
    
    # Test 2: Create sample keystroke
    keystroke = Keystroke(
        session_id="test-session",
        keystroke_id=str(uuid.uuid4()),
        keystroke_time=datetime.now(timezone.utc),
        keystroke_char="a",
        expected_char="a",
        is_error=False,
        time_since_previous=100
    )
    print("✓ Keystroke creation successful")
    
    # Test 3: Add keystroke to manager
    manager.add_keystroke(keystroke)
    print(f"✓ Add keystroke successful, list length: {len(manager.keystroke_list)}")
    
    # Test 4: Test save_keystrokes with mock
    result = manager.save_keystrokes()
    print(f"✓ save_keystrokes returned: {result}")
    print(f"✓ Mock execute call count: {manager.db_manager.execute.call_count}")
    
    # Test 5: Check what SQL was called
    if manager.db_manager.execute.call_args_list:
        call_args = manager.db_manager.execute.call_args_list[0]
        sql, params = call_args[0]
        print(f"✓ SQL called: {sql}")
        print(f"✓ Params: {params}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()
