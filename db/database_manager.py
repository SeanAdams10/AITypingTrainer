"""
Central database manager for project-wide use.
Provides connection, query, and schema management with specific exception handling.
Supports both local SQLite and cloud AWS Aurora PostgreSQL connections.

This is the unified database manager implementation used throughout the application.
All other database manager imports should use this class via relative imports.
"""

import enum
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Type

try:
    import boto3
    import psycopg2
    CLOUD_DEPENDENCIES_AVAILABLE = True
except ImportError:
    CLOUD_DEPENDENCIES_AVAILABLE = False

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


class ConnectionType(enum.Enum):
    """Connection type enum for database connections."""
    LOCAL = "local"
    CLOUD = "cloud"


class DatabaseManager:
    """
    Centralized manager for database connections and operations.

    Handles connection management, query execution, schema initialization, and
    exception translation for the Typing Trainer application. All database access
    should be performed through this class to ensure consistent error handling and
    schema management.

    Supports both local SQLite and cloud AWS Aurora PostgreSQL connections.
    """

    # AWS Aurora configuration
    AWS_REGION = "us-east-1"
    SECRETS_ID = "Aurora/WBTT_Config"
    SCHEMA_NAME = "typing"

    def __init__(self, db_path: Optional[str] = None, connection_type: ConnectionType = ConnectionType.LOCAL) -> None:
        """
        Initialize a DatabaseManager with the specified connection type and parameters.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
                    If None, creates an in-memory database.
                    Only used when connection_type is LOCAL.
            connection_type: Whether to use local SQLite or cloud Aurora PostgreSQL.

        Raises:
            DBConnectionError: If the database connection cannot be established.
            ImportError: If cloud dependencies are not available when cloud connection is requested.
        """
        self.connection_type = connection_type
        self.db_path: str = db_path or ":memory:"
        self.is_postgres = False

        if connection_type == ConnectionType.LOCAL:
            self._connect_sqlite()
        else:  # CLOUD
            if not CLOUD_DEPENDENCIES_AVAILABLE:
                raise ImportError(
                    "Cloud connection requires boto3 and psycopg2 packages. "
                    "Please install them first."
                )
            self._connect_aurora()

    def _connect_sqlite(self) -> None:
        """
        Establish connection to a local SQLite database.

        Raises:
            DBConnectionError: If the database connection cannot be established.
        """
        try:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            raise DBConnectionError(
                f"Failed to connect to SQLite database at {self.db_path}: {e}"
            ) from e

    def _connect_aurora(self) -> None:
        """
        Establish connection to AWS Aurora PostgreSQL.

        Raises:
            DBConnectionError: If the database connection cannot be established.
        """
        try:
            # Get secrets from AWS Secrets Manager
            sm_client = boto3.client('secretsmanager', region_name=self.AWS_REGION)
            secret = sm_client.get_secret_value(SecretId=self.SECRETS_ID)
            config = eval(secret['SecretString'])

            # Generate auth token for Aurora serverless
            rds = boto3.client('rds', region_name=self.AWS_REGION)
            token = rds.generate_db_auth_token(
                DBHostname=config['host'],
                Port=int(config['port']),
                DBUsername=config['username'],
                Region=self.AWS_REGION
            )

            # Connect to Aurora
            self._conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=config['dbname'],
                user=config['username'],
                password=token,
                sslmode='require'
            )

            # Set search_path to schema
            cursor = self._conn.cursor()
            cursor.execute(f"SET search_path TO {self.SCHEMA_NAME}")
            self._conn.commit()
            cursor.close()

            self.is_postgres = True
        except Exception as e:
            raise DBConnectionError(f"Failed to connect to AWS Aurora database: {e}") from e

    def close(self) -> None:
        """
        Close the SQLite database connection.

        Raises:
            DBConnectionError: If closing the connection fails.
        """
        try:
            self._conn.close()
            # del self._conn
        except sqlite3.Error as e:
            # Log and print the error, then re-raise
            logging.error("Error closing database connection: %s", e)
            print(f"Error closing database connection: {e}")
            raise

    def _get_cursor(self) -> sqlite3.Cursor:
        """
        Get a cursor from the database connection.

        Returns:
            A database cursor (either sqlite3.Cursor or object for psycopg2).

        Raises:
            DBConnectionError: If the database connection is not established.
        """
        if not self._conn:
            raise DBConnectionError("Database connection is not established")
        return self._conn.cursor()

    def _execute_ddl(self, query: str) -> None:
        """
        Execute DDL (Data Definition Language) statements consistently across both
        SQLite and PostgreSQL connections using a cursor-based approach.

        Args:
            query: SQL DDL statement to execute

        Raises:
            Various database exceptions depending on the error type
        """
        try:
            cursor = self._conn.cursor()
            cursor.execute(query)
            if self.is_postgres:
                self._conn.commit()  # PostgreSQL requires explicit commit
        except Exception:
            # Pass through to let the caller handle specific exceptions
            raise

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> Any:
        """
        Execute a SQL query with parameters and commit immediately.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            Database cursor object

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        # (Reminder: use FetchOne-style exception discipline for this method)
        try:
            cursor = self._get_cursor()

            # Adjust query for PostgreSQL if needed
            if self.is_postgres:
                # Convert SQLite's ? placeholders to PostgreSQL's %s if needed
                if '?' in query:
                    query = query.replace('?', '%s')
                # Add schema prefix to table names if not already present
                if query.strip().upper().startswith(('CREATE TABLE', 'DROP TABLE', 'ALTER TABLE',
                                                  'INSERT INTO', 'UPDATE',
                                                  'DELETE FROM', 'SELECT')) \
                   and f"{self.SCHEMA_NAME}." not in query:
                    # Simple heuristic to add schema name before the first table reference
                    table_keyword_pos = max(
                        query.upper().find('TABLE ') + 6
                        if query.upper().find('TABLE ') >= 0 else -1,
                        query.upper().find('INTO ') + 5
                        if query.upper().find('INTO ') >= 0 else -1,
                        query.upper().find('UPDATE ') + 7
                        if query.upper().find('UPDATE ') >= 0 else -1,
                        query.upper().find('FROM ') + 5
                        if query.upper().find('FROM ') >= 0 else -1,
                    )
                    if table_keyword_pos > 0:
                        # Find the end of table name
                        rest_of_query = query[table_keyword_pos:].lstrip()
                        table_name_end = rest_of_query.find(' ')
                        if table_name_end > 0:
                            table_name = rest_of_query[:table_name_end]
                        else:
                            table_name = rest_of_query
                        # Don't modify if it's already qualified or contains parentheses
                        if '.' not in table_name and '(' not in table_name:
                            query = query.replace(table_name, f"{self.SCHEMA_NAME}.{table_name}", 1)

            cursor.execute(query, params)
            self._conn.commit()
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
        except (psycopg2.OperationalError, psycopg2.ProgrammingError) as e:
            error_msg = str(e).lower()
            if "connection" in error_msg:
                raise DBConnectionError(f"Failed to connect to PostgreSQL database: {e}") from e
            if "does not exist" in error_msg and "relation" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "column" in error_msg and "does not exist" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        except psycopg2.IntegrityError as e:
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif "not null" in error_msg or "unique" in error_msg:
                raise ConstraintError(f"Constraint violation: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        except psycopg2.DataError as e:
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        except psycopg2.DatabaseError as e:
            raise DatabaseError(f"Database error: {e}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected database error: {e}") from e

    def fetchone(
        self, query: str, params: Tuple[Any, ...] = ()
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a SQL query and fetch a single result.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            Dict representing fetched row, or None if no results
            Both SQLite and PostgreSQL results are returned as dictionaries with column names as keys

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        cursor = self.execute(query, params)
        result = cursor.fetchone()

        # Return None if no result
        if result is None:
            return None

        # For PostgreSQL, convert tuple to dict using column names
        if self.is_postgres:
            col_names = [desc[0] for desc in cursor.description]
            return {col_names[i]: result[i] for i in range(len(col_names))}

        # SQLite's Row objects can be used as dictionaries but let's normalize to dict
        return dict(result)

    def fetchmany(
        self, query: str, params: Tuple[Any, ...] = (), size: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and fetch multiple results.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters
            size: Number of rows to fetch

        Returns:
            List of Dict representing fetched rows
            Both SQLite and PostgreSQL results are returned as dictionaries with column names as keys

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        cursor = self.execute(query, params)
        results = cursor.fetchmany(size)

        # For PostgreSQL, convert tuples to dicts using column names
        if self.is_postgres and results:
            col_names = [desc[0] for desc in cursor.description]
            return [{col_names[i]: row[i] for i in range(len(col_names))} for row in results]

        # SQLite's Row objects can be used as dictionaries but let's normalize to dict
        return [dict(row) for row in results]

    def fetchall(self, query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        """
        Execute a query and return all rows as a list.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            A list of dictionaries, with each dictionary representing a row
            Both SQLite and PostgreSQL results are returned as dictionaries with column names as keys

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        cursor = self.execute(query, params)
        results = cursor.fetchall()

        # For PostgreSQL, convert tuples to dicts using column names
        if self.is_postgres and results:
            col_names = [desc[0] for desc in cursor.description]
            return [{col_names[i]: row[i] for i in range(len(col_names))} for row in results]

        # SQLite's Row objects can be used as dictionaries but let's normalize to dict
        return [dict(row) for row in results]

    def _create_categories_table(self) -> None:
        """Create the categories table with UUID primary key if it does not exist."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id TEXT PRIMARY KEY,
                category_name TEXT NOT NULL UNIQUE
            );
            """
        )

    def _create_words_table(self) -> None:
        """Create the words table with UUID primary key if it does not exist."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS words (
                word_id TEXT PRIMARY KEY,
                word TEXT NOT NULL UNIQUE
            );
            """
        )

    def _create_snippets_table(self) -> None:
        """Create the snippets table with UUID primary key if it does not exist."""
        self._execute_ddl(
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
        self._execute_ddl(
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
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                keyboard_id TEXT NOT NULL,
                snippet_id TEXT NOT NULL,
                snippet_index_start INTEGER NOT NULL,
                snippet_index_end INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                actual_chars INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                ms_per_keystroke REAL NOT NULL,
                FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE
            );
            """
        )

    def _create_session_keystrokes_table(self) -> None:
        """Create the session_keystrokes table with UUID PK if it does not exist."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS session_keystrokes (
                keystroke_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                keystroke_time TEXT NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_error INTEGER NOT NULL,
                time_since_previous INTEGER,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )

    def _create_session_ngram_tables(self) -> None:
        """Create the session_ngram_speed and session_ngram_errors tables with UUID PKs."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                ngram_speed_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                ngram_time_ms REAL NOT NULL,
                ms_per_keystroke REAL DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )

        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS session_ngram_errors (
                ngram_error_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            );
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_speed_session_ngram ON session_ngram_speed (
                session_id, ngram_text, ngram_size
            );
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_errors_session_ngram ON session_ngram_errors (
                session_id, ngram_text, ngram_size
            );
            """
        )

    def _create_users_table(self) -> None:
        """Create the users table with UUID primary key if it does not exist."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                surname TEXT NOT NULL,
                email_address TEXT NOT NULL UNIQUE
            );
            """
        )

    def _create_keyboards_table(self) -> None:
        """Create the keyboards table with UUID primary key and user_id foreign key
        if it does not exist.
        """
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS keyboards (
                keyboard_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                keyboard_name TEXT NOT NULL,
                target_ms_per_keystroke INTEGER NOT NULL default 600,
                UNIQUE(user_id, keyboard_name),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
                    ON DELETE CASCADE
            );
            """
        )

    def _create_settings_table(self) -> None:
        """Create the settings table with UUID primary key if it does not exist.

        Also drops the legacy user_settings table if it exists.
        """
        # Drop the legacy user_settings table if it exists
        try:
            self._execute_ddl("DROP TABLE IF EXISTS user_settings;")
        except Exception:
            pass

        # Create the new settings table
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS settings (
                setting_id TEXT PRIMARY KEY,
                setting_type_id TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                related_entity_id TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(setting_type_id, related_entity_id)
            );
            """
        )

    def _create_settings_history_table(self) -> None:
        """Create the settings_history table with UUID primary key if it does not exist."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS settings_history (
                history_id TEXT PRIMARY KEY,
                setting_id TEXT NOT NULL,
                setting_type_id TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                related_entity_id TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    def init_tables(self) -> None:
        """Initialize all database tables by creating them if they do not exist.
        This includes core tables for categories, snippets, session data, users,
        keyboards, and settings.
        """
        self._create_categories_table()
        self._create_words_table()
        self._create_snippets_table()
        self._create_snippet_parts_table()
        self._create_practice_sessions_table()
        self._create_session_keystrokes_table()
        self._create_session_ngram_tables()
        self._create_users_table()
        self._create_keyboards_table()
        self._create_settings_table()
        self._create_settings_history_table()

        self._conn.commit()

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
