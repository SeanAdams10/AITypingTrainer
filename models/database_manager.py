"""
DatabaseManager: Central class for DB connection and query execution.
Ensures parameterized queries, connection management, and error handling.
"""

import sqlite3
from typing import Any, Optional, Tuple


class DatabaseManager:
    def initialize_category_table(self) -> None:
        """
        Create the categories table if it does not exist.
        """
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE
            );
            """,
            commit=True,
        )

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path: str = db_path or ":memory:"
        self.conn: sqlite3.Connection = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def execute(
        self, query: str, params: Tuple[Any, ...] = (), commit: bool = False
    ) -> sqlite3.Cursor:
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        if commit:
            self.conn.commit()
        return cursor

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "DatabaseManager":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
