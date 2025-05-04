"""
Central SQLite database manager for project-wide use.
Provides connection, query, and schema management.
"""

import sqlite3
from typing import Any, Optional, List, Dict, Tuple


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self.conn: sqlite3.Connection = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def execute(
        self, query: str, params: Tuple[Any, ...] = (), commit: bool = False
    ) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(query, params)
        if commit:
            self.conn.commit()
        return cur

    def fetchone(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        if row is None:
            return None
        desc = [d[0] for d in cur.description]
        return dict(zip(desc, row))

    def fetchall(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        desc = [d[0] for d in cur.description]
        return [dict(zip(desc, row)) for row in rows]

    def init_tables(self) -> None:
        """
        Initialize all required tables. Extend this for new models.
        """
        # Create categories table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE
            );
        """
        )
        
        # Create snippets table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snippets (
                snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                snippet_name TEXT NOT NULL,
                content TEXT NOT NULL,
                UNIQUE(category_id, snippet_name),
                FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
            );
        """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
