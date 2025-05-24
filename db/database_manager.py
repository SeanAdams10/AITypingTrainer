"""
Central SQLite database manager for project-wide use.
Provides connection, query, and schema management with specific exception handling.

This is the unified database manager implementation used throughout the application.
All other database manager imports should use this class via relative imports.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from .exceptions import (
    ConnectionError,
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
)


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize a DatabaseManager with the specified database path.
        
        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
                    If None, creates an in-memory database.
                    
        Raises:
            ConnectionError: If the database connection cannot be established
        """
        self.db_path: str = db_path or ":memory:"
        try:
            self.conn: sqlite3.Connection = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to database at {self.db_path}: {e}") from e
        
        #Todo: Make sure that hte internal connection (self.conn) is marked as super private using __

    def close(self) -> None:
        """
        Close the SQLite database connection.
        """
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def _get_cursor(self) -> sqlite3.Cursor:
        """
        Get a cursor from the database connection.
        
        Returns:
            sqlite3.Cursor: A database cursor.
            
        Raises:
            ConnectionError: If the database connection is not established.
        """
        if not hasattr(self, "conn") or self.conn is None:
            raise ConnectionError("Database connection is not established")
        return self.conn.cursor()

    def execute(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query with parameters and commit immediately.
        
        Args:
            query: SQL query string (parameterized)
            params: Query parameters
            
        Returns:
            SQLite cursor object
        """
        
        #TODO: this needs to have the same discipline as FetchOne - where it raises the right kind of exceptions based on what's going wrong, and should never pass on a SQLITE error.
        
        cursor = self._get_cursor()
        cursor.execute(query, params)
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
            
        Raises:
            ConnectionError: If there's an issue connecting to the database
            ForeignKeyError: If a foreign key constraint fails
            SchemaError: If there are missing columns in the query
            DatabaseTypeError: If there's a type mismatch in the query parameters
            ConstraintError: If a database constraint is violated
            IntegrityError: If database integrity is violated
            DatabaseError: For other database-related errors
        """
        try:
            cursor = self._get_cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "unable to open database" in error_msg:
                raise ConnectionError(
                    f"Failed to connect to database at {self.db_path}"
                ) from e
            if "no such table" in error_msg or "no column" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif "not null" in error_msg or "unique" in error_msg:
                raise ConstraintError(f"Constraint violation: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        except sqlite3.InterfaceError as e:
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"Database error: {e}") from e

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
            
        Raises:
            ConnectionError: If there's an issue connecting to the database
            ForeignKeyError: If a foreign key constraint fails
            SchemaError: If there are missing columns in the query
            DatabaseTypeError: If there's a type mismatch in the query parameters
            ConstraintError: If a database constraint is violated
            IntegrityError: If database integrity is violated
            DatabaseError: For other database-related errors
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "no such table" in error_msg or "no column" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            elif "unable to open database" in error_msg:
                raise ConnectionError(f"Database connection error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif "not null" in error_msg or "unique" in error_msg:
                raise ConstraintError(f"Constraint violation: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        except sqlite3.InterfaceError as e:
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"Database error: {e}") from e

    def init_tables(self) -> None:
        """Initialize all required tables for Typing Drill.

        Creates all necessary tables for the application. Should be called once
        after instantiating DatabaseManager.

        This includes core tables for categories, snippets, and session data.
        """

        def _create_categories_table():
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT NOT NULL UNIQUE
                );
                """
            )
            
        def _create_words_table():
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS words (
                    word_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL
                );
                """
            )

        def _create_snippets_table():
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snippets (
                    snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    snippet_name TEXT NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories (category_id)
                );
                """
            )

        def _create_snippet_parts_table():
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

        def _create_practice_sessions_table():
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

        def _create_session_keystrokes_table():
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

        def _create_session_ngram_tables():
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS session_ngram_speed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    ngram_size INTEGER NOT NULL,
                    ngram TEXT NOT NULL,
                    ngram_time_ms REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                    UNIQUE(session_id, ngram)
                );

                CREATE TABLE IF NOT EXISTS session_ngram_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    ngram_size INTEGER NOT NULL,
                    ngram TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                    UNIQUE(session_id, ngram)
                );

                CREATE INDEX IF NOT EXISTS idx_ngram_speed_session ON session_ngram_speed(session_id);
                CREATE INDEX IF NOT EXISTS idx_ngram_speed_ngram ON session_ngram_speed(ngram);
                CREATE INDEX IF NOT EXISTS idx_ngram_errors_session ON session_ngram_errors(session_id);
                CREATE INDEX IF NOT EXISTS idx_ngram_errors_ngram ON session_ngram_errors(ngram);
                """
            )

        _create_categories_table()
        _create_words_table()
        _create_snippets_table()
        _create_snippet_parts_table()
        _create_practice_sessions_table()
        _create_session_keystrokes_table()
        _create_session_ngram_tables()

        self.conn.commit()

    def __enter__(self) -> "DatabaseManager":
        """
        Context manager protocol support.
        
        Returns:
            Self for using in with statements
        """
        return self
        
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: object,
    ) -> None:
        """
        Context manager protocol support - close connection when exiting context.
        """
        self.close()
        
    # Transaction management methods have been removed.
    # All database operations now use commit=True parameter to ensure immediate commits.
        
    # Manager factory methods have been removed to reduce coupling.
    # Please use dependency injection to pass the database manager to managers/repositories.
    # Example:
    #     db_manager = DatabaseManager("path/to/db")
    #     snippet_manager = SnippetManager(db_manager)
    #     session_manager = SessionManager(db_manager)
#TODO: Make sure to update the DAtabaseManager.md file with the latest understanding of the functionality
