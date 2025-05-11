"""
Central SQLite database manager for project-wide use.
Provides connection, query, and schema management.

This is the unified database manager implementation used throughout the application.
All other database manager imports should use this class via relative imports.
"""

import sqlite3
from typing import Any, Optional, List, Dict, Tuple, Union


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize a DatabaseManager with the specified database path.
        
        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
                    If None, creates an in-memory database.
        """
        self.db_path: str = db_path or ":memory:"
        self.conn: sqlite3.Connection = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def close(self) -> None:
        """
        Close the SQLite database connection.
        """
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def execute(
        self, query: str, params: Tuple[Any, ...] = (), commit: bool = False
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query with optional parameters and commit.
        
        Args:
            query: SQL query string (parameterized)
            params: Query parameters
            commit: Whether to commit after execution
            
        Returns:
            SQLite cursor object
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        if commit:
            self.conn.commit()
        return cursor

    def fetchone(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> Optional[Union[Dict[str, Any], sqlite3.Row]]:
        """
        Execute a query and return the first row, or None if no results.
        
        Args:
            query: SQL query string (parameterized)
            params: Query parameters
            
        Returns:
            The first row as sqlite3.Row object or None
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def fetchall(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> List[sqlite3.Row]:
        """
        Execute a query and return all rows as a list.
        
        Args:
            query: SQL query string (parameterized)
            params: Query parameters
            
        Returns:
            A list of sqlite3.Row objects
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def init_tables(self) -> None:
        """
        Initialize all required tables for Typing Drill, including core and session tables.
        
        This is an alias for initialize_tables for backward compatibility.
        """
        self.initialize_tables()
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

    def __enter__(self) -> "DatabaseManager":
        """
        Context manager protocol support.
        
        Returns:
            Self for using in with statements
        """
        return self
        
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Context manager protocol support - close connection when exiting context.
        """
        self.close()
        
    def get_snippet_manager(self) -> Any:
        """
        Returns a SnippetManager instance for managing snippets.
        
        The SnippetManager is imported inside this method to avoid circular imports.
        
        Returns:
            A SnippetManager instance associated with this database connection
        """
        # Lazy import to avoid circular imports
        try:
            from models.snippet_manager import SnippetManager
            return SnippetManager(self)
        except ImportError as exc:
            # Provide a helpful error message with proper exception chaining
            raise ImportError(
                "SnippetManager not found. Please make sure models/snippet_manager.py exists."
            ) from exc
            
    def initialize_tables(self) -> None:
        """
        Create all database tables if they don't exist.
        
        Creates:
        - categories
        - snippets
        - snippet_parts
        - practice_sessions
        - practice_session_keystrokes
        - practice_session_errors
        - practice_session_ngram_speed
        - practice_session_ngram_errors
        """
