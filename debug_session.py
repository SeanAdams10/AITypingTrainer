#!/usr/bin/env python
"""
Debug script to understand validation errors with PracticeSession model.
"""
import os
import sys
import datetime
from typing import Dict, Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.practice_session import PracticeSession

# Create session data similar to the test case
session_data = {
    "snippet_id": 1,
    "snippet_index_start": 0,
    "snippet_index_end": 10,
    "content": "The quick brown fox",
    "start_time": datetime.datetime.now(),
    "end_time": datetime.datetime.now(),
    "total_time": 30,
    "session_wpm": 60.0,
    "session_cpm": 300.0,
    "expected_chars": 19,
    "actual_chars": 19,
    "errors": 0,
    "efficiency": 1.0,
    "correctness": 1.0,
    "accuracy": 1.0,
}

try:
    # Create the session
    session = PracticeSession(
        session_id=None,
        **session_data
    )
    print("Successfully created PracticeSession instance:")
    print(f"session_id: {session.session_id}")
    print(f"snippet_id: {session.snippet_id}")
    print(f"efficiency: {session.efficiency}")
    print(f"correctness: {session.correctness}")
    print(f"accuracy: {session.accuracy}")
except Exception as e:
    print(f"Error creating PracticeSession: {e}")
    print(f"Session data: {session_data}")
