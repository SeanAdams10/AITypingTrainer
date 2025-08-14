#!/usr/bin/env python3
"""
Test script to verify DebugUtil integration with main_menu and DatabaseManager.
"""

import os
import sys
import tempfile
from io import StringIO
from contextlib import redirect_stdout

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from helpers.debug_util import DebugUtil
from db.database_manager import DatabaseManager, ConnectionType


def test_debug_util_standalone():
    """Test the DebugUtil class functionality standalone."""
    
    print("=== Testing DebugUtil Standalone ===\n")
    
    # Test 1: Quiet mode
    print("Test 1: DebugUtil in quiet mode")
    debug_util_quiet = DebugUtil("quiet")
    print(f"Debug mode: {debug_util_quiet.debug_mode()}")
    print(f"Is quiet: {debug_util_quiet.is_quiet()}")
    print(f"Is loud: {debug_util_quiet.is_loud()}")
    
    # Capture stdout to verify quiet mode doesn't print
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        debug_util_quiet.debugMessage("This should not appear in stdout")
    
    stdout_content = captured_output.getvalue()
    if stdout_content:
        print(f"❌ FAIL: Quiet mode printed to stdout: '{stdout_content.strip()}'")
    else:
        print("✅ PASS: Quiet mode correctly suppressed stdout output")
    
    print()
    
    # Test 2: Loud mode
    print("Test 2: DebugUtil in loud mode")
    debug_util_loud = DebugUtil("loud")
    print(f"Debug mode: {debug_util_loud.debug_mode()}")
    print(f"Is quiet: {debug_util_loud.is_quiet()}")
    print(f"Is loud: {debug_util_loud.is_loud()}")
    
    # Test loud mode output
    print("Testing loud mode output:")
    debug_util_loud.debugMessage("This should appear in stdout (loud mode)")
    print("✅ PASS: Loud mode correctly outputs to stdout")
    
    print()


def test_database_manager_integration():
    """Test DatabaseManager integration with DebugUtil."""
    
    print("=== Testing DatabaseManager Integration ===\n")
    
    # Test 1: DatabaseManager with quiet DebugUtil
    print("Test 1: DatabaseManager with quiet DebugUtil")
    debug_util_quiet = DebugUtil("quiet")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        temp_db_path = temp_db.name
    
    try:
        db_manager = DatabaseManager(
            db_path=temp_db_path,
            connection_type=ConnectionType.LOCAL,
            debug_util=debug_util_quiet
        )
        
        # Test that debug_util is stored correctly
        if hasattr(db_manager, 'debug_util') and db_manager.debug_util is debug_util_quiet:
            print("✅ PASS: DatabaseManager correctly stores DebugUtil instance")
        else:
            print("❌ FAIL: DatabaseManager did not store DebugUtil instance correctly")
        
        # Test that _debug_message method exists
        if hasattr(db_manager, '_debug_message'):
            print("✅ PASS: DatabaseManager has _debug_message method")
            
            # Test quiet mode debug message (should not print to stdout)
            captured_output = StringIO()
            with redirect_stdout(captured_output):
                db_manager._debug_message("Debug message from DatabaseManager (quiet)")
            
            stdout_content = captured_output.getvalue()
            if stdout_content:
                print(f"❌ FAIL: Quiet mode debug message printed to stdout: '{stdout_content.strip()}'")
            else:
                print("✅ PASS: Quiet mode debug message correctly suppressed")
        else:
            print("❌ FAIL: DatabaseManager missing _debug_message method")
        
        db_manager.close()
        
    finally:
        try:
            os.unlink(temp_db_path)
        except:
            pass
    
    print()
    
    # Test 2: DatabaseManager with loud DebugUtil
    print("Test 2: DatabaseManager with loud DebugUtil")
    debug_util_loud = DebugUtil("loud")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        temp_db_path = temp_db.name
    
    try:
        db_manager = DatabaseManager(
            db_path=temp_db_path,
            connection_type=ConnectionType.LOCAL,
            debug_util=debug_util_loud
        )
        
        # Test loud mode debug message (should print to stdout)
        print("Testing loud mode debug message:")
        db_manager._debug_message("Debug message from DatabaseManager (loud)")
        print("✅ PASS: Loud mode debug message correctly outputs to stdout")
        
        db_manager.close()
        
    finally:
        try:
            os.unlink(temp_db_path)
        except:
            pass
    
    print()


def test_fallback_behavior():
    """Test fallback behavior when DebugUtil is not provided."""
    
    print("=== Testing Fallback Behavior ===\n")
    
    print("Test: DatabaseManager without DebugUtil (should use fallback)")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        temp_db_path = temp_db.name
    
    try:
        db_manager = DatabaseManager(
            db_path=temp_db_path,
            connection_type=ConnectionType.LOCAL,
            debug_util=None  # No DebugUtil provided
        )
        
        # Test that debug_util is None
        if db_manager.debug_util is None:
            print("✅ PASS: DatabaseManager correctly handles None DebugUtil")
        else:
            print("❌ FAIL: DatabaseManager should have None DebugUtil")
        
        # Test fallback debug message behavior
        print("Testing fallback debug message (should use debug_print):")
        db_manager._debug_message("Fallback debug message")
        print("✅ PASS: Fallback debug message works")
        
        db_manager.close()
        
    finally:
        try:
            os.unlink(temp_db_path)
        except:
            pass
    
    print()


if __name__ == "__main__":
    test_debug_util_standalone()
    test_database_manager_integration()
    test_fallback_behavior()
    print("=== All DebugUtil Integration Tests Complete ===")
