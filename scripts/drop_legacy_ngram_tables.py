"""
Script to remove legacy bigram and trigram tables from the database.
This supports the n-gram analysis refactoring to use a generic approach.
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database_manager import DatabaseManager

def drop_legacy_tables():
    """
    Drop the legacy bigram and trigram tables that are no longer needed
    after moving to the generic n-gram approach.
    """
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Tables to drop
    legacy_tables = [
        'session_bigram_speed',
        'session_trigram_speed',
        'session_bigram_error',
        'session_trigram_error'
    ]
    
    for table in legacy_tables:
        # Check if table exists before dropping
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if cursor.fetchone():
            print(f"Dropping table: {table}")
            cursor.execute(f"DROP TABLE {table}")
        else:
            print(f"Table {table} does not exist, skipping")
    
    # Commit the changes
    conn.commit()
    conn.close()
    
    print("Legacy tables cleanup completed successfully.")

if __name__ == "__main__":
    drop_legacy_tables()
