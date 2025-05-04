"""
Diagnostic script to test Category creation directly in isolation.
This helps us identify issues with the database/model setup outside the API context.
"""
import os
import sys
import tempfile
import sqlite3
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.database_manager import DatabaseManager
from models.category import Category

# (To be rebuilt: Diagnostic script for category creation and DB checks)

def main():
    pass
    
    # Reset and initialize DatabaseManager with test DB
    DatabaseManager.reset_instance()
    db = DatabaseManager()
    db.set_db_path(db_path)
    
    try:
        # Initialize database schema
        print("Initializing database schema...")
        db.initialize_database()
        
        # Verify tables were created
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"Created tables: {tables}")
        
        # Check if text_category table exists
        if 'text_category' not in tables:
            print("ERROR: text_category table not created!")
            return
        
        # Ensure category exists for diagnosis
        from db.database_manager import DatabaseManager
        db = DatabaseManager.get_instance()
        db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'Alpha') ON CONFLICT(category_id) DO NOTHING")
        # Try creating a category
        print("Attempting to create category...")
        try:
            category_id = Category.create_category("Test Category")
            print(f"SUCCESS: Created category with ID: {category_id}")
        except Exception as e:
            print(f"ERROR creating category: {e}")
            print(traceback.format_exc())
    
    except Exception as e:
        print(f"ERROR: {e}")
        print(traceback.format_exc())
    
    print("Diagnosis complete")

if __name__ == "__main__":
    main()
