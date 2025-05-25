"""Temporary debug file to identify failing test cases."""

import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Type

import pytest
from pydantic import ValidationError

from models.session import Session

@pytest.fixture
def valid_session_dict_fixture() -> Dict[str, object]:
    now = datetime.now()
    return {
        "session_id": str(uuid.uuid4()),
        "snippet_id": 1, 
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "abcde",
        "start_time": now,
        "end_time": now + timedelta(seconds=60),
        "actual_chars": 5,
        "errors": 1,
    }

# Debug function to run each test case individually
def test_debug_cases(valid_session_dict_fixture: Dict[str, object]) -> None:
    """Debug test to identify which test cases are failing."""
    test_cases = [
        (
            "Default fixture values",
            {},
            None, None,
        ),
        (
            "Perfect score, short text",
            {"actual_chars": 5, "errors": 0},
            None, None,
        ),
        (
            "All errors",
            {"actual_chars": 5, "errors": 5},
            None, None,
        ),
        (
            "Zero actual_chars (abandoned)",
            {"actual_chars": 0, "errors": 0},
            ValidationError, 
            "errors cannot be less than expected_chars - actual_chars",
        ),
        (
            "Short duration, high WPM/CPM",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0), 
                "end_time": datetime(2023, 1, 1, 12, 0, 1),
                "actual_chars": 5, 
                "errors": 0
            },
            None, None,
        ),
        (
            "Long duration, low WPM/CPM, incomplete",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0), 
                "end_time": datetime(2023, 1, 1, 13, 0, 0),
                "snippet_index_start": 0, 
                "snippet_index_end": 100, 
                "content": "a" * 100,
                "actual_chars": 50, 
                "errors": 5
            },
            None, None,
        ),
        (
            "Zero total_time (start_time == end_time)",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0), 
                "end_time": datetime(2023, 1, 1, 12, 0, 0),
                "actual_chars": 5, 
                "errors": 0
            },
            None, None,
        ),
        (
            "Incomplete typing (actual_chars < expected_chars)",
            {
                "snippet_index_start": 0, 
                "snippet_index_end": 30, 
                "content": "a" * 30,
                "actual_chars": 20, 
                "errors": 2
            },
            None, None,
        ),
        (
            "Snippet ID is None (should fail validation)",
            {"snippet_id": None},
            ValidationError, 
            "Input should be a valid integer",
        ),
    ]
    
    for idx, (case_name, overrides, expected_exception_type, expected_exception_match) in enumerate(test_cases):
        print(f"\nTesting case {idx}: {case_name}")
        data = valid_session_dict_fixture.copy()
        data.update(overrides)

        if "snippet_index_end" in overrides and "content" not in overrides:
            start_idx = overrides.get("snippet_index_start", data["snippet_index_start"])
            data["content"] = "a" * (overrides["snippet_index_end"] - start_idx)
        elif "content" in overrides and ("snippet_index_start" in data and "snippet_index_end" in data):
            data["snippet_index_start"] = 0
            data["snippet_index_end"] = len(str(data["content"]))

        try:
            s = Session.from_dict(data)
            print(f"Case {idx} passed successfully")
            if expected_exception_type:
                print(f"ERROR: Expected {expected_exception_type.__name__} but no exception was raised")
        except Exception as e:
            print(f"Case {idx} failed with: {type(e).__name__}: {str(e)}")
            if expected_exception_type:
                if not isinstance(e, expected_exception_type):
                    print(f"ERROR: Expected {expected_exception_type.__name__} but got {type(e).__name__}")
                elif expected_exception_match and expected_exception_match not in str(e):
                    print(f"ERROR: Expected message '{expected_exception_match}' but got '{str(e)}'")
                else:
                    print(f"Case {idx} failed as expected with correct exception")
            else:
                print(f"ERROR: Expected success but got {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
