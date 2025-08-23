"""
Tests for the DatabaseManager class.

This module contains comprehensive tests for the DatabaseManager class,
verifying its functionality, error handling, and edge cases.
"""

import os
import tempfile
from typing import Any, Generator, Iterable, Optional, TextIO, Tuple, cast

import pytest

from db.database_manager import (
    CLOUD_DEPENDENCIES_AVAILABLE,
    BulkMethod,
    ConnectionType,
    DatabaseManager,
)
from db.database_manager import (
    CursorProtocol as DBCursorProtocol,
)
from db.exceptions import (
    ConstraintError,
    DatabaseError,
    DBConnectionError,
    ForeignKeyError,
    SchemaError,
    TableNotFoundError,
)
from helpers.debug_util import DebugUtil

# Test data constants
TEST_TABLE_NAME = "test_table"
TEST_DATA = [
    (1, "Alice", 30, "alice@example.com"),
    (2, "Bob", 25, "bob@example.com"),
    (3, "Charlie", 35, "charlie@example.com"),
]


@pytest.fixture(scope="function")
def temp_db_path() -> Generator[str, None, None]:
    """
    Create a temporary database file for testing.

    Yields:
        str: Path to the temporary database file

    The database file is automatically deleted after the test completes.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    yield db_path

    # Clean up the temporary file
    try:
        os.unlink(db_path)
    except (OSError, PermissionError):
        pass


@pytest.fixture(scope="function")
def db_manager(temp_db_path: str) -> DatabaseManager:
    """
    Create a DatabaseManager instance with a temporary database.

    Args:
        temp_db_path: Path to the temporary database file

    Returns:
        DatabaseManager: A new DatabaseManager instance
    """
    # Create DebugUtil in loud mode for tests
    debug_util = DebugUtil()
    debug_util._mode = "loud"
    
    return DatabaseManager(temp_db_path, debug_util=debug_util)


@pytest.fixture(scope="function")
def initialized_db(db_manager: DatabaseManager) -> DatabaseManager:
    """
    Create a database with a test table and sample data.

    Args:
        db_manager: DatabaseManager instance

    Returns:
        DatabaseManager: The same DatabaseManager instance with test data
    """
    # Create a test table
    db_manager.execute(
        f"""
        CREATE TABLE {TEST_TABLE_NAME} (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT UNIQUE
        )
        """
    )

    # Insert test data
    for row in TEST_DATA:
        db_manager.execute(f"INSERT INTO {TEST_TABLE_NAME} VALUES (?, ?, ?, ?)", row)

    return db_manager


class TestDatabaseManagerInitialization:
    """Test cases for DatabaseManager initialization and basic functionality."""

    def test_init_with_temp_file(self, temp_db_path: str) -> None:
        """Test initialization with a temporary file database."""
        debug_util = DebugUtil()
        debug_util._mode = "loud"
        with DatabaseManager(temp_db_path, debug_util=debug_util) as db:
            assert db is not None
            # Verify the file was created
            assert os.path.exists(temp_db_path)

    def test_init_with_invalid_path_raises_error(self) -> None:
        """Test that an invalid path raises a DBConnectionError."""
        debug_util = DebugUtil()
        debug_util._mode = "loud"
        with pytest.raises(DBConnectionError):
            DatabaseManager("/invalid/path/database.db", debug_util=debug_util)

    def test_context_manager_cleans_up(self, temp_db_path: str) -> None:
        """Test that the context manager properly cleans up resources."""
        debug_util = DebugUtil()
        debug_util._mode = "loud"
        with DatabaseManager(temp_db_path, debug_util=debug_util) as db:
            # Do something with the database
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

        # The database file should still exist
        assert os.path.exists(temp_db_path)

        # But we shouldn't be able to use the connection anymore
        with pytest.raises(DatabaseError):
            db.execute("SELECT 1")


class TestDatabaseOperations:
    """Test cases for database operations (execute, fetchone, fetchall)."""

    def test_execute_create_table(self, db_manager: DatabaseManager) -> None:
        """Test executing a CREATE TABLE statement."""
        db_manager.execute(
            f"""
            CREATE TABLE {TEST_TABLE_NAME} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        # Verify the table was created by querying sqlite_master
        result = db_manager.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TEST_TABLE_NAME,)
        )
        assert result is not None
        assert result["name"] == TEST_TABLE_NAME

    def test_execute_insert(self, initialized_db: DatabaseManager) -> None:
        """Test executing an INSERT statement."""
        # Insert a new row
        initialized_db.execute(
            f"INSERT INTO {TEST_TABLE_NAME} (id, name, age, email) VALUES (?, ?, ?, ?)",
            (4, "David", 40, "david@example.com"),
        )

        # Verify the row was inserted
        result = initialized_db.fetchone(
            f"SELECT name, age, email FROM {TEST_TABLE_NAME} WHERE id = ?", (4,)
        )
        assert result is not None
        assert result["name"] == "David"
        assert result["age"] == 40
        assert result["email"] == "david@example.com"

    def test_fetchone_returns_none_for_no_results(self, initialized_db: DatabaseManager) -> None:
        """Test that fetchone returns None when no results are found."""
        result = initialized_db.fetchone(f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?", (999,))
        assert result is None

    def test_fetchall_returns_all_results(self, initialized_db: DatabaseManager) -> None:
        """Test that fetchall returns all matching rows."""
        results = initialized_db.fetchall(f"SELECT * FROM {TEST_TABLE_NAME} ORDER BY id")

        assert len(results) == len(TEST_DATA)
        for i, row in enumerate(results):
            assert row["id"] == TEST_DATA[i][0]
            assert row["name"] == TEST_DATA[i][1]
            assert row["age"] == TEST_DATA[i][2]
            assert row["email"] == TEST_DATA[i][3]

    def test_fetchall_returns_empty_list_for_no_results(
        self, initialized_db: DatabaseManager
    ) -> None:
        """Test that fetchall returns an empty list when no results are found."""
        results = initialized_db.fetchall(f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?", (999,))
        assert results == []


class TestErrorHandling:
    """Test cases for error handling in DatabaseManager."""

    def test_table_not_found_error(self, db_manager: DatabaseManager) -> None:
        """Test that querying a non-existent table raises TableNotFoundError."""
        with pytest.raises(TableNotFoundError):
            db_manager.execute("SELECT * FROM non_existent_table")

    def test_schema_error(self, initialized_db: DatabaseManager) -> None:
        """Test that querying with invalid column names raises SchemaError."""
        with pytest.raises(SchemaError):
            initialized_db.execute(f"SELECT non_existent_column FROM {TEST_TABLE_NAME}")

    def test_foreign_key_error(self, db_manager: DatabaseManager) -> None:
        """Test that foreign key violations raise ForeignKeyError."""
        # Create tables with foreign key relationship
        db_manager.execute("""
            CREATE TABLE parent (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        db_manager.execute("""
            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER,
                name TEXT,
                FOREIGN KEY (parent_id) REFERENCES parent(id)
            )
        """)

        # Try to insert into child with invalid parent_id
        with pytest.raises(ForeignKeyError):
            db_manager.execute("INSERT INTO child (id, parent_id, name) VALUES (1, 999, 'test')")

    def test_constraint_error_unique(self, db_manager: DatabaseManager) -> None:
        """Test that unique constraint violations raise ConstraintError."""
        # Create table with unique constraint
        db_manager.execute("""
            CREATE TABLE test_unique (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE
            )
        """)

        # Insert first row
        db_manager.execute("INSERT INTO test_unique (id, email) VALUES (1, 'test@example.com')")

        # Try to insert duplicate email
        with pytest.raises(ConstraintError):
            db_manager.execute("INSERT INTO test_unique (id, email) VALUES (2, 'test@example.com')")

    def test_constraint_error_not_null(self, db_manager: DatabaseManager) -> None:
        """Test that NOT NULL constraint violations raise ConstraintError."""
        # Create table with NOT NULL constraint
        db_manager.execute("""
            CREATE TABLE test_not_null (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        # Try to insert NULL into NOT NULL column
        with pytest.raises(ConstraintError):
            db_manager.execute("INSERT INTO test_not_null (id) VALUES (1)")


class TestExecuteMany:
    """Comprehensive tests for DatabaseManager.execute_many() on SQLite and Postgres."""

    TEST_TABLE = "tt_execmany_test"

    def _create_table(self, db: DatabaseManager) -> None:
        # Mixed field types; portable across SQLite and Postgres
        db.execute(
            f"""
            CREATE TABLE {self.TEST_TABLE} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                score REAL,
                created_at TEXT,
                email TEXT UNIQUE,
                flag INTEGER
            )
            """
        )

    def _drop_table(self, db: DatabaseManager) -> None:
        try:
            db.execute(f"DROP TABLE {self.TEST_TABLE}")
        except Exception:
            pass

    @pytest.fixture()
    def sqlite_db(self, temp_db_path: str) -> Generator[DatabaseManager, None, None]:
        debug_util = DebugUtil()
        debug_util._mode = "loud"
        with DatabaseManager(temp_db_path, debug_util=debug_util) as db:
            self._drop_table(db)
            self._create_table(db)
            yield db
            self._drop_table(db)

    def _cloud_available(self) -> bool:
        # Allow cloud tests only if deps exist and env signals intent
        # return CLOUD_DEPENDENCIES_AVAILABLE and (
        #     os.environ.get("RUN_CLOUD_DB_TESTS", "0") == "1"
        # )
        return CLOUD_DEPENDENCIES_AVAILABLE

    @pytest.fixture()
    def cloud_db(self) -> Generator[DatabaseManager, None, None]:
        if not self._cloud_available():
            pytest.skip("Cloud DB tests disabled or dependencies unavailable")
        debug_util = DebugUtil()
        debug_util._mode = "loud"
        with DatabaseManager(None, connection_type=ConnectionType.CLOUD, debug_util=debug_util) as db:
            self._drop_table(db)
            self._create_table(db)
            yield db
            self._drop_table(db)

    # -------- SQLite positive and error scenarios --------

    def test_execute_many_insert_success_sqlite(self, sqlite_db: DatabaseManager) -> None:
        rows = [
            (1, "Alice", 12.5, "2025-08-09T07:21:55-04:00", "a@example.com", 1),
            (2, "Bob", 99.9, "2025-08-09T07:21:56-04:00", "b@example.com", 0),
            (3, "Cara", None, None, None, None),
        ]
        sqlite_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        results = sqlite_db.fetchall(
            f"SELECT id, name, score, created_at, email, flag FROM {self.TEST_TABLE} ORDER BY id"
        )
        assert [tuple(r.values()) for r in results] == rows

    def test_execute_many_pk_violation_sqlite(self, sqlite_db: DatabaseManager) -> None:
        sqlite_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
            [(1, "A")],
        )
        with pytest.raises(ConstraintError):
            sqlite_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
                [(1, "Dup")],
            )

    def test_execute_many_unique_violation_sqlite(self, sqlite_db: DatabaseManager) -> None:
        sqlite_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, email) VALUES (?, ?, ?)",
            [(10, "X", "x@example.com")],
        )
        with pytest.raises(ConstraintError):
            sqlite_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name, email) VALUES (?, ?, ?)",
                [(11, "Y", "x@example.com")],
            )

    def test_execute_many_not_null_violation_sqlite(self, sqlite_db: DatabaseManager) -> None:
        with pytest.raises(ConstraintError):
            sqlite_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
                [(20, None)],  # wrong arity and None for NOT NULL
            )

    def test_execute_many_table_not_found_sqlite(self, sqlite_db: DatabaseManager) -> None:
        with pytest.raises(TableNotFoundError):
            sqlite_db.execute_many(
                "INSERT INTO missing_table (id) VALUES (?)",
                [(1,)],
            )

    # -------- Cloud (Postgres) scenarios, conditional --------

    def test_execute_many_insert_success_cloud(self, cloud_db: DatabaseManager) -> None:
        rows = [
            (100, "P-Alice", 1.25, "2025-08-09T07:21:55Z", "pa@example.com", 1),
            (101, "P-Bob", 2.5, "2025-08-09T07:21:56Z", "pb@example.com", 0),
        ]
        cloud_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        results = cloud_db.fetchall(
            f"SELECT id, name, score, created_at, email, flag FROM {self.TEST_TABLE} ORDER BY id"
        )
        # Postgres returns decimals/floats; compare converted tuples
        got = [
            (
                r["id"],
                r["name"],
                float(r["score"]) if r["score"] is not None else None,
                r["created_at"],
                r["email"],
                r["flag"],
            )
            for r in results
        ]
        exp = [
            (r[0], r[1], float(r[2]) if r[2] is not None else None, r[3], r[4], r[5]) for r in rows
        ]
        assert got == exp

    def test_execute_many_method_options_sqlite(self, sqlite_db: DatabaseManager) -> None:
        rows = [
            (11, "M1", 1.0, None, None, None),
            (12, "M2", 2.0, None, None, None),
        ]
        # Explicit EXECUTEMANY
        sqlite_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
            method=BulkMethod.EXECUTEMANY,
        )
        got = sqlite_db.fetchall(
            f"SELECT id, name, score, created_at, email, flag FROM {self.TEST_TABLE} WHERE id IN (?, ?) ORDER BY id",
            (11, 12),
        )
        assert [tuple(r.values()) for r in got] == rows

        # AUTO should also work (falls back to executemany on SQLite)
        rows2 = [
            (13, "M3", None, None, None, None),
        ]
        sqlite_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows2,
            method=BulkMethod.AUTO,
        )
        got2 = sqlite_db.fetchall(
            f"SELECT id, name, score, created_at, email, flag FROM {self.TEST_TABLE} WHERE id = ?",
            (13,),
        )
        assert [tuple(r.values()) for r in got2] == rows2

    @pytest.mark.parametrize(
        "method,base_id,rows",
        [
            (BulkMethod.VALUES, 300, [(300, "V1", 1.25, None, None, None), (301, "V2", 2.5, None, None, None)]),
            (BulkMethod.COPY, 302, [(302, "C1", None, None, None, None), (303, "C2", None, None, None, None)]),
            (BulkMethod.EXECUTEMANY, 304, [(304, "E1", None, None, None, None)]),
            (BulkMethod.AUTO, 305, [(305, "A1", None, None, None, None)]),
        ],
    )
    def test_execute_many_method_options_cloud(
        self, cloud_db: DatabaseManager, method: BulkMethod, base_id: int, rows: list[tuple]
    ) -> None:
        # Ensure clean slate for these IDs
        max_id = max(r[0] for r in rows) + 1
        cloud_db.execute(
            f"DELETE FROM {self.TEST_TABLE} WHERE id >= %s AND id < %s",
            (base_id, max_id),
        )

        cloud_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
            method=method,
        )

        ids = [r[0] for r in rows]
        placeholders = ", ".join(["%s"] * len(ids))
        results = cloud_db.fetchall(
            f"SELECT id, name FROM {self.TEST_TABLE} WHERE id IN ({placeholders}) ORDER BY id",
            tuple(ids),
        )
        assert [r["id"] for r in results] == ids

    def test_postgres_bulk_insert_performance(self, cloud_db: DatabaseManager, capsys: Any) -> None:
        import time

        n = 1000
        base_id = 400
        methods = [BulkMethod.VALUES, BulkMethod.COPY, BulkMethod.EXECUTEMANY]
        timings: list[tuple[BulkMethod, float, float]] = []

        for m in methods:
            # ensure clean id range
            cloud_db.execute(
                f"DELETE FROM {self.TEST_TABLE} WHERE id >= %s AND id < %s",
                (base_id, base_id + n),
            )
            rows = [
                (base_id + i, f"perf-{i}", float(i % 10), None, None, (i % 2)) for i in range(n)
            ]
            t0 = time.perf_counter()
            cloud_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
                rows,
                method=m,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            timings.append((m, elapsed_ms, elapsed_ms / n))

        # Print results for visibility
        for m, total_ms, per_row in timings:
            print(f"Method {m.value}: {total_ms:.2f} ms total, {per_row:.3f} ms/row")

        captured = capsys.readouterr()
        assert "ms total" in captured.out

    def test_execute_many_pk_violation_cloud(self, cloud_db: DatabaseManager) -> None:
        cloud_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
            [(200, "Z")],
        )
        with pytest.raises(ConstraintError):
            cloud_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
                [(200, "Dup")],
            )

    def test_execute_many_unique_violation_cloud(self, cloud_db: DatabaseManager) -> None:
        cloud_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, email) VALUES (?, ?, ?)",
            [(210, "U1", "u@example.com")],
        )
        with pytest.raises(ConstraintError):
            cloud_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name, email) VALUES (?, ?, ?)",
                [(211, "U2", "u@example.com")],
            )

    def test_execute_many_not_null_violation_cloud(self, cloud_db: DatabaseManager) -> None:
        with pytest.raises(ConstraintError):
            cloud_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
                [(220, None)],
            )


