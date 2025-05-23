"""
Script to remove the content field from the text_snippets table.
This migration creates a new table without the content field,
copies the data, drops the old table, and renames the new one.
"""

import os
import sqlite3
import sys
from pathlib import Path


def remove_content_field(db_path: str) -> None:
    """
    Remove the content field from text_snippets table.

    Args:
        db_path: Path to the SQLite database file
    """
    print(f"Migrating database at: {db_path}")

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Disable foreign key constraints during migration
        cursor.execute("PRAGMA foreign_keys=off")

        # Check if text_snippets table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='text_snippets'"
        )
        if not cursor.fetchone():
            print("text_snippets table doesn't exist, nothing to migrate")
            conn.close()
            return

        # Create new table without the content field
        cursor.execute(
            """
            CREATE TABLE text_snippets_new (
                snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                snippet_name TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES text_category (category_id),
                UNIQUE (category_id, snippet_name)
            )
        """
        )

        # Copy data to the new table without the content field
        cursor.execute(
            "INSERT INTO text_snippets_new (snippet_id, category_id, snippet_name) SELECT snippet_id, category_id, snippet_name FROM text_snippets"
        )

        # Track how many rows were migrated
        rows_migrated = cursor.rowcount

        # Drop old table
        cursor.execute("DROP TABLE text_snippets")

        # Rename new table to original name
        cursor.execute("ALTER TABLE text_snippets_new RENAME TO text_snippets")

        print(f"Migration successful. {rows_migrated} rows migrated.")

    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=on")
        conn.close()


if __name__ == "__main__":
    # Use the database path directly from the project root
    db_path = Path(__file__).parents[1] / "typing_data.db"
    remove_content_field(str(db_path))
