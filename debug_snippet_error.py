"""
Improved debug script for test_snippet.py with proper cleanup
"""
import sys
import tempfile
import traceback
from pathlib import Path
import sqlite3

from db.database_manager import DatabaseManager
from models.snippet_manager import SnippetManager
from db.exceptions import IntegrityError, ForeignKeyError, DatabaseError

def main():
    """Run a manual test to reproduce the error in test_create_snippet_with_nonexistent_category"""
    print("Setting up test environment...")
    
    # Use tempfile module for better cleanup
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_db.sqlite3"
        
        try:
            # Initialize the database
            db = DatabaseManager(str(db_path))
            db.init_tables()
            
            # Create snippet manager
            snippet_manager = SnippetManager(db)
            
            # Try to create a snippet with non-existent category
            print("\nAttempting to create snippet with non-existent category...")
            try:
                snippet_manager.create_snippet(
                    category_id=999,  # Non-existent category
                    snippet_name="OrphanSnippet",
                    content="Content",
                )
                print("ERROR: This should have raised an exception!")
            except Exception as e:
                print(f"\nGot exception (expected): {type(e).__name__}: {e}")
                print(f"Is IntegrityError? {isinstance(e, IntegrityError)}")
                print(f"Is ForeignKeyError? {isinstance(e, ForeignKeyError)}")
                print(f"Exception hierarchy: {e.__class__.__mro__}")
                print("\nTraceback:")
                traceback.print_exc()
                
            # Close the database connection explicitly
            db.close()
            
        except Exception as e:
            print(f"Setup error: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()
