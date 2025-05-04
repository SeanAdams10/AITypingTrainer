"""
DatabaseManager: Central class for DB connection and query execution.
Ensures parameterized queries, connection management, and error handling.
"""

import sqlite3
from typing import Any, Optional, Tuple


class DatabaseManager:
    def initialize_tables(self) -> None:
        """
        Create the categories, snippets, and snippet_parts tables if they do not exist.
        """
        # Create category table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE
            );
            """,
            commit=True,
        )
        
        # Create snippets table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS snippets (
                snippet_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                category_id INTEGER NOT NULL,
                snippet_name TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (category_id),
                UNIQUE (category_id, snippet_name)
            );
            """,
            commit=True,
        )
        
        # Create snippet_parts table
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS snippet_parts (
                snippet_id INTEGER NOT NULL,
                part_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (snippet_id, part_number),
                FOREIGN KEY (snippet_id) REFERENCES snippets (snippet_id)
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

    def fetchone(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        """
        Execute a query and return the first row, or None if no results.
        Args:
            query: SQL query string (parameterized)
            params: Query parameters
        Returns:
            The first sqlite3.Row or None
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: Tuple[Any, ...] = ()) -> list:
        """
        Execute a query and return all rows as a list.
        Args:
            query: SQL query string (parameterized)
            params: Query parameters
        Returns:
            A list of sqlite3.Row objects.
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "DatabaseManager":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
