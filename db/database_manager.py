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

    def close(self) -> None:
        """
        Close the SQLite database connection.
        """
        if self.conn:
            self.conn.close()

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
        Initialize all required tables for Typing Drill, including core and session tables.
        """
        # Categories
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE
            );
            """
        )
        # Snippets
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snippets (
                snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                snippet_name TEXT NOT NULL,
                UNIQUE(category_id, snippet_name),
                FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE
            );
            """
        )
        # Snippet Parts
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snippet_parts (
                snippet_id INTEGER NOT NULL,
                part_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                PRIMARY KEY (snippet_id, part_number),
                FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
            );
            """
        )
        # Practice Sessions
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snippet_id INTEGER,
                snippet_index_start INTEGER,
                snippet_index_end INTEGER,
                start_time TEXT,
                end_time TEXT,
                total_time INTEGER,
                session_wpm REAL,
                session_cpm REAL,
                expected_chars INTEGER,
                actual_chars INTEGER,
                errors INTEGER,
                accuracy REAL,
                FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE SET NULL
            );
            """
        )
        # Practice Session Keystrokes
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
                keystroke_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                char_index INTEGER NOT NULL,
                key TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                event_time TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )
        # Practice Session Errors
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_session_errors (
                error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                char_index INTEGER NOT NULL,
                expected_char TEXT NOT NULL,
                actual_char TEXT NOT NULL,
                event_time TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )
        # Practice Session Ngram Speed
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_session_ngram_speed (
                ngram_speed_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                speed REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )
        # Practice Session Ngram Errors
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_session_ngram_errors (
                ngram_error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                error_count INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
