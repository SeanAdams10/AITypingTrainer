============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.3.5, pluggy-1.5.0 -- D:\SeanDevLocal\AITypingTrainer\.venv\Scripts\python.exe
cachedir: .pytest_cache
PySide6 6.9.1 -- Qt runtime 6.9.1 -- Qt compiled 6.9.1
rootdir: D:\SeanDevLocal\AITypingTrainer
configfile: pytest.ini
plugins: anyio-4.9.0, cov-6.1.1, mock-3.14.0, qt-4.4.0
collecting ... collected 31 items

tests/db/test_database_manager.py::TestDatabaseManagerInitialization::test_init_with_temp_file PASSED [  3%]
tests/db/test_database_manager.py::TestDatabaseManagerInitialization::test_init_with_invalid_path_raises_error PASSED [  6%]
tests/db/test_database_manager.py::TestDatabaseManagerInitialization::test_context_manager_cleans_up PASSED [  9%]
tests/db/test_database_manager.py::TestDatabaseOperations::test_execute_create_table PASSED [ 12%]
tests/db/test_database_manager.py::TestDatabaseOperations::test_execute_insert PASSED [ 16%]
tests/db/test_database_manager.py::TestDatabaseOperations::test_fetchone_returns_none_for_no_results PASSED [ 19%]
tests/db/test_database_manager.py::TestDatabaseOperations::test_fetchall_returns_all_results PASSED [ 22%]
tests/db/test_database_manager.py::TestDatabaseOperations::test_fetchall_returns_empty_list_for_no_results PASSED [ 25%]
tests/db/test_database_manager.py::TestErrorHandling::test_table_not_found_error PASSED [ 29%]
tests/db/test_database_manager.py::TestErrorHandling::test_schema_error PASSED [ 32%]
tests/db/test_database_manager.py::TestErrorHandling::test_foreign_key_error PASSED [ 35%]
tests/db/test_database_manager.py::TestErrorHandling::test_constraint_error_unique PASSED [ 38%]
tests/db/test_database_manager.py::TestErrorHandling::test_constraint_error_not_null PASSED [ 41%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_insert_success_sqlite PASSED [ 45%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_pk_violation_sqlite PASSED [ 48%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_unique_violation_sqlite PASSED [ 51%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_not_null_violation_sqlite PASSED [ 54%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_table_not_found_sqlite PASSED [ 58%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_insert_success_cloud PASSED [ 61%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_method_options_sqlite PASSED [ 64%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_method_options_cloud[BulkMethod.VALUES-300-rows0] PASSED [ 67%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_method_options_cloud[BulkMethod.COPY-302-rows1] FAILED [ 70%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_method_options_cloud[BulkMethod.EXECUTEMANY-304-rows2] PASSED [ 74%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_method_options_cloud[BulkMethod.AUTO-305-rows3] PASSED [ 77%]
tests/db/test_database_manager.py::TestExecuteMany::test_postgres_bulk_insert_performance FAILED [ 80%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_pk_violation_cloud PASSED [ 83%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_unique_violation_cloud PASSED [ 87%]
tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_not_null_violation_cloud PASSED [ 90%]
tests/db/test_database_manager.py::TestExecuteManyHelpers::test__bulk_executemany_sqlite_inserts PASSED [ 93%]
tests/db/test_database_manager.py::TestExecuteManyHelpers::test__bulk_execute_values_calls_psycopg2_extras PASSED [ 96%]
tests/db/test_database_manager.py::TestExecuteManyHelpers::test__bulk_copy_from_builds_tsv_and_calls_copy PASSED [100%]

================================== FAILURES ===================================
_ TestExecuteMany.test_execute_many_method_options_cloud[BulkMethod.COPY-302-rows1] _

self = <db.database_manager.DatabaseManager object at 0x00000244BA3676E0>
query = 'INSERT INTO tt_execmany_test (id, name, score, created_at, email, flag) VALUES (%s, %s, %s, %s, %s, %s)'
params_seq = [(302, 'C1', None, None, None, None), (303, 'C2', None, None, None, None)]

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
    
            if self.is_postgres:
                # Use shared qualifier logic for Postgres
                query = self._qualify_schema_in_query(query)
    
            # PostgreSQL-specific bulk strategies
            params_list: List[Tuple[object, ...]] = list(params_seq)
    
            # Normalize method flag to BulkMethod enum
            if isinstance(method, BulkMethod):
                method_flag = method
            else:
                method_map = {
                    "auto": BulkMethod.AUTO,
                    "values": BulkMethod.VALUES,
                    "copy": BulkMethod.COPY,
                    "execute_many": BulkMethod.EXECUTEMANY,
                }
                method_flag = method_map.get(str(method or "auto").lower(), BulkMethod.AUTO)
    
            if method_flag in (BulkMethod.AUTO, BulkMethod.VALUES, BulkMethod.COPY):
                # execute_values path
                if method_flag in (BulkMethod.AUTO, BulkMethod.VALUES) and query.strip().upper().startswith(
                    "INSERT INTO"
                ):
                    try:
                        if self.is_postgres:
                            return self._bulk_execute_values(cursor, query, params_list, page_size)
                        # For non-Postgres, fall through to executemany
                    except Exception:
                        if method_flag == BulkMethod.VALUES:
                            raise
    
                # COPY path
                if method_flag == BulkMethod.COPY and query.strip().upper().startswith("INSERT INTO"):
                    try:
                        if self.is_postgres:
>                           return self._bulk_copy_from(cursor, query, params_list)

db\database_manager.py:612: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <db.database_manager.DatabaseManager object at 0x00000244BA3676E0>
cursor = <cursor object at 0x00000244B85E9EE0; closed: 0>
query = 'INSERT INTO tt_execmany_test (id, name, score, created_at, email, flag) VALUES (%s, %s, %s, %s, %s, %s)'
params_list = [(302, 'C1', None, None, None, None), (303, 'C2', None, None, None, None)]

    def _bulk_copy_from(
        self,
        cursor: CursorProtocol,
        query: str,
        params_list: List[Tuple[object, ...]],
    ) -> CursorProtocol:
        """Use ``COPY FROM STDIN`` for fast ingestion of INSERT-like data on Postgres.
    
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
        import io
        import re
    
        m = re.search(r"INSERT\s+INTO\s+([^\s(]+)\s*\(([^)]+)\)", query, flags=re.IGNORECASE)
        if not m:
            raise DatabaseTypeError("COPY method requires INSERT ... (cols) VALUES ... form")
        table_name = m.group(1)
        cols_raw = m.group(2)
        cols = [c.strip() for c in cols_raw.split(",")]
        if "." not in table_name:
            table_name = f"{self.SCHEMA_NAME}.{table_name}"
        # Debug visibility for failing COPYs
        try:
            print(f"[DEBUG] COPY target table: {table_name}; columns: {cols}")
        except Exception:
            pass
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
    
>       cursor.copy_from(buf, table_name, columns=cols, sep="\t", null="\\N")
E       psycopg2.errors.UndefinedTable: relation "typing.tt_execmany_test" does not exist

db\database_manager.py:741: UndefinedTable

The above exception was the direct cause of the following exception:

self = <AITypingTrainer.tests.db.test_database_manager.TestExecuteMany object at 0x00000244B8456C50>
cloud_db = <db.database_manager.DatabaseManager object at 0x00000244BA3676E0>
method = <BulkMethod.COPY: 'copy'>, base_id = 302
rows = [(302, 'C1', None, None, None, None), (303, 'C2', None, None, None, None)]

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
    
>       cloud_db.execute_many(
            f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
            method=method,
        )

tests\db\test_database_manager.py:452: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
db\database_manager.py:630: in execute_many
    self._translate_and_raise(e)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <db.database_manager.DatabaseManager object at 0x00000244BA3676E0>
e = UndefinedTable('relation "typing.tt_execmany_test" does not exist\n')

    def _translate_and_raise(self, e: Exception) -> NoReturn:
        """Translate backend-specific exceptions to our custom exceptions and raise.
    
        Always raises; does not return.
        """
        # SQLite mapping
        if isinstance(e, sqlite3.OperationalError):
            error_msg: str = str(e).lower()
            if "unable to open database" in error_msg:
                raise DBConnectionError(f"Failed to connect to database at {self.db_path}") from e
            if "no such table" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "no such column" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        elif isinstance(e, sqlite3.IntegrityError):
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif "not null" in error_msg or "unique" in error_msg:
                raise ConstraintError(f"Constraint violation: {e}") from e
            elif "datatype mismatch" in error_msg:
                raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        elif isinstance(e, sqlite3.InterfaceError):
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        elif isinstance(e, sqlite3.DatabaseError):
            raise DatabaseError(f"Database error: {e}") from e
    
        # PostgreSQL mapping (optional dependency)
        if PSYCOPG2 is not None:
            if isinstance(e, (PSYCOPG2.OperationalError, PSYCOPG2.ProgrammingError)):
                error_msg = str(e).lower()
                if "connection" in error_msg:
                    raise DBConnectionError(f"Failed to connect to PostgreSQL database: {e}") from e
                if "does not exist" in error_msg and "relation" in error_msg:
>                   raise TableNotFoundError(f"Table not found: {e}") from e
E                   db.exceptions.TableNotFoundError: Table not found: relation "typing.tt_execmany_test" does not exist

db\database_manager.py:485: TableNotFoundError
---------------------------- Captured stdout setup ----------------------------
[DEBUG] Exception during query: table "tt_execmany_test" does not exist
. Rolling back transaction.
---------------------------- Captured stdout call -----------------------------
[DEBUG] COPY target table: typing.tt_execmany_test; columns: ['id', 'name', 'score', 'created_at', 'email', 'flag']
[DEBUG] Exception during execute_many: relation "typing.tt_execmany_test" does not exist
. Rolling back transaction.
____________ TestExecuteMany.test_postgres_bulk_insert_performance ____________

self = <db.database_manager.DatabaseManager object at 0x00000244BA473C40>
query = 'INSERT INTO tt_execmany_test (id, name, score, created_at, email, flag) VALUES (%s, %s, %s, %s, %s, %s)'
params_seq = [(400, 'perf-0', 0.0, None, None, 0), (401, 'perf-1', 1.0, None, None, 1), (402, 'perf-2', 2.0, None, None, 0), (403, 'perf-3', 3.0, None, None, 1), (404, 'perf-4', 4.0, None, None, 0), (405, 'perf-5', 5.0, None, None, 1), ...]

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
    
            if self.is_postgres:
                # Use shared qualifier logic for Postgres
                query = self._qualify_schema_in_query(query)
    
            # PostgreSQL-specific bulk strategies
            params_list: List[Tuple[object, ...]] = list(params_seq)
    
            # Normalize method flag to BulkMethod enum
            if isinstance(method, BulkMethod):
                method_flag = method
            else:
                method_map = {
                    "auto": BulkMethod.AUTO,
                    "values": BulkMethod.VALUES,
                    "copy": BulkMethod.COPY,
                    "execute_many": BulkMethod.EXECUTEMANY,
                }
                method_flag = method_map.get(str(method or "auto").lower(), BulkMethod.AUTO)
    
            if method_flag in (BulkMethod.AUTO, BulkMethod.VALUES, BulkMethod.COPY):
                # execute_values path
                if method_flag in (BulkMethod.AUTO, BulkMethod.VALUES) and query.strip().upper().startswith(
                    "INSERT INTO"
                ):
                    try:
                        if self.is_postgres:
                            return self._bulk_execute_values(cursor, query, params_list, page_size)
                        # For non-Postgres, fall through to executemany
                    except Exception:
                        if method_flag == BulkMethod.VALUES:
                            raise
    
                # COPY path
                if method_flag == BulkMethod.COPY and query.strip().upper().startswith("INSERT INTO"):
                    try:
                        if self.is_postgres:
>                           return self._bulk_copy_from(cursor, query, params_list)

db\database_manager.py:612: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <db.database_manager.DatabaseManager object at 0x00000244BA473C40>
cursor = <cursor object at 0x00000244B8502180; closed: 0>
query = 'INSERT INTO tt_execmany_test (id, name, score, created_at, email, flag) VALUES (%s, %s, %s, %s, %s, %s)'
params_list = [(400, 'perf-0', 0.0, None, None, 0), (401, 'perf-1', 1.0, None, None, 1), (402, 'perf-2', 2.0, None, None, 0), (403, 'perf-3', 3.0, None, None, 1), (404, 'perf-4', 4.0, None, None, 0), (405, 'perf-5', 5.0, None, None, 1), ...]

    def _bulk_copy_from(
        self,
        cursor: CursorProtocol,
        query: str,
        params_list: List[Tuple[object, ...]],
    ) -> CursorProtocol:
        """Use ``COPY FROM STDIN`` for fast ingestion of INSERT-like data on Postgres.
    
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
        import io
        import re
    
        m = re.search(r"INSERT\s+INTO\s+([^\s(]+)\s*\(([^)]+)\)", query, flags=re.IGNORECASE)
        if not m:
            raise DatabaseTypeError("COPY method requires INSERT ... (cols) VALUES ... form")
        table_name = m.group(1)
        cols_raw = m.group(2)
        cols = [c.strip() for c in cols_raw.split(",")]
        if "." not in table_name:
            table_name = f"{self.SCHEMA_NAME}.{table_name}"
        # Debug visibility for failing COPYs
        try:
            print(f"[DEBUG] COPY target table: {table_name}; columns: {cols}")
        except Exception:
            pass
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
    
>       cursor.copy_from(buf, table_name, columns=cols, sep="\t", null="\\N")
E       psycopg2.errors.UndefinedTable: relation "typing.tt_execmany_test" does not exist

db\database_manager.py:741: UndefinedTable

The above exception was the direct cause of the following exception:

self = <AITypingTrainer.tests.db.test_database_manager.TestExecuteMany object at 0x00000244B85E8D70>
cloud_db = <db.database_manager.DatabaseManager object at 0x00000244BA473C40>
capsys = <_pytest.capture.CaptureFixture object at 0x00000244B86317F0>

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
>           cloud_db.execute_many(
                f"INSERT INTO {self.TEST_TABLE} (id, name, score, created_at, email, flag) VALUES (?, ?, ?, ?, ?, ?)",
                rows,
                method=m,
            )

tests\db\test_database_manager.py:484: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
db\database_manager.py:630: in execute_many
    self._translate_and_raise(e)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <db.database_manager.DatabaseManager object at 0x00000244BA473C40>
e = UndefinedTable('relation "typing.tt_execmany_test" does not exist\n')

    def _translate_and_raise(self, e: Exception) -> NoReturn:
        """Translate backend-specific exceptions to our custom exceptions and raise.
    
        Always raises; does not return.
        """
        # SQLite mapping
        if isinstance(e, sqlite3.OperationalError):
            error_msg: str = str(e).lower()
            if "unable to open database" in error_msg:
                raise DBConnectionError(f"Failed to connect to database at {self.db_path}") from e
            if "no such table" in error_msg:
                raise TableNotFoundError(f"Table not found: {e}") from e
            if "no such column" in error_msg:
                raise SchemaError(f"Schema error: {e}") from e
            raise DatabaseError(f"Database operation failed: {e}") from e
        elif isinstance(e, sqlite3.IntegrityError):
            error_msg = str(e).lower()
            if "foreign key" in error_msg:
                raise ForeignKeyError(f"Foreign key constraint failed: {e}") from e
            elif "not null" in error_msg or "unique" in error_msg:
                raise ConstraintError(f"Constraint violation: {e}") from e
            elif "datatype mismatch" in error_msg:
                raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
            raise IntegrityError(f"Integrity error: {e}") from e
        elif isinstance(e, sqlite3.InterfaceError):
            raise DatabaseTypeError(f"Type error in query parameters: {e}") from e
        elif isinstance(e, sqlite3.DatabaseError):
            raise DatabaseError(f"Database error: {e}") from e
    
        # PostgreSQL mapping (optional dependency)
        if PSYCOPG2 is not None:
            if isinstance(e, (PSYCOPG2.OperationalError, PSYCOPG2.ProgrammingError)):
                error_msg = str(e).lower()
                if "connection" in error_msg:
                    raise DBConnectionError(f"Failed to connect to PostgreSQL database: {e}") from e
                if "does not exist" in error_msg and "relation" in error_msg:
>                   raise TableNotFoundError(f"Table not found: {e}") from e
E                   db.exceptions.TableNotFoundError: Table not found: relation "typing.tt_execmany_test" does not exist

db\database_manager.py:485: TableNotFoundError
---------------------------- Captured stdout setup ----------------------------
[DEBUG] Exception during query: table "tt_execmany_test" does not exist
. Rolling back transaction.
---------------------------- Captured stdout call -----------------------------
[DEBUG] COPY target table: typing.tt_execmany_test; columns: ['id', 'name', 'score', 'created_at', 'email', 'flag']
[DEBUG] Exception during execute_many: relation "typing.tt_execmany_test" does not exist
. Rolling back transaction.
============================== warnings summary ===============================
tests/db/test_database_manager.py: 18 warnings
  D:\SeanDevLocal\AITypingTrainer\.venv\Lib\site-packages\botocore\auth.py:422: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    datetime_now = datetime.datetime.utcnow()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/db/test_database_manager.py::TestExecuteMany::test_execute_many_method_options_cloud[BulkMethod.COPY-302-rows1] - db.exceptions.TableNotFoundError: Table not found: relation "typing.tt_execmany_test" does not exist
FAILED tests/db/test_database_manager.py::TestExecuteMany::test_postgres_bulk_insert_performance - db.exceptions.TableNotFoundError: Table not found: relation "typing.tt_execmany_test" does not exist
================== 2 failed, 29 passed, 18 warnings in 8.07s ==================
