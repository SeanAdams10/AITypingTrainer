"""
Script to check all tables in the database
"""
import sqlite3
import os

# Get the database path
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "typing_trainer.db")

print(f"Database path: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\nTables in the database:")
    for table in tables:
        print(f"- {table[0]}")

    # Check for both table names
    print("\nChecking specific tables:")
    for table_name in ['categories', 'text_category', 'snippets', 'text_snippet']:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if cursor.fetchone():
            print(f"- {table_name} EXISTS")
            # Show table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for column in columns:
                print(f"  - {column[1]} ({column[2]})")
        else:
            print(f"- {table_name} does NOT exist")

    # Close the connection
    conn.close()
else:
    print("Database file does not exist!")
