"""
Central SQLite database manager for project-wide use.
Provides connection, query, and schema management with specific exception handling.

This is the unified database manager implementation used throughout the application.
All other database manager imports should use this class via relative imports.
"""

import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from .exceptions import (
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    DBConnectionError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
    TableNotFoundError,
)


class DatabaseManager:
    """
    Centralized manager for SQLite database connections and operations.

    Handles connection management, query execution, schema initialization, and
    exception translation for the Typing Trainer application. All database access
    should be performed through this class to ensure consistent error handling and
    schema management.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize a DatabaseManager with the specified database path.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
                    If None, creates an in-memory database.

        Raises:
            DBConnectionError: If the database connection cannot be established.
        """
        self.db_path: str = db_path or ":memory:"
        try:
            self.__conn: sqlite3.Connection = sqlite3.connect(self.db_path)
            self.__conn.row_factory = sqlite3.Row
            self.__conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            raise DBConnectionError(f"Failed to connect to database at {self.db_path}: {e}") from e

        # (Reminder: internal connection should always be accessed via self.__conn)

    def close(self) -> None:
        """
        Close the SQLite database connection.

        Raises:
            DBConnectionError: If closing the connection fails.
        """
        if hasattr(self, "__conn") and self.__conn:
            try:
                self.__conn.close()
            except sqlite3.Error as e:
                # Log and print the error, then re-raise
                logging.error("Error closing database connection: %s", e)
                print(f"Error closing database connection: {e}")
                raise

    def _get_cursor(self) -> sqlite3.Cursor:
        """
        Get a cursor from the database connection.

        Returns:
            sqlite3.Cursor: A database cursor.

        Raises:
            DBConnectionError: If the database connection is not established.
        """
        if self.__conn is None:
            raise DBConnectionError("Database connection is not established")
        return self.__conn.cursor()

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query with parameters and commit immediately.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            SQLite cursor object

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        # (Reminder: use FetchOne-style exception discipline for this method)
        try:
            cursor = self._get_cursor()
            cursor.execute(query, params)
            self.__conn.commit()
            return cursor
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "unable to open database" in error_msg:
                raise DBConnectionError(f"Failed to connect to database at {self.db_path}") from e
            if "no such table" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "no such column" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif "not null" in error_msg or "unique" in error_msg:
                raise ConstraintError(f"Constraint violation: {e}") from e
            elif "datatype mismatch" in error_msg:
                raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        except sqlite3.InterfaceError as e:
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        except sqlite3.DatabaseError as e:
            raise DatabaseError(f"Database error: {e}") from e

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
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        try:
            cursor = self._get_cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "unable to open database" in error_msg:
                raise DBConnectionError(f"Failed to connect to database at {self.db_path}") from e
            if "no such table" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "no column" in error_msg:
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

    def fetchall(self, query: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        """
        Execute a query and return all rows as a list.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            A list of sqlite3.Row objects

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        try:
            cursor = self.__conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "no such table" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "no column" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            elif "unable to open database" in error_msg:
                raise DBConnectionError(f"Database connection error: {e}") from e
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

    def _create_categories_table(self) -> None:
        """Create the categories table with UUID primary key if it does not exist."""
        self.__conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id TEXT PRIMARY KEY,
                category_name TEXT NOT NULL UNIQUE
            );
            """
        )

    def _create_words_table(self) -> None:
        """Create the words table if it does not exist."""
        self.__conn.execute(
            """
            CREATE TABLE IF NOT EXISTS words (
                word_id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE
            );
            """
        )

    def _create_snippets_table(self) -> None:
        """Create the snippets table with UUID primary key if it does not exist."""
        self.__conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snippets (
                snippet_id TEXT PRIMARY KEY,
                category_id TEXT NOT NULL,
                snippet_name TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE CASCADE,
                UNIQUE (category_id, snippet_name)
            );
            """
        )

    def _create_snippet_parts_table(self) -> None:
        """Create the snippet_parts table with UUID foreign key if it does not exist."""
        self.__conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snippet_parts (
                part_id TEXT PRIMARY KEY,
                snippet_id TEXT NOT NULL,
                part_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
            );
            """
        )

    def _create_practice_sessions_table(self) -> None:
        """Create the practice_sessions table with UUID PK if it does not exist."""
        self.__conn.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id TEXT PRIMARY KEY,
                snippet_id TEXT NOT NULL,
                snippet_index_start INTEGER NOT NULL,
                snippet_index_end INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                total_time REAL NOT NULL,
                session_wpm REAL,
                session_cpm REAL,
                expected_chars INTEGER NOT NULL,
                actual_chars INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                efficiency REAL,
                correctness REAL,
                accuracy REAL,
                FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE
            );
            """
        )

    def _create_session_keystrokes_table(self) -> None:
        """Create the session_keystrokes table with UUID PK if it does not exist."""
        self.__conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_keystrokes (
                keystroke_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                key_char TEXT NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )

    def _create_session_ngram_tables(self) -> None:
        """Create the session_ngram_speed and session_ngram_errors tables with UUID PKs."""
        self.__conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                ngram_speed_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram TEXT NOT NULL,
                avg_time REAL NOT NULL,
                count INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                UNIQUE (session_id, ngram)
            );

            CREATE TABLE IF NOT EXISTS session_ngram_errors (
                ngram_error_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram TEXT NOT NULL,
                error_count INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                UNIQUE (session_id, ngram)
            );

            CREATE INDEX IF NOT EXISTS idx_ngram_speed_session_ngram ON session_ngram_speed (
                session_id, ngram
            );
            CREATE INDEX IF NOT EXISTS idx_ngram_errors_session_ngram ON session_ngram_errors (
                session_id, ngram
            );
            """
        )

    def init_tables(self) -> None:
        """Initialize all database tables by creating them if they do not exist.
        This includes core tables for categories, snippets, and session data.
        """
        self._create_categories_table()
        self._create_words_table()
        self._create_snippets_table()
        self._create_snippet_parts_table()
        self._create_practice_sessions_table()
        self._create_session_keystrokes_table()
        self._create_session_ngram_tables()

        self.__conn.commit()

    def __enter__(self) -> "DatabaseManager":
        """
        Context manager protocol support.

        Returns:
            Self for using in with statements.
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
