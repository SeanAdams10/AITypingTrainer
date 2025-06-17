"""
Temporary debug test for the session creation tests.
"""

from datetime import datetime

from pydantic import ValidationError

from models.session import Session


def test_debug_all_failing_cases() -> None:
    """Test the specific failing test cases from test_session_creation_and_calculated_fields."""
    test_cases = [
        # Case 1: Long duration, low WPM/CPM, incomplete
        {
            "name": "Long duration, low WPM/CPM, incomplete",
            "data": {
                "session_id": "244a4556-1234-5678-abcd-1234567890ab",
                "snippet_id": 1,
                "snippet_index_start": 0,
                "snippet_index_end": 100,
                "content": "a" * 100,
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 13, 0, 0),
                "actual_chars": 50,
                "errors": 50  # errors >= expected_chars - actual_chars (100 - 50 = 50)
            },
            "expected": {
                "expected_chars": 100, 
                "total_time": 3600.0, 
                "efficiency": 0.5, 
                "correctness": 0.0,  # (actual_chars - errors) / actual_chars = (50 - 50) / 50 = 0
                "accuracy": 0.0,     # correctness * efficiency = 0.0 * 0.5 = 0.0
                "session_cpm": 50.0 / 60.0, 
                "session_wpm": (50.0 / 5) / 60.0
            }
        },
        # Case 2: Zero actual_chars (abandoned)
        {
            "name": "Zero actual_chars (abandoned)",
            "data": {
                "session_id": "244a4556-1234-5678-abcd-1234567890ab",
                "snippet_id": 1,
                "snippet_index_start": 0,
                "snippet_index_end": 5,
                "content": "abcde",
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 12, 1, 0),
                "actual_chars": 0,
                "errors": 5  # errors >= expected_chars - actual_chars (5 - 0 = 5)
            },
            "expected": None  # This should raise a ValidationError
        },
        # Case 3: Incomplete typing
        {
            "name": "Incomplete typing (actual_chars < expected_chars)",
            "data": {
                "session_id": "244a4556-1234-5678-abcd-1234567890ab",
                "snippet_id": 1,
                "snippet_index_start": 0,
                "snippet_index_end": 30,
                "content": "a" * 30,
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 12, 1, 0),
                "actual_chars": 20,
                "errors": 10  # errors >= expected_chars - actual_chars (30 - 20 = 10)
            },
            "expected": {
                "expected_chars": 30, 
                "total_time": 60.0, 
                "efficiency": 20.0 / 30.0, 
                "correctness": 10.0 / 20.0, 
                "accuracy": (10.0 / 20.0) * (20.0 / 30.0), 
                "session_cpm": 20.0, 
                "session_wpm": 4.0
            }
        }
    ]
    
    for case in test_cases:
        print(f"\n\nTesting case: {case['name']}")
        try:
            if case['expected'] is None:
                try:
                    s = Session.from_dict(case['data'])
                    print("UNEXPECTED SUCCESS: Should have raised ValidationError")
                    print(f"Session: {s}")
                except ValidationError as e:
                    print(f"SUCCESS: Validation error as expected: {e}")
            else:
                s = Session.from_dict(case['data'])
                print("Session created successfully")
                print(f"expected_chars - Expected: {case['expected']['expected_chars']}, Actual: {s.expected_chars}")
                print(f"total_time - Expected: {case['expected']['total_time']}, Actual: {s.total_time}")
                print(f"efficiency - Expected: {case['expected']['efficiency']}, Actual: {s.efficiency}")
                print(f"correctness - Expected: {case['expected']['correctness']}, Actual: {s.correctness}")
                print(f"accuracy - Expected: {case['expected']['accuracy']}, Actual: {s.accuracy}")
                print(f"session_cpm - Expected: {case['expected']['session_cpm']}, Actual: {s.session_cpm}")
                print(f"session_wpm - Expected: {case['expected']['session_wpm']}, Actual: {s.session_wpm}")
        except Exception as e:
            print(f"ERROR: Unexpected exception: {e}")
            print(f"Data: {case['data']}")

