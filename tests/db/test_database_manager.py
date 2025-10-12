"""Tests for the DatabaseManager class.

This module contains comprehensive tests for the DatabaseManager class,
verifying its functionality, error handling, and edge cases.
"""

from typing import Any, Iterable, Optional, TextIO, cast

import pytest

from db.database_manager import BulkMethod, ConnectionType, DatabaseManager
from db.database_manager import CursorProtocol as DBCursorProtocol
from db.exceptions import (
    ConstraintError,
    DBConnectionError,
    ForeignKeyError,
    SchemaError,
    TableNotFoundError,
)

# Import test constants from global conftest
from tests.conftest import TEST_DATA, TEST_TABLE_NAME

# Note: initialized_db fixture is now provided globally in tests/conftest.py


class TestDatabaseManagerInitialization:
    """Test cases for DatabaseManager initialization and basic functionality."""

    def test_init_with_postgres_docker(self, db_manager: DatabaseManager) -> None:
        """Test initialization with a PostgreSQL Docker database."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        db = db_manager
        assert db is not None
        # Verify we can connect and execute a simple query
        result = db.fetchone("SELECT 1 as test_value")
        assert result is not None
        assert result["test_value"] == 1

    def test_invalid_connection_type_raises_error(self) -> None:
        """Test that invalid connection types raise appropriate errors."""
        # Test with None (invalid connection type)
        with pytest.raises((DBConnectionError, TypeError)):
            DatabaseManager(connection_type=None)  # type: ignore[arg-type]

    def test_context_manager_cleans_up(self) -> None:
        """Test that the context manager properly cleans up resources."""
        # Note: This test creates its own DB instance, so we assert after creation
        with DatabaseManager(connection_type=ConnectionType.POSTGRESS_DOCKER) as db:
            assert db.connection_type == ConnectionType.POSTGRESS_DOCKER
            # Do something with the database
            db.execute("CREATE TABLE test (id SERIAL PRIMARY KEY)")
            # Verify table was created
            assert db.table_exists("test")

        # After context manager exits, connection should be closed
        # We can't easily test this without accessing private attributes
        # but the Docker container should be cleaned up


class TestDatabaseOperations:
    """Test cases for database operations (execute, fetchone, fetchall)."""

    def test_execute_create_table(self, db_manager: DatabaseManager) -> None:
        """Test executing a CREATE TABLE statement."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        db_manager.execute(
            f"""
            CREATE TABLE {TEST_TABLE_NAME} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """
        )

        # Verify the table was created by querying information_schema
        result = db_manager.fetchone(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (db_manager.SCHEMA_NAME, TEST_TABLE_NAME),
        )
        assert result is not None
        assert result["table_name"] == TEST_TABLE_NAME

    def test_execute_insert(self, initialized_db: DatabaseManager) -> None:
        """Test executing an INSERT statement."""
        assert initialized_db.connection_type == ConnectionType.POSTGRESS_DOCKER
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
        assert initialized_db.connection_type == ConnectionType.POSTGRESS_DOCKER
        result = initialized_db.fetchone(f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?", (999,))
        assert result is None

    def test_fetchall_returns_all_results(self, initialized_db: DatabaseManager) -> None:
        """Test that fetchall returns all matching rows."""
        assert initialized_db.connection_type == ConnectionType.POSTGRESS_DOCKER
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
        assert initialized_db.connection_type == ConnectionType.POSTGRESS_DOCKER
        results = initialized_db.fetchall(f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?", (999,))
        assert results == []


class TestErrorHandling:
    """Test cases for error handling in DatabaseManager."""

    def test_table_not_found_error(self, db_manager: DatabaseManager) -> None:
        """Test that querying a non-existent table raises TableNotFoundError."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        with pytest.raises(TableNotFoundError):
            db_manager.execute("SELECT * FROM non_existent_table")

    def test_schema_error(self, initialized_db: DatabaseManager) -> None:
        """Test that querying with invalid column names raises SchemaError."""
        assert initialized_db.connection_type == ConnectionType.POSTGRESS_DOCKER
        with pytest.raises(SchemaError):
            initialized_db.execute(f"SELECT non_existent_column FROM {TEST_TABLE_NAME}")

    def test_foreign_key_error(self, db_manager: DatabaseManager) -> None:
        """Test that foreign key violations raise ForeignKeyError."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
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
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
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
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
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

    def _cloud_available(self) -> bool:
        # Allow cloud tests only if deps exist and env signals intent
        # return CLOUD_DEPENDENCIES_AVAILABLE and (
        #     os.environ.get("RUN_CLOUD_DB_TESTS", "0") == "1"
        # )
        # Cloud dependencies are now always available (direct imports)
        return True

    def test_execute_many_insert_success_cloud(self, db_with_tables: DatabaseManager) -> None:
        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER
        rows = [
            (100, "P-Alice", 1.25, "2025-08-09T07:21:55Z", "pa@example.com", 1),
            (101, "P-Bob", 2.5, "2025-08-09T07:21:56Z", "pb@example.com", 0),
        ]

        # create the test table
        self._create_table(db_with_tables)
        db_with_tables.execute_many(
            f"INSERT INTO {self.TEST_TABLE} "
            f"(id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        results = db_with_tables.fetchall(
            f"SELECT id, name, score, created_at, email, flag FROM {self.TEST_TABLE} ORDER BY id"
        )
        # Postgres returns decimals/floats; compare converted tuples
        got = [
            (
                r["id"],
                r["name"],
                float(cast(Any, r["score"])) if r["score"] is not None else None,
                r["created_at"],
                r["email"],
                r["flag"],
            )
            for r in results
        ]
        exp = [
            (
                r[0],
                r[1],
                float(cast(Any, r[2])) if r[2] is not None else None,
                r[3],
                r[4],
                r[5],
            )
            for r in rows
        ]
        assert got == exp

    @pytest.mark.parametrize(
        "method,base_id,rows",
        [
            (
                BulkMethod.VALUES,
                300,
                [(300, "V1", 1.25, None, None, None), (301, "V2", 2.5, None, None, None)],
            ),
            (
                BulkMethod.COPY,
                302,
                [(302, "C1", None, None, None, None), (303, "C2", None, None, None, None)],
            ),
            (BulkMethod.EXECUTEMANY, 304, [(304, "E1", None, None, None, None)]),
            (BulkMethod.AUTO, 305, [(305, "A1", None, None, None, None)]),
        ],
    )
    def test_execute_many_method_options(
        self,
        db_with_tables: DatabaseManager,
        method: BulkMethod,
        base_id: int,
        rows: list[tuple[object, ...]],
    ) -> None:
        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        # create the test table
        self._create_table(db_with_tables)

        # Ensure clean slate for these IDs
        ids_for_delete = [cast(int, r[0]) for r in rows]
        max_id = max(ids_for_delete) + 1
        db_with_tables.execute(
            f"DELETE FROM {self.TEST_TABLE} WHERE id >= %s AND id < %s",
            (base_id, max_id),
        )

        db_with_tables.execute_many(
            f"INSERT INTO {self.TEST_TABLE} "
            f"(id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
            method=method,
        )

        ids = ids_for_delete
        placeholders = ", ".join(["%s"] * len(ids))
        results = db_with_tables.fetchall(
            f"SELECT id, name FROM {self.TEST_TABLE} WHERE id IN ({placeholders}) ORDER BY id",
            tuple(ids),
        )
        assert [r["id"] for r in results] == ids

    def test_postgres_bulk_insert_performance(
        self,
        db_with_tables: DatabaseManager,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        import time

        # create the test table
        self._create_table(db_with_tables)

        n = 1000
        base_id = 400
        methods = [BulkMethod.VALUES, BulkMethod.COPY, BulkMethod.EXECUTEMANY]
        timings: list[tuple[BulkMethod, float, float]] = []

        for m in methods:
            # ensure clean id range
            db_with_tables.execute(
                f"DELETE FROM {self.TEST_TABLE} WHERE id >= %s AND id < %s",
                (base_id, base_id + n),
            )
            rows = [
                (base_id + i, f"perf-{i}", float(i % 10), None, None, (i % 2)) for i in range(n)
            ]
            t0 = time.perf_counter()
            db_with_tables.execute_many(
                (
                    f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)"
                ),
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

    def test_execute_many_pk_violation(self, db_with_tables: DatabaseManager) -> None:
        self._create_table(db_with_tables)

        db_with_tables.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
            [(200, "Z")],
        )
        with pytest.raises(ConstraintError):
            db_with_tables.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
                [(200, "Dup")],
            )

    def test_execute_many_unique_violation(self, db_with_tables: DatabaseManager) -> None:
        self._create_table(db_with_tables)

        db_with_tables.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, email) VALUES (?, ?, ?)",
            [(210, "U1", "u@example.com")],
        )
        with pytest.raises(ConstraintError):
            db_with_tables.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name, email) VALUES (?, ?, ?)",
                [(211, "U2", "u@example.com")],
            )

    def test_execute_many_not_null_violation(self, db_with_tables: DatabaseManager) -> None:
        self._create_table(db_with_tables)

        with pytest.raises(ConstraintError):
            db_with_tables.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name) VALUES (?, ?)",
                [(220, None)],
            )


