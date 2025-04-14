"""
Script to check the database schema and tables
"""
import sqlite3
import os
from pathlib import Path

# Get the database path
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "typing_trainer.db")

print(f"Database path: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\nTables in the database:")
for table in tables:
    print(f"- {table[0]}")

# Check if categories table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
if cursor.fetchone():
    print("\nCategories table exists. Checking schema:")
    cursor.execute("PRAGMA table_info(categories)")
    columns = cursor.fetchall()
    for column in columns:
        print(f"- {column[1]} ({column[2]})")
else:
    print("\nCategories table does NOT exist!")

# Close the connection
conn.close()
