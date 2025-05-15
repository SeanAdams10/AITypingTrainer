import datetime
from models.practice_session import PracticeSession

# Minimal test case to debug PracticeSession validation error
try:
    # Create a session with all required fields
    session = PracticeSession(
        session_id=None,
        snippet_id=1,
        snippet_index_start=0,
        snippet_index_end=10,
        content="The quick brown fox",
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now(),
        total_time=30.0,
        session_wpm=60.0,
        session_cpm=300.0,
        expected_chars=19,
        actual_chars=19,
        errors=0,
        efficiency=1.0,
        correctness=1.0,
        accuracy=1.0,
    )
    print("Successfully created PracticeSession object!")
    print(f"Session attributes: {session}")
except Exception as e:
    print(f"Validation error: {str(e)}")
    import traceback
    print(traceback.format_exc())
