"""
Tests for database exception handling in DatabaseManager.
"""
import sqlite3

import pytest
from pytest_mock import MockerFixture

from db.database_manager import DatabaseManager
from db.exceptions import (
    ConnectionError,
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
)
from tests.helpers.db_helpers import create_connection_error_db


class TestDatabaseExceptions:
    """Test cases for database exception handling."""

    def test_connection_error(self) -> None:
        """Test connection error when database cannot be opened."""
        # Use helper function to create a path that will cause a connection error
        db_path = create_connection_error_db()
        with pytest.raises(ConnectionError):
            DatabaseManager(db_path)

    def test_foreign_key_violation(self, db_with_tables: DatabaseManager) -> None:
        """Test foreign key constraint violation."""
        # db_with_tables already has tables initialized
        
        # Try to insert a snippet with a non-existent category_id
        with pytest.raises(ForeignKeyError):
            db_with_tables.execute(
                "INSERT INTO snippets (snippet_id, category_id, snippet_name, content) "
                "VALUES (?, ?, ?, ?)",
                (1, 999, "test_snippet", "test content"),  # category_id 999 doesn't exist
            )

    def test_schema_error(self, db_with_tables: DatabaseManager) -> None:
        """Test schema-related errors."""
        # Try to query a non-existent table
        with pytest.raises(SchemaError):
            db_with_tables.fetchall("SELECT * FROM non_existent_table")
        
        # Try to query a non-existent column
        with pytest.raises(SchemaError):
            db_with_tables.fetchall("SELECT non_existent_column FROM categories")

    def test_type_error(self, db_with_tables: DatabaseManager) -> None:
        """Test type-related errors."""
        # Try to insert a row with wrong parameter types
        with pytest.raises(DatabaseTypeError):
            # Passing a dictionary instead of a tuple for params
            db_with_tables.execute(
                "INSERT INTO categories (category_name) VALUES (?)",
                {"name": "test"},  # Wrong type, should be a tuple
            )

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

    def test_integrity_error(self, db_with_tables: DatabaseManager) -> None:
        """Test other integrity errors."""
        # This will raise an IntegrityError that's not a foreign key or constraint violation
        with pytest.raises(IntegrityError):
            # Try to insert a duplicate primary key
            db_with_tables.execute("PRAGMA foreign_keys=OFF")
            db_with_tables.execute(
                "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                (1, "test1"),
            )
            db_with_tables.execute(
                "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                (1, "test2"),  # Duplicate primary key
            )

    def test_general_database_error(
        self,
        db_with_tables: DatabaseManager,
        mocker: MockerFixture,
    ) -> None:
        """Test general database errors."""
        # Mock cursor to raise a generic DatabaseError
        mock_cursor = mocker.MagicMock()
        mock_cursor.execute.side_effect = sqlite3.DatabaseError(
            "Generic database error"
        )
        mocker.patch.object(db_with_tables, "_get_cursor", return_value=mock_cursor)
        
        with pytest.raises(DatabaseError):
            db_with_tables.fetchall("SELECT * FROM categories")

    def test_connection_error_on_close(
        self,
        db_with_tables: DatabaseManager,
        mocker: MockerFixture,
    ) -> None:
        """Test connection error when closing the database."""
        # Mock the connection's close method to raise an error
        mocker.patch.object(
            db_with_tables.conn,
            "close",
            side_effect=sqlite3.Error("Close error"),
        )
        
        # Should not raise an exception
        db_with_tables.close()
        assert not hasattr(db_with_tables, "conn") or db_with_tables.conn is None

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
