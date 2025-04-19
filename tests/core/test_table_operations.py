"""
Tests for table operations (delete, backup, restore).
"""
import os
import sys
import json
import pytest
import sqlite3
from pathlib import Path
from typing import Callable, Generator, Dict, List, Any, TypedDict

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now import from project modules
from db.table_operations import TableOperations, BackupData  # noqa: E402


class TestTableOperations:
    """Test class for database table operations."""

    @pytest.fixture
    def test_db_path(self, tmp_path: Path) -> Generator[str, None, None]:
        """Create a temporary test database using pytest's tmp_path fixture."""
        # Create a database file in the temporary directory
        db_path = tmp_path / "test.db"
        yield str(db_path)
        # Cleanup is handled automatically by pytest's tmp_path fixture

    @pytest.fixture
    def test_db_connection(
        self, test_db_path: str
    ) -> Callable[[], sqlite3.Connection]:
        """Create a test database with test table and sample data."""
        # Create a connection to the test database
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create a test table
        cursor.execute('''
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            text_value TEXT,
            int_value INTEGER,
            float_value REAL
        )
        ''')

        # Insert some test data
        cursor.execute('''
        INSERT INTO test_table (text_value, int_value, float_value)
        VALUES (?, ?, ?)
        ''', ('Test value', 123, 45.67))

        # Create a special table for testing with special characters
        cursor.execute('''
        CREATE TABLE special_chars (
            id INTEGER PRIMARY KEY,
            special_value TEXT
        )
        ''')
        # Insert special character test data
        special_cases = [
            (1, "'"),
            (2, '"'),
            (3, "[ ] { } ( ) < >"),
            (4, "Hello 'World' \"Python\" [test] {json} (tuple) <html>")
        ]
        cursor.executemany('INSERT INTO special_chars (id, special_value) VALUES (?, ?)', special_cases)
        # Commit the changes
        conn.commit()
        conn.close()

        # Return a function that creates connections to this database
        def get_connection() -> sqlite3.Connection:
            connection = sqlite3.connect(test_db_path)
            connection.row_factory = sqlite3.Row
            return connection

        return get_connection

    @pytest.fixture
    def table_ops(
        self,
        test_db_connection: Callable[[], sqlite3.Connection],
        tmp_path: Path
    ) -> TableOperations:
        """Create a TableOperations instance with test database connection."""
        # Use pytest's tmp_path fixture for backup directory
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()

        # Create and initialize TableOperations
        ops = TableOperations(test_db_connection)
        ops.backup_dir = str(backup_dir)

        return ops

    def test_table_exists(self, table_ops: TableOperations) -> None:
        """Test the table_exists method."""
        # Test with existing table
        assert table_ops.table_exists("test_table") is True

        # Test with non-existent table
        assert table_ops.table_exists("nonexistent_table") is False

    def test_is_table_empty_with_empty_table(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test checking if an empty table is empty."""
        # First empty the table
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM test_table")
        conn.commit()
        conn.close()

        # Check if table is empty
        is_empty, error = table_ops.is_table_empty("test_table")

        # Assert result
        assert is_empty is True
        assert error is None

    def test_is_table_empty_with_data(self, table_ops: TableOperations) -> None:
        """Test checking if a non-empty table is empty."""
        # The test_table fixture already contains data
        is_empty, error = table_ops.is_table_empty("test_table")

        # Assert result
        assert is_empty is False
        assert error is None

    def test_is_table_empty_nonexistent_table(
        self, table_ops: TableOperations
    ) -> None:
        """Test checking if a non-existent table is empty."""
        is_empty, error = table_ops.is_table_empty("nonexistent_table")

        # Assert result
        assert is_empty is False
        assert error is not None
        assert "not found" in error

    def test_delete_all_rows_success(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test deleting all rows from a table successfully."""
        # First verify there's data in the table using is_table_empty
        is_empty, _ = table_ops.is_table_empty("test_table")
        assert is_empty is False, "Table should have data"

        # Delete all rows
        success, error = table_ops.delete_all_rows("test_table")

        # Assert success
        assert success is True
        assert error is None

        # Verify table is empty using is_table_empty
        is_empty, error = table_ops.is_table_empty("test_table")
        assert is_empty is True, "Table should be empty after deletion"
        assert error is None

    def test_delete_all_rows_nonexistent_table(
        self, table_ops: TableOperations
    ) -> None:
        """Test deleting from a non-existent table."""
        # Try to delete from a non-existent table
        success, error = table_ops.delete_all_rows("nonexistent_table")

        # Assert failure
        assert success is False
        assert error is not None and "Table not found" in error

    def test_backup_table_success(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test backing up a table successfully."""
        # Backup the test table
        success, error, file_path = table_ops.backup_table("test_table")

        # Assert success
        assert success is True
        assert error is None
        assert file_path is not None
        assert os.path.exists(file_path)

        # Verify backup file contents
        with open(file_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        # Check structure and content
        assert backup_data["table_name"] == 'test_table'
        assert set(backup_data["columns"]) == {
            'id', 'text_value', 'int_value', 'float_value'
        }
        assert len(backup_data["data"]) > 0
        assert backup_data["data"][0]['text_value'] == 'Test value'
        assert backup_data["data"][0]['int_value'] == 123
        assert backup_data["data"][0]['float_value'] == 45.67

    def test_backup_table_nonexistent(self, table_ops: TableOperations) -> None:
        """Test backing up a non-existent table."""
        # Try to backup a non-existent table
        success, error, file_path = table_ops.backup_table("nonexistent_table")

        # Assert failure
        assert success is False
        assert error is not None and "Table not found" in error
        assert file_path is None

    def test_backup_table_empty(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test backing up an empty table."""
        # First empty the test table
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM test_table")
        conn.commit()
        conn.close()

        # Try to backup the empty table
        success, error, file_path = table_ops.backup_table("test_table")

        # Assert failure
        assert success is False
        assert error is not None and "no rows" in error.lower()
        assert file_path is None

    def test_restore_table_success(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test restoring a table from backup successfully."""
        # First backup the table
        success, error, backup_file = table_ops.backup_table("test_table")
        assert success is True, "Failed to create backup"

        # Now delete all rows
        success, error = table_ops.delete_all_rows("test_table")
        assert success is True, "Failed to delete rows"

        # Now restore from the backup
        assert backup_file is not None
        success, error, rows_restored = table_ops.restore_table(
            "test_table", backup_file
        )

        # Assert success
        assert success is True
        assert error is None
        assert rows_restored > 0

        # Verify restored data
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_table")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) > 0
        row = dict(rows[0])
        assert row['text_value'] == 'Test value'
        assert row['int_value'] == 123
        assert row['float_value'] == 45.67

    def test_restore_table_nonexistent(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test restoring to a non-existent table."""
        # First create a backup
        success, error, backup_file = table_ops.backup_table("test_table")
        assert success is True, "Failed to create backup"

        # Try to restore to a non-existent table
        assert backup_file is not None
        success, error, rows_restored = table_ops.restore_table(
            "nonexistent_table", backup_file
        )

        # Assert failure
        assert success is False
        assert error is not None and "Table not found" in error
        assert rows_restored == 0

    def test_restore_table_invalid_backup(
        self, table_ops: TableOperations
    ) -> None:
        """Test restoring from an invalid backup file."""
        # Create an invalid backup file
        invalid_file = os.path.join(
            table_ops.backup_dir, "invalid_backup.json"
        )
        with open(invalid_file, 'w') as f:
            f.write('{"invalid": "json"}')

        # Try to restore from the invalid file
        success, error, rows_restored = table_ops.restore_table(
            "test_table", invalid_file
        )  # invalid_file is always str

        # Assert failure
        assert success is False
        assert error is not None and "Invalid backup file" in error
        assert rows_restored == 0

    def test_restore_table_column_mismatch(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test restoring with mismatched columns."""
        # First backup the table
        success, error, backup_file = table_ops.backup_table("test_table")
        assert success is True, "Failed to create backup"

    @pytest.mark.parametrize("special_value", [
        "'", '"', '[ ] { } ( ) < >', "Hello 'World' \"Python\" [test] {json} (tuple) <html>"
    ])
    def test_backup_and_restore_special_characters(
        self,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection],
        special_value: str
    ) -> None:
        """Test backup and restore with special characters in data."""
        # Insert the special value into the table
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM special_chars')
        cursor.execute('INSERT INTO special_chars (id, special_value) VALUES (?, ?)', (1, special_value))
        conn.commit()
        conn.close()
        # Backup
        success, error, backup_file = table_ops.backup_table("special_chars")
        assert success is True
        assert error is None
        assert backup_file is not None
        # Delete all rows
        success, error = table_ops.delete_all_rows("special_chars")
        assert success is True
        # Restore
        success, error, rows_restored = table_ops.restore_table("special_chars", backup_file)
        assert success is True
        assert error is None
        assert rows_restored == 1
        # Check restored value
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT special_value FROM special_chars WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        assert result[0] == special_value

        # Modify the backup file to have different columns
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        # Change the columns
        backup_data['columns'] = [
            'id', 'text_value', 'int_value', 'extra_column'
        ]

        # Write back to file
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)

        # Try to restore from the modified file
        success, error, rows_restored = table_ops.restore_table(
            "test_table", backup_file
        )

        # Assert failure
        assert success is False
        assert error is not None and "columns do not match" in error.lower()
        assert rows_restored == 0

    @pytest.mark.parametrize("special_chars", [
        "' single quote",
        '" double quote',
        "[ ] square brackets",
        "{ } curly braces",
        "( ) parentheses",
        "< > angle brackets",
        "# $ % ^ & * symbols",
        "\\backslash\\ and /forward slash/",
        "tab\tand newline\nchars",
        "unicode €£¥ chars",
        "SQL reserved words SELECT FROM WHERE"
    ])
    def test_special_chars_backup_restore(
        self,
        special_chars: str,
        table_ops: TableOperations,
        test_db_connection: Callable[[], sqlite3.Connection]
    ) -> None:
        """Test backing up and restoring with special characters."""
        # Insert data with special characters
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM special_chars")  # Clear existing data
        cursor.execute(
            "INSERT INTO special_chars (special_value) VALUES (?)",
            (special_chars,)
        )
        conn.commit()
        conn.close()

        # Backup the table
        success, error, backup_file = table_ops.backup_table("special_chars")
        msg = f"Failed to backup with special chars: {error}"
        assert success is True, msg

        # Delete all rows
        success, error = table_ops.delete_all_rows("special_chars")
        assert success is True, "Failed to delete rows"

        # Restore from backup
        assert backup_file is not None
        success, error, rows_restored = table_ops.restore_table(
            "special_chars", backup_file
        )
        msg = f"Failed to restore with special chars: {error}"
        assert success is True, msg

        # Verify the restored data
        conn = test_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT special_value FROM special_chars LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        # Assert the restored value matches the original
        assert row is not None
        assert row[0] == special_chars
