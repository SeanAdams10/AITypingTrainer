from models.session import Session
import uuid
from datetime import datetime

# Create a session with a None snippet_id
try:
    d = {
        "session_id": str(uuid.uuid4()),
        "snippet_id": None,
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "abcde",
        "start_time": datetime.now(),
        "end_time": datetime.now(),
        "actual_chars": 5,
        "errors": 1,
    }
    
    print("Attempting to create a Session with snippet_id=None")
    session = Session.from_dict(d)
    print("SUCCESS - This shouldn't happen! Session created:", session)
except Exception as e:
    print(f"EXCEPTION (Expected): {type(e).__name__}: {str(e)}")
