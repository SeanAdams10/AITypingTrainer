import uuid
from datetime import datetime

from models.session import Session

# Create a session object with the same parameters as the test case
session = Session(
    session_id=str(uuid.uuid4()),
    snippet_id=str(uuid.uuid4()),
    snippet_index_start=0,
    snippet_index_end=100,
    content="a" * 100,
    start_time=datetime(2023, 1, 1, 12, 0, 0),
    end_time=datetime(2023, 1, 1, 13, 0, 0),
    actual_chars=50,
    errors=5,
)

# Print each property to debug
print(f"expected_chars: {session.expected_chars}")
print(f"actual_chars: {session.actual_chars}")
print(f"errors: {session.errors}")
print(f"correctness calc: ({session.actual_chars} - {session.errors}) / {session.actual_chars}")
print(f"correctness: {session.correctness}")
print(f"efficiency: {session.efficiency}")
print(f"accuracy: {session.accuracy}")
print(f"total_time: {session.total_time}")
print(f"session_cpm: {session.session_cpm}")
print(f"session_wpm: {session.session_wpm}")
