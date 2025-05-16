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
        
        This method creates all necessary tables for the application. It should be called once after instantiating DatabaseManager.
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
                session_id TEXT PRIMARY KEY,
                snippet_id INTEGER,
                snippet_index_start INTEGER,
                snippet_index_end INTEGER,
                content TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                total_time REAL,
                session_wpm REAL,
                session_cpm REAL,
                expected_chars INTEGER,
                actual_chars INTEGER,
                errors INTEGER,
                efficiency REAL,
                correctness REAL,
                accuracy REAL,
                FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE SET NULL
            );
            """
        )
        # Session Keystrokes
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_keystrokes (
                session_id TEXT,
                keystroke_id INTEGER,
                keystroke_time DATETIME NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                time_since_previous INTEGER,
                PRIMARY KEY (session_id, keystroke_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )
        # Practice Session Errors table removed
        # Drop existing n-gram tables if they exist
        self.conn.executescript("""
            DROP TABLE IF EXISTS session_ngram_speed;
            DROP TABLE IF EXISTS session_ngram_errors;
            
            -- Session N-Gram Speed table
            -- Tracks timing information for correct n-grams
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                ngram_time_ms REAL NOT NULL,
                count INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );

            -- Session N-Gram Errors table
            -- Tracks error information for n-grams
            CREATE TABLE IF NOT EXISTS session_ngram_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                error_count INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            
            -- Create indexes for better query performance
            CREATE INDEX IF NOT EXISTS idx_ngram_speed_session ON session_ngram_speed(session_id);
            CREATE INDEX IF NOT EXISTS idx_ngram_speed_ngram ON session_ngram_speed(ngram);
            CREATE INDEX IF NOT EXISTS idx_ngram_errors_session ON session_ngram_errors(session_id);
            CREATE INDEX IF NOT EXISTS idx_ngram_errors_ngram ON session_ngram_errors(ngram);
        """)
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
        
    def begin_transaction(self) -> None:
        """
        Begin a new transaction to ensure atomicity of multiple operations.
        
        This method disables autocommit mode for the connection, allowing multiple
        operations to be executed as a single transaction.
        """
        self.conn.execute("BEGIN TRANSACTION")
        
    def commit_transaction(self) -> None:
        """
        Commit the current transaction, making all changes permanent.
        
        This method should be called after a successful sequence of operations
        that began with begin_transaction().
        """
        self.conn.commit()
        
    def rollback_transaction(self) -> None:
        """
        Roll back the current transaction, discarding all pending changes.
        
        This method should be called if an error occurs during a transaction,
        to ensure that the database remains in a consistent state.
        """
        self.conn.rollback()
        
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
    
    def get_session_manager(self) -> Any:
        """
        Returns a PracticeSessionManager instance for managing typing sessions.
        
        The PracticeSessionManager is imported inside this method to avoid circular imports.
        
        Returns:
            A PracticeSessionManager instance associated with this database connection
        """
        # Lazy import to avoid circular imports
        try:
            from models.practice_session import PracticeSessionManager
            return PracticeSessionManager(self)
        except ImportError as exc:
            # Provide a helpful error message with proper exception chaining
            raise ImportError(
                "PracticeSessionManager not found. Please make sure models/practice_session.py exists."
            ) from exc
            

