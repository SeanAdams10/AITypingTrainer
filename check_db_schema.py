"""Script to check the database schema."""
import sqlite3
from pathlib import Path


def check_schema(db_path: str):
    """Check the database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables in the database:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Get schema for each table
    for table in tables:
        table_name = table[0]
        print(f"\nSchema for {table_name}:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    
    conn.close()

if __name__ == "__main__":
    db_path = str(Path(__file__).parent / "typing_data.db")
    print(f"Checking schema for database at: {db_path}")
    check_schema(db_path)