class TestInitTables:
    """Test cases for DatabaseManager.init_tables() method."""

    # Expected tables that should be created by init_tables()
    EXPECTED_TABLES = {
        "categories",
        "words",
        "snippets",
        "snippet_parts",
        "practice_sessions",
        "session_keystrokes",
        "session_ngram_speed",
        "session_ngram_errors",
        "ngram_speed_summary_curr",
        "ngram_speed_summary_hist",
        "session_ngram_summary",
        "users",
        "keyboards",
        "settings",
        "settings_history",
        "keysets",
        "keysets_history",
        "keyset_keys",
        "keyset_keys_history",
    }

    def test_init_tables_creates_all_expected_tables(self, db_manager: DatabaseManager) -> None:
        """Test 1: SQLITE - Verify all expected tables are created in new database."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        # Verify database starts empty (no user tables)
        initial_tables = db_manager.list_tables()
        assert initial_tables == []

        # Call init_tables
        db_manager.init_tables()

        # Get all tables after initialization
        created_tables = set(db_manager.list_tables())

        # Verify all expected tables were created
        assert created_tables == self.EXPECTED_TABLES, (
            f"Missing tables: {self.EXPECTED_TABLES - created_tables}, "
            f"Unexpected tables: {created_tables - self.EXPECTED_TABLES}"
        )

        # Verify each expected table exists using table_exists method
        for table_name in self.EXPECTED_TABLES:
            assert db_manager.table_exists(table_name), f"Table {table_name} should exist"

    def test_init_tables_creates_no_unexpected_tables(self, db_manager: DatabaseManager) -> None:
        """Test 2: SQLITE - Verify no unexpected tables are created beyond expected list."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        # Call init_tables
        db_manager.init_tables()

        # Get all created tables
        created_tables = set(db_manager.list_tables())

        # Verify no extra tables were created
        unexpected_tables = created_tables - self.EXPECTED_TABLES
        assert len(unexpected_tables) == 0, f"Unexpected tables created: {unexpected_tables}"

        # Verify exact count matches expected
        assert len(created_tables) == len(self.EXPECTED_TABLES), (
            f"Expected {len(self.EXPECTED_TABLES)} tables, got {len(created_tables)}"
        )

    def test_init_tables_idempotency(self, db_manager: DatabaseManager) -> None:
        """Test that init_tables can be called multiple times safely (idempotency)."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        # Call init_tables first time
        db_manager.init_tables()
        first_tables = set(db_manager.list_tables())

        # Call init_tables second time
        db_manager.init_tables()
        second_tables = set(db_manager.list_tables())

        # Verify tables are identical after multiple calls
        assert first_tables == second_tables == self.EXPECTED_TABLES

    def test_list_tables_with_custom_tables(self, db_manager: DatabaseManager) -> None:
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER

        db_manager.execute("Drop Schema typing CASCADE")
        db_manager.execute("Create Schema typing")

        # Create a series of test tables with different names
        test_tables = ["test_table_1", "test_table_2", "custom_data", "temp_results"]

        for table_name in test_tables:
            db_manager.execute(f"""
                CREATE TABLE {table_name} (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Get all tables using list_tables
        all_tables = set(db_manager.list_tables())

        # Verify all custom tables exist in the list
        for table_name in test_tables:
            assert table_name in all_tables, (
                f"Custom table {table_name} should be in list_tables result"
            )

        # Verify table_exists returns True for each custom table
        for table_name in test_tables:
            assert db_manager.table_exists(table_name), (
                f"table_exists should return True for {table_name}"
            )

        # Verify only our custom tables exist (no system tables)
        assert all_tables == set(test_tables), (
            f"Expected only custom tables {test_tables}, got {all_tables}"
        )

    def test_list_tables_excludes_postgres_system_tables(self, db_manager: DatabaseManager) -> None:
        """Test that list_tables properly excludes PostgreSQL system tables."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        db_manager.execute("Drop Schema typing CASCADE")
        db_manager.execute("Create Schema typing")

        # Create one custom table
        db_manager.execute("""
            CREATE TABLE user_data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)

        # Get tables using list_tables
        tables = db_manager.list_tables()

        # Verify only user table is returned (no PostgreSQL system tables)
        assert tables == ["user_data"]

        # Verify system tables are not included even though they exist in information_schema
        system_tables_query = """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'information_schema' 
            AND table_type = 'BASE TABLE'
        """
        system_tables = db_manager.fetchall(system_tables_query)

        # System tables should exist in information_schema but not in list_tables result
        if system_tables:  # Only check if system tables exist
            for system_table in system_tables:
                assert system_table["table_name"] not in tables, (
                    f"System table {system_table['table_name']} should not be in list_tables result"
                )

    def test_table_exists_method_accuracy(self, db_manager: DatabaseManager) -> None:
        """Test table_exists method accuracy with various scenarios."""
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        # Clean out all tables
        db_manager.execute("Drop Schema typing CASCADE")
        db_manager.execute("Create Schema typing")

        # Test with non-existent table
        assert not db_manager.table_exists("non_existent_table")

        # Create a test table
        db_manager.execute("""
            CREATE TABLE test_existence (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)

        # Test with existing table
        assert db_manager.table_exists("test_existence")

        # Test case sensitivity (SQLite is sensitive for table names)
        assert not db_manager.table_exists("TEST_EXISTENCE")
        assert not db_manager.table_exists("Test_Existence")

        # Test with empty string (should return False)
        assert not db_manager.table_exists("")

        # Test with special characters in table name
        db_manager.execute("""
            CREATE TABLE "table-with-dashes" (
                id INTEGER PRIMARY KEY
            )
        """)
        assert db_manager.table_exists("table-with-dashes")


class TestExecuteManyHelpers:
    """Explicit unit tests for execute_many helper methods and schema qualifier."""

    def test__bulk_copy_from_builds_tsv_and_calls_copy(self, db_manager: DatabaseManager) -> None:
        assert db_manager.connection_type == ConnectionType.POSTGRESS_DOCKER
        # Arrange fake cursor to capture copy_from inputs
        captured: dict[str, object | None] = {"table": None, "columns": None, "content": None}

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
        db_manager._bulk_copy_from(
            cast(DBCursorProtocol, cur),
            query,
            cast(list[tuple[object, ...]], rows),
        )

        # Assert: schema-qualified table and TSV with nulls as \N
        table_obj = captured["table"]
        assert isinstance(table_obj, str)
        assert table_obj == "typing.t_copy"

        columns_obj = captured["columns"]
        # We expect COPY column names to be a list of strings
        assert isinstance(columns_obj, list)
        assert cast(list[str], columns_obj) == ["id", "name"]

        # Expect two lines: "1\ta\n" and "2\t\\N\n"
        content_obj = captured["content"]
        assert isinstance(content_obj, str)
        assert content_obj.splitlines() == ["1\ta", "2\t\\N"]