class TestExecuteManyHelpers:
    """Explicit unit tests for execute_many helper methods and schema qualifier."""

    def test__bulk_executemany_sqlite_inserts(self, db_manager: DatabaseManager) -> None:
        # Arrange: create table
        db_manager.execute(
            """
            CREATE TABLE t_bulk (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )
        rows = [(1, "a"), (2, "b"), (3, "c")]
        cursor = db_manager._get_cursor()

        # Act
        db_manager._bulk_executemany(cursor, "INSERT INTO t_bulk (id, name) VALUES (?, ?)", rows)

        # Assert
        got = db_manager.fetchall("SELECT id, name FROM t_bulk ORDER BY id")
        assert [tuple(r.values()) for r in got] == rows

    def test__bulk_execute_values_calls_psycopg2_extras(
        self,
        db_manager: DatabaseManager,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange: stub psycopg2.extras.execute_values and capture args
        called = {"args": None, "kwargs": None}

        class _StubExtras:
            @staticmethod
            def execute_values(
                cur: object,
                query: str,
                data: object,
                page_size: int = 1000,
            ) -> None:
                from typing import Iterable, cast

                data_cast = cast(Iterable[Tuple[Any, ...]], data)
                called["args"] = (cur, query, list(data_cast))
                called["kwargs"] = {"page_size": page_size}

        monkeypatch.setattr("db.database_manager.PSYCOPG2_EXTRAS", _StubExtras, raising=True)

        # Fake cursor implementing the minimal surface
        class FakeCursor:
            def __init__(self) -> None:
                self.closed = False

            def close(self) -> None:
                self.closed = True

        cur = FakeCursor()
        db_manager.is_postgres = True  # simulate PG env
        # Compatible VALUES pattern will be rewritten to VALUES %s
        query = "INSERT INTO some_table (id, name) VALUES (%s, %s)"
        rows = [(1, "x"), (2, "y")]

        # Act
        db_manager._bulk_execute_values(cast(DBCursorProtocol, cur), query, rows, page_size=500)

        # Assert: our stub was invoked with expected arguments
        assert called["args"] is not None
        import re

        _, q_used, data_used = called["args"]
        assert re.search(r"(?i)VALUES\s+%s", q_used) is not None
        assert data_used == rows
        assert called["kwargs"] == {"page_size": 500}

        # Negative path: incompatible query raises DatabaseTypeError
        from db.exceptions import DatabaseTypeError

        with pytest.raises(DatabaseTypeError):
            db_manager._bulk_execute_values(
                cast(DBCursorProtocol, cur),
                "UPDATE some_table SET name=%s WHERE id=%s",
                rows,
                page_size=100,
            )

    def test__bulk_copy_from_builds_tsv_and_calls_copy(self, db_manager: DatabaseManager) -> None:
        # Arrange fake cursor to capture copy_from inputs
        captured = {"table": None, "columns": None, "content": None}

        class FakeCursor:
            def copy_from(
                self,
                file: TextIO,
                table: str,
                columns: Optional[Iterable[str]] = None,
                sep: str = "\t",
                null: str = "\\N",
            ) -> None:  # noqa: D401
                # Read whole stream to capture content
                captured["content"] = file.read()
                captured["table"] = table
                captured["columns"] = list(columns) if columns is not None else None

        cur = FakeCursor()
        db_manager.is_postgres = True
        db_manager.SCHEMA_NAME = "typing"  # ensure schema is set for qualification

        query = "INSERT INTO t_copy (id, name) VALUES (%s, %s)"
        rows = [(1, "a"), (2, None)]

        # Act
        db_manager._bulk_copy_from(cast(DBCursorProtocol, cur), query, rows)

        # Assert: schema-qualified table and TSV with nulls as \N
        assert captured["table"] == "typing.t_copy"
        assert captured["columns"] == ["id", "name"]
        # Expect two lines: "1\ta\n" and "2\t\\N\n"
        assert captured["content"].splitlines() == ["1\ta", "2\t\\N"]

    # @pytest.mark.parametrize(
    #     "sql,expected",
    #     [
    #         (
    #             "INSERT INTO foo (id,name) VALUES (?, ?)",
    #             "INSERT INTO typing.foo (id,name) VALUES (%s, %s)",
    #         ),
    #         ("UPDATE foo SET name=? WHERE id=?", "UPDATE typing.foo SET name=%s WHERE id=%s"),
    #         ("DELETE FROM foo WHERE id=?", "DELETE FROM typing.foo WHERE id=%s"),
    #         (
    #             "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
    #             "SELECT table_name FROM information_schema.tables WHERE table_schema = typing AND table_type = 'BASE TABLE' ORDER BY table_name",
    #         ),
    #         ("SELECT * FROM foo WHERE id=?", "SELECT * FROM typing.foo WHERE id=%s"),
    #         (
    #             "SELECT * FROM testtable limit 50 offset 0",
    #             "SELECT * FROM typing.testtable limit 50 offset 0",
    #         ),
    #         ("CREATE TABLE foo (id INT)", "CREATE TABLE typing.foo (id INT)"),
    #         ("DROP TABLE IF EXISTS foo", "DROP TABLE IF EXISTS typing.foo"),
    #         # normalization artifacts
    #         ("INSERT ... DO UPDATE typing.SET name='x'", "INSERT ... DO UPDATE SET name='x'"),
    #         ("DROP TABLE typing.IF EXISTS foo", "DROP TABLE IF EXISTS foo"),
    #     ],
    # )
    # def test__qualify_schema_in_query_parametrized(
    #     self, db_manager: DatabaseManager, sql: str, expected: str
    # ) -> None:
    #     db_manager.is_postgres = True
    #     db_manager.SCHEMA_NAME = "typing"
    #     got = db_manager._qualify_schema_in_query(sql)
    #     # Case-insensitive compare for non-placeholder parts; exact for %s replacement
    #     assert got == expected
