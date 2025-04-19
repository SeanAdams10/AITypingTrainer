"""
Database initialization script for AI Typing Trainer

This script creates the necessary database tables for the application,
including categories and snippets tables required by the library manager.
"""
import os
import sqlite3
from pathlib import Path

# Get the database path
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "typing_trainer.db")

print(f"Initializing database at: {db_path}")

# Connect to the database (this will create it if it doesn't exist)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create the categories table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE
    )
""")

# Create the snippets table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS snippets (
        snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        snippet_name TEXT NOT NULL,
        text TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories (category_id)
    )
""")

# Create practice_sessions table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_sessions (
        session_id TEXT PRIMARY KEY,
        snippet_id INTEGER NOT NULL,
        snippet_index_start INTEGER NOT NULL,
        snippet_index_end INTEGER NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        practice_type TEXT,
        wpm REAL,
        cpm REAL,
        accuracy REAL,
        total_errors INTEGER,
        FOREIGN KEY (snippet_id) REFERENCES snippets (snippet_id)
    )
""")

# Create practice_session_keystrokes table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
        session_id TEXT NOT NULL,
        keystroke_id INTEGER NOT NULL,
        keystroke_time TIMESTAMP NOT NULL,
        keystroke_char TEXT NOT NULL,
        expected_char TEXT NOT NULL,
        is_correct BOOLEAN NOT NULL,
        time_since_previous INTEGER,
        PRIMARY KEY (session_id, keystroke_id),
        FOREIGN KEY (session_id) REFERENCES practice_sessions (session_id)
    )
""")

# Create practice_session_errors table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS practice_session_errors (
        session_id TEXT NOT NULL,
        error_index INTEGER NOT NULL,
        error_char TEXT NOT NULL,
        expected_char TEXT NOT NULL,
        PRIMARY KEY (session_id, error_index),
        FOREIGN KEY (session_id) REFERENCES practice_sessions (session_id)
    )
""")

# Create session_ngram_speed table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_ngram_speed (
        session_id TEXT NOT NULL,
        ngram_text TEXT NOT NULL,
        ngram_size INTEGER NOT NULL,
        avg_time REAL NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (session_id, ngram_text, ngram_size),
        FOREIGN KEY (session_id) REFERENCES practice_sessions (session_id)
    )
""")

# Create session_ngram_error table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_ngram_error (
        session_id TEXT NOT NULL,
        ngram_text TEXT NOT NULL,
        ngram_size INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (session_id, ngram_text, ngram_size),
        FOREIGN KEY (session_id) REFERENCES practice_sessions (session_id)
    )
""")

# Insert some default categories and snippets for testing
cursor.execute("SELECT COUNT(*) FROM categories")
if cursor.fetchone()[0] == 0:
    print("Adding default categories and snippets...")
    
    # Insert default categories
    cursor.execute("INSERT INTO categories (category_name) VALUES (?)", ("Programming",))
    cursor.execute("INSERT INTO categories (category_name) VALUES (?)", ("Literature",))
    cursor.execute("INSERT INTO categories (category_name) VALUES (?)", ("Science",))
    
    # Insert default snippets
    cursor.execute("""
        INSERT INTO snippets (category_id, snippet_name, text) 
        VALUES (1, 'Python Basics', 'Python is an interpreted, high-level, general-purpose programming language. 
        Created by Guido van Rossum and first released in 1991, Python has a design philosophy 
        that emphasizes code readability, notably using significant whitespace.')
    """)
    
    cursor.execute("""
        INSERT INTO snippets (category_id, snippet_name, text) 
        VALUES (2, 'Shakespeare - Hamlet', 'To be, or not to be, that is the question:
        Whether ''tis nobler in the mind to suffer
        The slings and arrows of outrageous fortune,
        Or to take arms against a sea of troubles
        And by opposing end them.')
    """)
    
    cursor.execute("""
        INSERT INTO snippets (category_id, snippet_name, text) 
        VALUES (3, 'Theory of Relativity', 'In physics, the theory of relativity is the scientific theory 
        regarding the relationship between space and time. Albert Einstein''s theory of relativity is a set 
        of two theories: special relativity and general relativity.')
    """)

# Commit changes and close the connection
conn.commit()
print("Database initialized successfully!")

# Print tables for verification
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\nTables in the database:")
for table in tables:
    print(f"- {table[0]}")

conn.close()
