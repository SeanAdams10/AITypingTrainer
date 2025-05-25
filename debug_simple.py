"""
Simple debug script for test_snippet.py
"""
import sys
from pathlib import Path
import pytest
from models.snippet_manager import SnippetManager
from db.database_manager import DatabaseManager
from db.exceptions import IntegrityError, ForeignKeyError

def main():
    """Run a manual test to reproduce the error in test_create_snippet_with_nonexistent_category"""
    print("Setting up test environment...")
    # Create a temp DB
    tmp_path = Path("./temp_test")
    tmp_path.mkdir(exist_ok=True)
    db_file = tmp_path / "test_db.sqlite3"
    
    try:
        # Initialize the database
        db = DatabaseManager(str(db_file))
        db.init_tables()
        
        # Create snippet manager
        snippet_manager = SnippetManager(db)
        
        # Try to create a snippet with non-existent category
        print("Attempting to create snippet with non-existent category...")
        try:
            snippet_manager.create_snippet(
                category_id=999,  # Non-existent category
                snippet_name="OrphanSnippet",
                content="Content",
            )
            print("ERROR: This should have raised an exception!")
        except Exception as e:
            print(f"Got exception (expected): {type(e).__name__}: {e}")
            print(f"Is IntegrityError? {isinstance(e, IntegrityError)}")
            print(f"Is ForeignKeyError? {isinstance(e, ForeignKeyError)}")
            
    finally:
        # Clean up
        if db_file.exists():
            db_file.unlink()
        tmp_path.rmdir()

if __name__ == "__main__":
    main()
