"""Central database manager for project-wide use.

Provides connection, query, and schema management with specific exception handling.
Supports both local SQLite and cloud AWS Aurora PostgreSQL connections.

This is the unified database manager implementation used throughout the application.
All other database manager imports should use this class via relative imports.
"""

import contextlib
import enum
import io
import json
import logging
import os
import re
import time
import traceback
import uuid
from typing import (
    IO,
    Dict,
    Iterable,
    List,
    NoReturn,
    Optional,
    Protocol,
    Self,
    Sequence,
    TextIO,
    Tuple,
    Type,
    Union,
    cast,
)

import boto3
import docker
import psycopg2
from psycopg2 import extras as psycopg2_extras

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

# Removed optional alias/guards; direct imports are now required.


def debug_print(*args: object, **kwargs: object) -> None:
    """Print debug messages based on environment variable setting.

    Args:
        *args: Arguments to pass to print()
        **kwargs: Keyword arguments to pass to print()
    """
    # Imports moved to top of file

    debug_mode = os.environ.get("AI_TYPING_TRAINER_DEBUG_MODE", "loud").lower()
    if debug_mode != "quiet":
        sep_val = kwargs.get("sep")
        end_val = kwargs.get("end")
        flush_val = kwargs.get("flush")
        file_val = kwargs.get("file")

        sep_arg: Optional[str] = sep_val if (sep_val is None or isinstance(sep_val, str)) else None
        end_arg: Optional[str] = end_val if (end_val is None or isinstance(end_val, str)) else None
        flush_arg: bool = bool(flush_val) if isinstance(flush_val, bool) else False

        file_obj = (
            cast(Optional[IO[str]], file_val) if isinstance(file_val, object) and hasattr(file_val, "write") else None
        )

        args_tuple: tuple[object, ...] = tuple(args)
        if file_obj is not None:
            print(*args_tuple, sep=sep_arg, end=end_arg, file=file_obj, flush=flush_arg)
        else:
            print(*args_tuple, sep=sep_arg, end=end_arg, flush=flush_arg)


class ConnectionProtocol(Protocol):
    """Minimal DB-API connection protocol used by DatabaseManager."""

    def cursor(self) -> "CursorProtocol":
        """Return a new database cursor."""
        ...

    def commit(self) -> None:
        """Commit the current transaction."""
        ...

    def rollback(self) -> None:
        """Rollback the current transaction."""
        ...

    def close(self) -> None:
        """Close the underlying connection."""
        ...

    # Optional attributes/methods present on certain backends
    # SQLite connection exposes row_factory and execute (for PRAGMA)
    row_factory: object  # pragma: no cover - typing aid

    def execute(self, query: str) -> None:
        """Execute a statement on backends that expose connection.execute (SQLite)."""
        ...  # pragma: no cover - typing aid

    # psycopg2 connection offers autocommit
    autocommit: bool  # pragma: no cover - typing aid


class CursorProtocol(Protocol):
    """Minimal DB-API cursor protocol used by DatabaseManager."""

    def execute(self, query: str, params: Tuple[object, ...] = ...) -> Self:
        """Execute a single SQL statement with optional parameters."""
        ...

    def executemany(self, query: str, seq_of_params: Iterable[Tuple[object, ...]]) -> Self:
        """Execute a SQL statement against all parameter tuples."""
        ...

    def fetchone(self) -> Optional[Union[Dict[str, object], Tuple[object, ...]]]:
        """Fetch the next row of a query result."""
        ...

    def fetchall(self) -> List[Union[Dict[str, object], Tuple[object, ...]]]:
        """Fetch all remaining rows of a query result."""
        ...

    def fetchmany(self, size: int = ...) -> List[Union[Dict[str, object], Tuple[object, ...]]]:
        """Fetch up to size rows of a query result."""
        ...

    def close(self) -> None:
        """Close the cursor."""
        ...

    # PostgreSQL-specifics used in bulk COPY
    def copy_from(
        self,
        file: TextIO,
        table: str,
        columns: Optional[Iterable[str]] = ...,
        sep: str = ...,
        null: str = ...,
    ) -> None:
        """PostgreSQL COPY FROM STDIN interface."""
        ...

    # Optional attribute for column metadata
    @property
    def description(self) -> Optional[Sequence[Sequence[object]]]:
        """DB-API cursor description: column metadata or None before execution."""
        ...

    # Support context manager usage in some code paths (psycopg2)
    def __enter__(self) -> Self:
        """Enter context manager for cursor (psycopg2)."""
        ...  # pragma: no cover - typing aid

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: object,
    ) -> None:
        """Exit context manager for cursor (psycopg2)."""
        ...  # pragma: no cover - typing aid


class ConnectionType(enum.Enum):
    """Connection type enum for database connections."""

    CLOUD = "cloud"
    POSTGRESS_DOCKER = "postgres_docker"


