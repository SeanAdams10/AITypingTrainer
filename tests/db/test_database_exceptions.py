"""
Tests for database exception handling in DatabaseManager.
"""

import sqlite3

import pytest
from pytest_mock import MockerFixture

from db.database_manager import DatabaseManager
from db.exceptions import (
    ConstraintError,
    DatabaseTypeError,
    DBConnectionError,
    ForeignKeyError,
    SchemaError,
    TableNotFoundError,
)
from tests.helpers.db_helpers import create_connection_error_db


class TestDatabaseExceptions:
    """Test cases for database exception handling."""

    def test_connection_error(self) -> None:
        """Test connection error when database cannot be opened."""
        # Use helper function to create a path that will cause a connection error
        db_path = create_connection_error_db()
        with pytest.raises(DBConnectionError):
            DatabaseManager(db_path)

    def test_foreign_key_violation(self, db_with_tables: DatabaseManager) -> None:
        """Test foreign key constraint violation."""
        # db_with_tables already has tables initialized

        print("Testing foreign key violation")

        # Try to insert a snippet with a non-existent category_id
        with pytest.raises(ForeignKeyError):
            db_with_tables.execute(
                "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
                (1, 999, "test_snippet"),  # category_id 999 doesn't exist
            )

    def test_schema_error(self, db_with_tables: DatabaseManager) -> None:
        """Test schema-related errors with bad column names."""
        # First, create a valid category to ensure the table exists and has data
        db_with_tables.execute(
            "INSERT INTO categories (category_name) VALUES (?)", ("Test Category",)
        )

        # Try to update a valid table with a non-existent column
        with pytest.raises(SchemaError):
            db_with_tables.execute(
                "UPDATE categories SET non_existent_column = 'test' "
                "WHERE category_name = 'Test Category'"
            )

    def test_type_error(self, db_with_tables: DatabaseManager) -> None:
        """Test type-related errors."""
        # Try to insert a row with wrong parameter types
        db_with_tables.execute("INSERT INTO categories (category_name) VALUES ('test')")
        with pytest.raises(DatabaseTypeError):
            # Passing a dictionary instead of a tuple for params
            db_with_tables.execute("update categories set category_id = 'fish'")

    def test_constraint_violation(self, db_with_tables: DatabaseManager) -> None:
        """Test constraint violations (NOT NULL, UNIQUE)."""
        # Test NOT NULL constraint
        with pytest.raises(ConstraintError):
            db_with_tables.execute(
                "INSERT INTO categories (category_id) VALUES (?)",
                (1,),  # Missing required category_name
            )

        # Test UNIQUE constraint
        db_with_tables.execute(
            "INSERT INTO categories (category_name) VALUES (?)",
            ("test_category",),
        )
        with pytest.raises(ConstraintError):
            db_with_tables.execute(
                "INSERT INTO categories (category_name) VALUES (?)",
                ("test_category",),  # Duplicate name
            )

    def test_connection_error_on_close(
        self,
        db_with_tables: DatabaseManager,
        mocker: MockerFixture,
    ) -> None:
        """Test connection error when closing the database."""
        # Test that the database manager tries to close the connection,
        # even if an error occurs during close

        # Create a mock connection with an error-raising close method
        mock_conn = mocker.MagicMock()
        mock_conn.close.side_effect = sqlite3.Error("Close error")

        # We need to patch hasattr to make it think __conn exists
        # and also patch the mangled attribute
        original_hasattr = hasattr

        def mock_hasattr(obj: object, name: str) -> bool:
            if obj is db_with_tables and name == "__conn":
                return True
            return original_hasattr(obj, name)

        mocker.patch("builtins.hasattr", mock_hasattr)
        mocker.patch.object(db_with_tables, "_DatabaseManager__conn", mock_conn)

        # Expect the error to be re-raised as per the close() method implementation
        with pytest.raises(sqlite3.Error):
            db_with_tables.close()

        # Verify the close method was called
        mock_conn.close.assert_called_once()

    def test_context_manager_handles_exceptions(
        self,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test that context manager properly handles exceptions."""
        with pytest.raises(ValueError):
            with db_with_tables:
                # This will raise a ValueError inside the context
                raise ValueError("Test error")

        # Connection should still be closed
        assert not hasattr(db_with_tables, "conn") or db_with_tables.conn is None

    def test_table_not_found_error_select(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for SELECT from a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute("SELECT * FROM totally_missing_table")

    def test_table_not_found_error_insert(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for INSERT into a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute(
                "INSERT INTO missing_table (id, name) VALUES (?, ?)", (1, "test")
            )

    def test_table_not_found_error_update(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for UPDATE on a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute("UPDATE missing_table SET name=? WHERE id=?", ("test", 1))

    def test_table_not_found_error_delete(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for DELETE from a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute("DELETE FROM missing_table WHERE id=?", (1,))
