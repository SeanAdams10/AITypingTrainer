"""
Debug script to identify validation errors in PracticeSession.
Run this script directly to see detailed error messages.
"""
import sys
import datetime
from models.practice_session import PracticeSession, PracticeSessionManager
from db.database_manager import DatabaseManager
import tempfile
import os

def main():
    # Create a temporary DB for testing
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    print(f"Creating temp database at: {path}")
    db = DatabaseManager(path)
    db.init_tables()
    
    # Set up basic test data
    db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (1, "Test Category"),
        commit=True
    )
    db.execute(
        "INSERT INTO snippets (snippet_name, category_id) VALUES (?, ?)",
        ("Test Snippet", 1),
        commit=True
    )
    db.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (1, 0, "abc"),
        commit=True
    )
    
    try:
        # Create practice session with all required fields
        print("\nCreating PracticeSession object...")
        session = PracticeSession(
            session_id=None,
            snippet_id=1,
            snippet_index_start=0,
            snippet_index_end=3,
            content="abc",
            start_time=datetime.datetime.now(),
            end_time=datetime.datetime.now(),
            total_time=5.0,
            session_wpm=30.0,
            session_cpm=150.0,
            expected_chars=3,
            actual_chars=3,
            errors=0,
            efficiency=1.0,
            correctness=1.0,
            accuracy=1.0,
        )
        print(f"PracticeSession created successfully: {session}")
        
        # Now try to save it to the database
        print("\nSaving PracticeSession to database...")
        session_manager = PracticeSessionManager(db)
        session_id = session_manager.create_session(session)
        print(f"Session saved with ID: {session_id}")
        
        # Try to retrieve it
        print("\nRetrieving session...")
        retrieved = session_manager.get_last_session_for_snippet(1)
        print(f"Retrieved session: {retrieved}")
        
        # Clean up
        os.unlink(path)
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        
        # Try to clean up even on error
        try:
            os.unlink(path)
        except:
            pass

if __name__ == "__main__":
    main()
