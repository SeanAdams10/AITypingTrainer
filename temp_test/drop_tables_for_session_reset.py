"""
Script to drop keystroke, session, ngram_errors, and ngram_speed tables for schema reset.
"""

import sqlite3

DB_PATH = "snippets_library.db"  # Change if needed

tables = [
    "session_keystrokes",
    "practice_sessions",
    "session_ngram_speed",
    "session_ngram_errors",
]


def drop_tables(db_path: str, tables: list[str]):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for table in tables:
        try:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"Dropped table: {table}")
        except Exception as e:
            print(f"Error dropping {table}: {e}")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    drop_tables(DB_PATH, tables)