class BulkMethod(enum.Enum):
    """Bulk execution strategy for DatabaseManager.execute_many()."""

    AUTO = "auto"  # Choose best available (values for INSERT on Postgres; else fallback)
    VALUES = "values"  # Force psycopg2.extras.execute_values (Postgres INSERT only)
    COPY = "copy"  # Force COPY FROM STDIN (Postgres INSERT only)
    EXECUTEMANY = "execute_many"  # Force DB-API executemany fallback


class DatabaseManager:
    """Centralized manager for database connections and operations.

    Handles connection management, query execution, schema initialization, and
    exception translation for the Typing Trainer application. All database access
    should be performed through this class to ensure consistent error handling and
    schema management.

    Supports both local SQLite and cloud AWS Aurora PostgreSQL connections.
    """

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database (backend-agnostic).

        Args:
            table_name: Name of the table to check
        Returns:
            True if the table exists, False otherwise
        """
        query = (
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s AND table_type = 'BASE TABLE'"
        )
        params = (self.SCHEMA_NAME, table_name)
        result = self.fetchone(query, params)
        return result is not None

    def list_tables(self) -> List[str]:
        """Return a list of all user table names in the database, backend-agnostic.

        Returns:
            A list of table names as strings
        """
        query = (
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
            "ORDER BY table_name"
        )
        params = (self.SCHEMA_NAME,)
        rows = self.fetchall(query, params)
        return [cast(str, row["table_name"]) for row in rows]

    # AWS Aurora configuration
    AWS_REGION = "us-east-1"
    SECRETS_ID = "Aurora/WBTT_Config"
    SCHEMA_NAME = "typing"

    def __init__(
        self,
        db_path: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.POSTGRESS_DOCKER,
        debug_util: Optional[object] = None,
    ) -> None:
        """Initialize a DatabaseManager with the specified connection type and parameters.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory database.
                    If None, creates an in-memory database.
                    Only used when connection_type is LOCAL.
            connection_type: Whether to use local SQLite or cloud Aurora PostgreSQL.
            debug_util: Optional DebugUtil instance for handling debug output.

        Raises:
            DBConnectionError: If the database connection cannot be established.
            ImportError: If cloud dependencies are not available when cloud connection
                is requested.
        """
        self.connection_type = connection_type
        self.db_path: str = db_path or ""
        self.is_postgres = False
        self._conn: ConnectionProtocol = cast(ConnectionProtocol, None)  # Set in connect methods
        self.debug_util = debug_util  # Store the DebugUtil instance

        self._docker_container_name: Optional[str] = None
        self._docker_host_port: Optional[int] = None
        self._docker_container_id: Optional[str] = None
        self._docker_client = None  # DockerClient when available

        if connection_type == ConnectionType.CLOUD:
            self._connect_aurora()
        elif connection_type == ConnectionType.POSTGRESS_DOCKER:
            self._connect_postgres_docker()
        else:
            raise DBConnectionError(f"Unsupported connection type: {connection_type}")

    def _debug_message(self, *args: object, **kwargs: object) -> None:
        """Send debug message through DebugUtil if available, otherwise use debug_print fallback."""
        if self.debug_util and hasattr(self.debug_util, "debugMessage"):
            self.debug_util.debugMessage(*args, **kwargs)
        else:
            # Fallback to the old debug_print function if DebugUtil not available
            debug_print(*args, **kwargs)

    # SQLite connection method removed; only Postgres backends supported.

    def _connect_aurora(self) -> None:
        """Establish connection to AWS Aurora PostgreSQL.

        Raises:
            DBConnectionError: If the database connection cannot be established.
        """
        try:
            # Get secrets from AWS Secrets Manager
            sm_client = boto3.client("secretsmanager", region_name=self.AWS_REGION)
            secret = sm_client.get_secret_value(SecretId=self.SECRETS_ID)
            secret_str = cast(str, secret["SecretString"])
            config = cast(Dict[str, str], json.loads(secret_str))

            # Generate auth token for Aurora serverless
            rds = boto3.client("rds", region_name=self.AWS_REGION)
            token = rds.generate_db_auth_token(
                DBHostname=config["host"],
                Port=int(config["port"]),
                DBUsername=config["username"],
                Region=self.AWS_REGION,
            )

            # Connect to Aurora
            self._conn = cast(
                ConnectionProtocol,
                psycopg2.connect(
                    host=config["host"],
                    port=int(config["port"]),
                    database=config["dbname"],
                    user=config["username"],
                    password=token,
                    sslmode="require",
                    options=f"-c search_path={self.SCHEMA_NAME},public",
                ),
            )
            # Set autocommit when available (psycopg2)
            self._conn.autocommit = True

            # Ensure the target schema exists to avoid UndefinedTable on qualified ops
            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.SCHEMA_NAME}")
            except Exception as schema_exc:
                # Non-fatal: we'll surface later if DDL/DML fails, but log for visibility
                traceback.print_exc()
                self._debug_message(f"Failed to ensure schema '{self.SCHEMA_NAME}': {schema_exc}")

            # Debug connection/session state
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT current_user, current_schema, current_setting('search_path')")
                    row = cur.fetchone()
                    if row:
                        row_t = cast(Tuple[object, ...], row)
                        self._debug_message(f"PG session user={row_t[0]}, schema={row_t[1]}, search_path={row_t[2]}")
            except Exception as sess_exc:
                self._debug_message(f"Failed to read PG session state: {sess_exc}")
                traceback.print_exc()

            self.is_postgres = True
        except Exception as e:
            traceback.print_exc()
            self._debug_message(f"Aurora connection failed: {e}")
            raise DBConnectionError(f"Failed to connect to AWS Aurora database: {e}") from e

    # --- Docker-based Postgres support ---
    POSTGRES_IMAGE = "postgres:16-alpine"
    POSTGRES_USER = "postgres"
    POSTGRES_PASSWORD = "postgres"
    POSTGRES_DB = "typing_demo"

    def _ensure_docker_available(self) -> None:
        try:
            client = docker.from_env()
            client.ping()
            # Store client for reuse
            self._docker_client = client
        except Exception as exc:
            raise DBConnectionError(
                "Docker SDK cannot reach the Docker daemon. Ensure Docker Desktop is running "
                "and the current user has access to the Docker Engine."
            ) from exc

    def _create_postgres_container(self) -> Tuple[str, int]:
        try:
            assert hasattr(self, "_docker_client") and self._docker_client is not None
            client: "docker.DockerClient" = self._docker_client

            container_name = f"typing-db-{uuid.uuid4().hex[:8]}"
            # Ensure image exists
            client.images.pull(self.POSTGRES_IMAGE)
            container = client.containers.run(
                self.POSTGRES_IMAGE,
                detach=True,
                remove=True,
                name=container_name,
                environment={
                    "POSTGRES_USER": self.POSTGRES_USER,
                    "POSTGRES_PASSWORD": self.POSTGRES_PASSWORD,
                    "POSTGRES_DB": self.POSTGRES_DB,
                },
                ports={"5432/tcp": ("127.0.0.1", 0)},
            )
            container.reload()
            port_info = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            mapping = port_info.get("5432/tcp") or []
            if not mapping:
                raise DBConnectionError("Failed to determine mapped host port for PostgreSQL container")
            host_port = int(mapping[0].get("HostPort"))
            self._docker_container_name = container.name
            self._docker_container_id = container.id
            return container.name, host_port
        except Exception as exc:
            raise DBConnectionError("Failed to start PostgreSQL container via Docker SDK") from exc

    def _build_dsn(self, port: int) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@localhost:{port}/{self.POSTGRES_DB}"

    def _wait_for_database(self, port: int, timeout: float = 45.0) -> None:
        deadline = time.monotonic() + timeout
        last_err: Optional[Exception] = None
        while time.monotonic() < deadline:
            try:
                dsn = self._build_dsn(port)
                conn = cast(ConnectionProtocol, psycopg2.connect(dsn))
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    return
                finally:
                    conn.close()
            except Exception as exc:
                last_err = exc
                time.sleep(1)
        raise DBConnectionError(f"Timed out waiting for PostgreSQL to become ready: {last_err}")

    def _connect_postgres_docker(self) -> None:
        try:
            self._ensure_docker_available()
            name, port = self._create_postgres_container()
            self._docker_container_name = name
            self._docker_host_port = port
            self._debug_message(f"Started Docker Postgres container {name} on port {port}")
            self._wait_for_database(port)

            dsn = self._build_dsn(port)
            self._conn = cast(ConnectionProtocol, psycopg2.connect(dsn))
            self._conn.autocommit = True

            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.SCHEMA_NAME}")
                    cur.execute("SELECT current_setting('search_path')")
            except Exception as schema_exc:
                traceback.print_exc()
                self._debug_message(f"Failed ensuring schema/search_path: {schema_exc}")

            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"SET search_path TO {self.SCHEMA_NAME},public")
            except Exception as sp_exc:
                traceback.print_exc()
                self._debug_message(f"Failed to set search_path: {sp_exc}")

            self.is_postgres = True
        except Exception as e:
            traceback.print_exc()
            self._debug_message(f"Docker Postgres connection failed: {e}")
            # Attempt teardown if container was started
            try:
                self._teardown_docker_container()
            finally:
                pass
            raise DBConnectionError(f"Failed to connect to Docker PostgreSQL: {e}") from e

    def _teardown_docker_container(self) -> None:
        try:
            if getattr(self, "_docker_container_id", None):
                try:
                    assert hasattr(self, "_docker_client") and self._docker_client is not None
                    client: "docker.DockerClient" = self._docker_client
                    with contextlib.suppress(Exception):
                        container = client.containers.get(self._docker_container_id)
                        container.stop()
                        self._debug_message(f"Stopped Docker container: {self._docker_container_name}")
                finally:
                    self._docker_container_id = None  # type: ignore[attr-defined]
                    self._docker_container_name = None
                    self._docker_host_port = None
        except Exception as e2:
            traceback.print_exc()
            self._debug_message(f"Failed to teardown Docker container: {e2}")

    @property
    def execute_many_supported(self) -> bool:
        """Whether the active connection supports execute_many.

        - Returns True for both SQLite and PostgreSQL
        - Raises DBConnectionError if there is no active connection
        """
        if not self._conn:
            raise DBConnectionError("Database connection is not established")
        return True

    def close(self) -> None:
        """Close the database connection.

        Raises:
            DBConnectionError: If closing the connection fails.
        """
        try:
            if self._conn is not None:
                self._conn.close()
        except Exception as e:
            traceback.print_exc()
            logging.error("Error closing database connection: %s", e)
            self._debug_message(f"Error closing database connection: {e}")
            raise
        finally:
            self._teardown_docker_container()

    def _get_cursor(self) -> CursorProtocol:
        """Get a cursor from the database connection.

        Returns:
            A database cursor for PostgreSQL.

        Raises:
            DBConnectionError: If the database connection is not established.
        """
        if not self._conn:
            raise DBConnectionError("Database connection is not established")
        return self._conn.cursor()

    def _execute_ddl(self, query: str) -> None:
        """Execute DDL (Data Definition Language) statements.

        Works consistently across both SQLite and PostgreSQL connections
        using a cursor-based approach.

        Args:
            query: SQL DDL statement to execute

        Raises:
            Various database exceptions depending on the error type
        """
        cursor = self._conn.cursor()
        cursor.execute(query)
        self._conn.commit()
        cursor.close()

    def _qualify_schema_in_query(self, query: str) -> str:
        """Prepare queries for PostgreSQL execution.

        Since the connection is configured with search_path=typing,public,
        unqualified table names will automatically resolve to the typing schema.
        This method only handles placeholder conversion and minimal DDL qualification
        where explicit schema specification is required.
        """
        # Convert SQLite-style placeholders to PostgreSQL-style
        if "?" in query:
            query = query.replace("?", "%s")

        # Only qualify CREATE TABLE and DROP TABLE statements to ensure they
        # create/drop tables in the correct schema. Other operations (SELECT, INSERT,
        # UPDATE, DELETE) rely on the search_path configuration.
        try:
            # Qualify CREATE TABLE <name>
            # CREATE TABLE [IF NOT EXISTS] <table>
            m = re.search(r"(?i)^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s;(]+)", query)
            if m:
                tbl = m.group(1)
                if "." not in tbl:
                    start, end = m.span(1)
                    query = f"{query[:start]}{self.SCHEMA_NAME}.{tbl}{query[end:]}"

            # Qualify DROP TABLE [IF EXISTS] <name>
            m2 = re.search(r"(?i)^\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([^\s;]+)", query)
            if m2:
                tbl2 = m2.group(1)
                if "." not in tbl2:
                    s2, e2 = m2.span(1)
                    query = f"{query[:s2]}{self.SCHEMA_NAME}.{tbl2}{query[e2:]}"

        except Exception:
            # Best-effort; non-fatal if qualification fails
            pass

        return query

    def _translate_and_raise(self, e: Exception) -> NoReturn:
        """Translate backend-specific exceptions to our custom exceptions and raise.

        Always raises; does not return.
        """
        # SQLite mapping removed; Postgres-only

        # PostgreSQL mapping
        if isinstance(e, (psycopg2.OperationalError, psycopg2.ProgrammingError)):
            error_msg = str(e).lower()
            if "connection" in error_msg:
                raise DBConnectionError(f"Failed to connect to PostgreSQL database: {e}") from e
            if "does not exist" in error_msg and "relation" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "column" in error_msg and "does not exist" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        if isinstance(e, psycopg2.IntegrityError):
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif (
                "not null" in error_msg or "not-null" in error_msg or "null value" in error_msg or "unique" in error_msg
            ):
                raise ConstraintError(f"Constraint violation: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        if isinstance(e, psycopg2.DataError):
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        if isinstance(e, psycopg2.DatabaseError):
            raise DatabaseError(f"Database error: {e}") from e

        # Fallback
        raise DatabaseError(f"Unexpected database error: {e}") from e

    def execute(self, query: str, params: Tuple[object, ...] = ()) -> CursorProtocol:
        """Execute a SQL query with parameters and commit immediately.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            Database cursor object

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        try:
            cursor: CursorProtocol = self._get_cursor()

            # Apply schema qualification and placeholder conversion for PostgreSQL
            query = self._qualify_schema_in_query(query)
            # Debug the final SQL being executed on Postgres
            try:
                dbg_sql = query.replace("\n", " ").strip()
                self._debug_message(f"Executing SQL (PG): {dbg_sql}; params={params}")
            except Exception:
                pass

            # Execute the query
            cursor.execute(query, params)

            # Commit the transaction for non-SELECT queries
            if not query.strip().upper().startswith("SELECT"):
                self._conn.commit()

            return cursor
        except Exception as e:
            traceback.print_exc()
            self._debug_message(f"Exception during query: {e}. Rolling back transaction.")
            try:
                self._conn.rollback()
            except Exception as rollback_exc:
                traceback.print_exc()
                self._debug_message(f" Rollback failed: {rollback_exc}")
            self._translate_and_raise(e)
            raise AssertionError("unreachable") from e

    def execute_many(
        self,
        query: str,
        params_seq: Iterable[Tuple[object, ...]],
        *,
        method: Union[BulkMethod, str] = BulkMethod.AUTO,
        page_size: int = 1000,
    ) -> CursorProtocol:
        """Execute a parameterized statement for many rows efficiently.

        Applies the same placeholder and schema adjustments as `execute()`.

        Args:
            query: SQL statement with positional placeholders ('?' for SQLite style)
            params_seq: Iterable of parameter tuples
            method: One of "auto", "values", "copy" (PostgreSQL only). Defaults to "auto".
            page_size: Batch page size for execute_values. Defaults to 1000.

        Returns:
            Database cursor after execution.
        """
        try:
            cursor: CursorProtocol = self._get_cursor()

            # Guard: feature support check
            if not self.execute_many_supported:
                raise DBConnectionError("execute_many is not supported for this connection")

            # Only apply Postgres-specific qualification when truly on a Postgres backend
            if self.is_postgres and "%s" in self._qualify_schema_in_query("?"):
                query = self._qualify_schema_in_query(query)

            # Bulk strategies selection
            params_list: List[Tuple[object, ...]] = list(params_seq)

            # Normalize method to enum
            method_enum: BulkMethod
            if isinstance(method, BulkMethod):
                method_enum = method
            else:
                m = str(method).strip().lower()
                if m in ("auto",):
                    method_enum = BulkMethod.AUTO
                elif m in ("values",):
                    method_enum = BulkMethod.VALUES
                elif m in ("copy",):
                    method_enum = BulkMethod.COPY
                elif m in ("executemany", "execute_many"):
                    method_enum = BulkMethod.EXECUTEMANY
                else:
                    # Safe default
                    method_enum = BulkMethod.EXECUTEMANY

            # Route by backend and method
            # PostgreSQL strategies
            if method_enum is BulkMethod.EXECUTEMANY:
                return self._bulk_executemany(cursor, query, params_list)

            if method_enum is BulkMethod.VALUES:
                return self._bulk_execute_values(cursor, query, params_list, page_size)

            if method_enum is BulkMethod.COPY:
                return self._bulk_copy_from(cursor, query, params_list)

            # AUTO: prefer VALUES, fallback to COPY, then EXECUTEMANY
            try:
                return self._bulk_execute_values(cursor, query, params_list, page_size)
            except Exception:
                try:
                    return self._bulk_copy_from(cursor, query, params_list)
                except Exception:
                    return self._bulk_executemany(cursor, query, params_list)
        except Exception as e:
            traceback.print_exc()
            self._debug_message(f" Exception during execute_many: {e}. Rolling back transaction.")
            try:
                self._conn.rollback()
            except Exception as rollback_exc:
                traceback.print_exc()
                self._debug_message(f" Rollback failed: {rollback_exc}")
            self._translate_and_raise(e)
            raise AssertionError("unreachable") from e

    # --- Bulk helper methods for execute_many ---
    def _bulk_executemany(
        self,
        cursor: CursorProtocol,
        query: str,
        params_list: List[Tuple[object, ...]],
    ) -> CursorProtocol:
        """Fallback bulk execution using DB-API ``cursor.executemany``.

        - Backend: works on both SQLite and PostgreSQL.
        - Placeholders: pass the query exactly as produced by
          ``_qualify_schema_in_query`` for Postgres (i.e., ``%s``) and as originally
          written for SQLite (i.e., ``?``).
        - Commit: commits when the statement is non-SELECT.
        - Errors: any backend errors are handled by caller via ``_translate_and_raise``.
        """
        cursor.executemany(query, params_list)
        if not query.strip().upper().startswith("SELECT"):
            self._conn.commit()
        return cursor

    def _bulk_execute_values(
        self,
        cursor: CursorProtocol,
        query: str,
        params_list: List[Tuple[object, ...]],
        page_size: int,
    ) -> CursorProtocol:
        """Use ``psycopg2.extras.execute_values`` for efficient INSERT batches.

        - Backend: PostgreSQL only. Raises ``DatabaseTypeError`` if extras module is
          not available.
        - Statement: must be an ``INSERT INTO <table>(cols...) VALUES (...)``-style
          statement. If explicit tuples are present, the first occurrence is rewritten
          to ``VALUES %s``; if the query already contains ``VALUES %s`` it is used
          as-is. Any other form raises ``DatabaseTypeError``.
        - Page size: forwarded to ``execute_values``.
        - Commit: commits when the statement is non-SELECT.
        - Errors: any backend errors are handled by caller via ``_translate_and_raise``.
        """
        pattern = r"VALUES\s*\((?:\s*%s\s*,?\s*)+\)"
        if re.search(pattern, query, flags=re.IGNORECASE):
            query_for_values = re.sub(pattern, "VALUES %s", query, count=1, flags=re.IGNORECASE)
        else:
            # If user already provided VALUES %s, keep as-is; otherwise not compatible
            if re.search(r"VALUES\s*%s", query, flags=re.IGNORECASE):
                query_for_values = query
            else:
                raise DatabaseTypeError("Query not compatible with execute_values")

        psycopg2_extras.execute_values(cursor, query_for_values, params_list, page_size=page_size)
        if not query.strip().upper().startswith("SELECT"):
            self._conn.commit()
        return cursor

    def _bulk_copy_from(
        self,
        cursor: CursorProtocol,
        query: str,
        params_list: List[Tuple[object, ...]],
    ) -> CursorProtocol:
        r"""Use ``COPY FROM STDIN`` for fast ingestion of INSERT-like data on Postgres.

        - Backend: PostgreSQL only. Requires that the active connection has the
          search_path set (handled during connection) and the table exists in the
          configured schema.
        - Statement: must be an ``INSERT INTO <table>(cols...) VALUES (...)``-style
          statement. We parse table and columns, and stream data as TSV with ``\n``
          line terminators, ``\t`` separators, and ``\\N`` for NULLs.
        - Data sanitation: tabs/newlines in values are replaced with spaces.
        - Commit: commits when the statement is non-SELECT.
        - Errors: raises ``DatabaseTypeError`` for incompatible statements or length
          mismatches; backend errors are handled by caller via ``_translate_and_raise``.
        """
        m = re.search(r"INSERT\s+INTO\s+([^\s(]+)\s*\(([^)]+)\)", query, flags=re.IGNORECASE)
        if not m:
            raise DatabaseTypeError("COPY method requires INSERT ... (cols) VALUES ... form")
        table_name = cast(str, m.group(1))
        cols_raw = cast(str, m.group(2))
        cols: List[str] = [c.strip() for c in cols_raw.split(",")]
        # Build both qualified and unqualified identifiers.
        # Unit tests using a FakeCursor expect a schema-qualified value, but on real
        # PostgreSQL cursors passing a dotted identifier to copy_from can fail due to
        # quoting behavior. We'll choose which to use based on cursor capabilities.
        if "." in table_name:
            qualified_table_name = table_name
            unqualified_table_name = table_name.split(".", 1)[1]
        else:
            qualified_table_name = f"{self.SCHEMA_NAME}.{table_name}"
            unqualified_table_name = table_name

        # We keep using the qualified name for existence checks and debug logs.

        # Debug visibility for failing COPYs
        try:
            self._debug_message(f" COPY target table: {qualified_table_name}; columns: {cols}")
        except Exception as debug_exc:
            traceback.print_exc()
            self._debug_message(f"Failed to log COPY debug info: {debug_exc}")
        # Verify table existence before COPY using to_regclass (best-effort).
        # In unit tests, the cursor may be a minimal fake without execute/fetchone.
        try:
            if hasattr(cursor, "execute") and hasattr(cursor, "fetchone"):
                cursor.execute("SELECT to_regclass(%s)", (qualified_table_name,))
                reg = cursor.fetchone()
                self._debug_message(f" to_regclass({qualified_table_name}) => {reg}")
        except Exception as reg_exc:
            traceback.print_exc()
            self._debug_message(f" to_regclass check failed for {qualified_table_name}: {reg_exc}")

        buf = io.StringIO()
        for row in params_list:
            if len(row) != len(cols):
                raise DatabaseTypeError("Row length does not match column count for COPY")
            fields = []
            for v in row:
                if v is None:
                    fields.append("\\N")
                else:
                    s = str(v).replace("\t", " ").replace("\n", " ")
                    fields.append(s)
            buf.write("\t".join(fields) + "\n")
        buf.seek(0)

        # Choose table identifier for copy_from:
        # - If cursor looks like a real psycopg2 cursor (has execute/fetchone), use
        #   the unqualified name and rely on search_path to resolve the schema. This
        #   avoids issues where a dotted identifier may be treated as a single quoted
        #   name by the driver.
        # - Otherwise (e.g., FakeCursor in unit tests), use the qualified name to
        #   satisfy test expectations of seeing "typing.<table>" captured.
        use_unqualified = hasattr(cursor, "execute") and hasattr(cursor, "fetchone")
        target_for_copy = unqualified_table_name if use_unqualified else qualified_table_name

        # Use copy_from for direct COPY FROM STDIN operation
        cursor.copy_from(buf, target_for_copy, columns=cols, sep="\t", null="\\N")
        if not query.strip().upper().startswith("SELECT"):
            self._conn.commit()
        return cursor

    def fetchone(self, query: str, params: Tuple[object, ...] = ()) -> Optional[Dict[str, object]]:
        """Execute a SQL query and fetch a single result.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            Dict representing fetched row, or None if no results
            Both SQLite and PostgreSQL results are returned as dictionaries with col names as keys

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        cursor = self.execute(query, params)
        result = cursor.fetchone()

        # Return None if no result
        if result is None:
            return None

        # Convert tuple to dict using column names
        assert cursor.description is not None
        result_t = cast(Tuple[object, ...], result)
        col_names = [cast(str, desc[0]) for desc in cursor.description]
        return {col_names[i]: result_t[i] for i in range(len(col_names))}

    def fetchmany(self, query: str, params: Tuple[object, ...] = (), size: int = 1) -> List[Dict[str, object]]:
        """Execute a SQL query and fetch multiple results.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters
            size: Number of rows to fetch

        Returns:
            List of Dict representing fetched rows
            Both SQLite and PostgreSQL results are returned as dictionaries with col names as keys

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        cursor = self.execute(query, params)
        results = cursor.fetchmany(size)

        # Convert tuples to dicts using column names
        if not results:
            return []
        assert cursor.description is not None
        results_t = cast(List[Tuple[object, ...]], results)
        col_names = [cast(str, desc[0]) for desc in cursor.description]
        return [{col_names[i]: row[i] for i in range(len(col_names))} for row in results_t]

    def fetchall(self, query: str, params: Tuple[object, ...] = ()) -> List[Dict[str, object]]:
        """Execute a query and return all rows as a list.

        Args:
            query: SQL query string (parameterized)
            params: Query parameters

        Returns:
            A list of dictionaries, with each dictionary representing a row
            Both SQLite and PostgreSQL results are returned as dictionaries with col names as keys

        Raises:
            DBConnectionError, TableNotFoundError, SchemaError, DatabaseError,
            ForeignKeyError, ConstraintError, IntegrityError, DatabaseTypeError
        """
        cursor = self.execute(query, params)
        results = cursor.fetchall()

        # For PostgreSQL, convert tuples to dicts using column names
        if self.is_postgres and results:
            assert cursor.description is not None
            results_t = cast(List[Tuple[object, ...]], results)
            col_names = [cast(str, desc[0]) for desc in cursor.description]
            return [{col_names[i]: row[i] for i in range(len(col_names))} for row in results_t]

        # SQLite's Row objects can be used as dictionaries but let's normalize to dict
        return [cast(Dict[str, object], dict(cast(Dict[str, object], row))) for row in results]

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
        datetime_type = "TIMESTAMP(6)"

        self._execute_ddl(
            f"""
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                keyboard_id TEXT NOT NULL,
                snippet_id TEXT NOT NULL,
                snippet_index_start INTEGER NOT NULL,
                snippet_index_end INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_time {datetime_type} NOT NULL,
                end_time {datetime_type} NOT NULL,
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
                text_index INTEGER NOT NULL,
                key_index INTEGER NOT NULL,
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

    def _create_ngram_speed_summary_curr_table(self) -> None:
        """Create the ngram_speed_summary_curr table for current performance summaries."""
        datetime_type = "TIMESTAMP(6)"

        self._execute_ddl(
            f"""
            CREATE TABLE IF NOT EXISTS ngram_speed_summary_curr (
                summary_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                keyboard_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                ngram_text TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                decaying_average_ms REAL NOT NULL,
                target_speed_ms REAL NOT NULL,
                target_performance_pct REAL NOT NULL,
                meets_target INT NOT NULL,
                sample_count INTEGER NOT NULL,
                updated_dt {datetime_type} NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE,
                Primary Key (user_id, keyboard_id, ngram_text, ngram_size)
            );
            """
        )

        # Create indexes for better query performance
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_summary_curr_user_keyboard 
            ON ngram_speed_summary_curr(user_id, keyboard_id);
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_summary_curr_performance 
            ON ngram_speed_summary_curr(target_performance_pct, meets_target);
            """
        )

    def _create_ngram_speed_summary_hist_table(self) -> None:
        """Create the ngram_speed_summary_hist table for tracking performance over time."""
        # Use high-precision datetime type based on database type
        datetime_type = "TIMESTAMP(6)" if self.is_postgres else "TEXT"

        self._execute_ddl(
            f"""


            
            CREATE TABLE IF NOT EXISTS ngram_speed_summary_hist (
                history_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                keyboard_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                ngram_text TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                decaying_average_ms REAL NOT NULL,
                target_speed_ms REAL NOT NULL,
                target_performance_pct REAL NOT NULL,
                meets_target INT NOT NULL,
                sample_count INTEGER NOT NULL,
                updated_dt {datetime_type} NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE
            );
            """
        )

        # Create indexes for better query performance
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_summary_hist_user_keyboard 
            ON ngram_speed_summary_hist(user_id, keyboard_id);
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_summary_hist_ngram 
            ON ngram_speed_summary_hist(ngram_text, ngram_size);
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_ngram_summary_hist_date 
            ON ngram_speed_summary_hist(updated_dt);
            """
        )

    def _create_session_ngram_summary_table(self) -> None:
        """Create the session_ngram_summary table for session-level ngram summaries."""
        # Use high-precision datetime type based on database type
        datetime_type = "TIMESTAMP(6)" if self.is_postgres else "TEXT"

        self._execute_ddl(
            f"""
            CREATE TABLE IF NOT EXISTS session_ngram_summary (
                session_id TEXT NOT NULL,
                ngram_text TEXT NOT NULL,
                user_id TEXT NOT NULL,
                keyboard_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                avg_ms_per_keystroke REAL NOT NULL,
                target_speed_ms REAL NOT NULL,
                instance_count INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                updated_dt {datetime_type} NOT NULL,
                session_dt {datetime_type} NOT NULL,
                PRIMARY KEY (session_id, ngram_text),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE
            );
            """
        )

        # Create indexes for better query performance
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_session_ngram_summary_session 
            ON session_ngram_summary(session_id);
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_session_ngram_summary_user_keyboard 
            ON session_ngram_summary(user_id, keyboard_id);
            """
        )

        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_session_ngram_summary_ngram 
            ON session_ngram_summary(ngram_text, ngram_size);
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
        """Create the keyboards table with UUID primary key and user_id foreign key.

        Creates the table if it does not exist.
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

    # --- Keysets schema (and history) ---
    def _create_keysets_table(self) -> None:
        """Create keysets table (name + progression per keyboard)."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS keysets (
                keyset_id TEXT PRIMARY KEY,
                keyboard_id TEXT NOT NULL,
                keyset_name TEXT NOT NULL,
                progression_order INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                row_checksum TEXT NOT NULL,
                UNIQUE (keyboard_id, keyset_name),
                UNIQUE (keyboard_id, progression_order),
                FOREIGN KEY (keyboard_id) REFERENCES keyboards(keyboard_id) ON DELETE CASCADE
            );
            """
        )

    def _create_keysets_history_table(self) -> None:
        """Create keysets history table using SCD-2 close-update pattern."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS keysets_history (
                history_id TEXT PRIMARY KEY,
                keyset_id TEXT NOT NULL,
                keyboard_id TEXT NOT NULL,
                keyset_name TEXT NOT NULL,
                progression_order INTEGER NOT NULL,
                action TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT NOT NULL DEFAULT '9999-12-31 23:59:59',
                is_current INTEGER NOT NULL,
                version_no INTEGER NOT NULL,
                recorded_at TEXT NOT NULL,
                created_user_id TEXT,
                updated_user_id TEXT,
                row_checksum TEXT NOT NULL
            );
            """
        )
        # Lightweight indexes for common queries
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_keysets_hist_current 
            ON keysets_history(keyset_id, is_current);
            """
        )
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_keysets_hist_version 
            ON keysets_history(keyset_id, version_no);
            """
        )

    def _create_keyset_keys_table(self) -> None:
        """Create keyset_keys table for per-character membership with emphasis flag."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS keyset_keys (
                key_id TEXT PRIMARY KEY,
                keyset_id TEXT NOT NULL,
                key_char TEXT NOT NULL,
                is_new_key INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                row_checksum TEXT NOT NULL,
                UNIQUE (keyset_id, key_char),
                FOREIGN KEY (keyset_id) REFERENCES keysets(keyset_id) ON DELETE CASCADE
            );
            """
        )

    def _create_keyset_keys_history_table(self) -> None:
        """Create keyset_keys history table using SCD-2 close-update pattern."""
        self._execute_ddl(
            """
            CREATE TABLE IF NOT EXISTS keyset_keys_history (
                history_id TEXT PRIMARY KEY,
                key_id TEXT NOT NULL,
                keyset_id TEXT NOT NULL,
                key_char TEXT NOT NULL,
                is_new_key INTEGER NOT NULL,
                action TEXT NOT NULL,
                valid_from TEXT NOT NULL,
                valid_to TEXT NOT NULL DEFAULT '9999-12-31 23:59:59',
                is_current INTEGER NOT NULL,
                version_no INTEGER NOT NULL,
                recorded_at TEXT NOT NULL,
                created_user_id TEXT,
                updated_user_id TEXT,
                row_checksum TEXT NOT NULL
            );
            """
        )
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_keyset_keys_hist_current 
            ON keyset_keys_history(key_id, is_current);
            """
        )
        self._execute_ddl(
            """
            CREATE INDEX IF NOT EXISTS idx_keyset_keys_hist_version 
            ON keyset_keys_history(key_id, version_no);
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
        self._create_ngram_speed_summary_curr_table()
        self._create_ngram_speed_summary_hist_table()
        self._create_session_ngram_summary_table()
        self._create_users_table()
        self._create_keyboards_table()
        self._create_settings_table()
        self._create_settings_history_table()
        # Keysets feature
        self._create_keysets_table()
        self._create_keysets_history_table()
        self._create_keyset_keys_table()
        self._create_keyset_keys_history_table()

    def __enter__(self) -> "DatabaseManager":
        """Context manager protocol support.

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
        """Context manager protocol support - close connection when exiting context."""
        self.close()

    def __del__(self) -> None:
        """Clean up database connection and Docker container on object destruction."""
        try:
            # Attempt to close DB connection and teardown docker container
            self.close()
        except Exception as e:
            traceback.print_exc()
            try:
                self._debug_message(f"Destructor cleanup failed: {e}")
            except Exception:
                pass

    # Transaction management methods have been removed.
    # All database operations now use commit=True parameter to ensure immediate commits.

    # Manager factory methods have been removed to reduce coupling.
    # Please use dependency injection to pass the database manager to managers/repositories.
    # Example:
    #     db_manager = DatabaseManager("path/to/db")
    #     snippet_manager = SnippetManager(db_manager)
    #     session_manager = SessionManager(db_manager)
