"""Direct debug script to identify failing test cases in test_session.py."""

import uuid
from datetime import datetime, timedelta

from models.session import Session

def run_debug():
    """Run debug tests directly to identify failing cases."""
    now = datetime.now()
    base_dict = {
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
    
    # Test cases from test_session_creation_and_calculated_fields
    test_cases = [
        ("Default fixture values", {}),
        ("Perfect score, short text", {"actual_chars": 5, "errors": 0}),
        ("All errors", {"actual_chars": 5, "errors": 5}),
        ("Zero actual_chars (abandoned)", {"actual_chars": 0, "errors": 0}),
        (
            "Short duration, high WPM/CPM",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0), 
                "end_time": datetime(2023, 1, 1, 12, 0, 1),
                "actual_chars": 5, 
                "errors": 0
            },
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
        ),
        (
            "Zero total_time (start_time == end_time)",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0), 
                "end_time": datetime(2023, 1, 1, 12, 0, 0),
                "actual_chars": 5, 
                "errors": 0
            },
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
        ),
        ("Snippet ID is None (should fail validation)", {"snippet_id": None}),
    ]
    
    print("\n=== RUNNING DEBUG TESTS ===\n")
    
    for idx, (case_name, overrides) in enumerate(test_cases):
        print(f"\n--- Test case {idx}: {case_name} ---")
        data = base_dict.copy()
        data.update(overrides)
        
        # Handle special content/index logic
        if "snippet_index_end" in overrides and "content" not in overrides:
            start_idx = overrides.get("snippet_index_start", data["snippet_index_start"])
            data["content"] = "a" * (overrides["snippet_index_end"] - start_idx)
        elif "content" in overrides and "snippet_index_start" in data and "snippet_index_end" in data:
            data["snippet_index_start"] = 0
            data["snippet_index_end"] = len(str(data["content"]))
        
        print(f"Input data: {data}")
        
        try:
            s = Session.from_dict(data)
            print(f"SUCCESS: Created Session object")
            print(f"Total time: {s.total_time}")
            print(f"Expected chars: {s.expected_chars}")
            print(f"Efficiency: {s.efficiency}")
            print(f"Correctness: {s.correctness}")
            print(f"Accuracy: {s.accuracy}")
            print(f"WPM: {s.session_wpm}")
            print(f"CPM: {s.session_cpm}")
        except Exception as e:
            print(f"FAILED with {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    run_debug()
