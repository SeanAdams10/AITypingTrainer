"""Tests for database exception handling in DatabaseManager."""

import pytest

from db.database_manager import DatabaseManager
from db.exceptions import ConstraintError, ForeignKeyError, SchemaError, TableNotFoundError


class TestDatabaseExceptions:
    """Test cases for database exception handling."""

    def test_foreign_key_violation(self, db_with_tables: DatabaseManager) -> None:
        """Test foreign key constraint violation."""
        # db_with_tables already has tables initialized

        # Try to insert a snippet with a non-existent category_id
        with pytest.raises(ForeignKeyError):
            db_with_tables.execute(
                query="INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
                params=(1, 999, "test_snippet"),  # category_id 999 doesn't exist
            )

    def test_schema_error(self, db_with_tables: DatabaseManager) -> None:
        """Test schema-related errors with bad column names."""
        # First, create a valid category to ensure the table exists and has data
        db_with_tables.execute(
            query="INSERT INTO categories (category_id, category_name) VALUES (?,?)",
            params=(
                "1",
                "Test Category",
            ),
        )

        # Try to update a valid table with a non-existent column
        with pytest.raises(SchemaError):
            db_with_tables.execute(
                query="UPDATE categories SET non_existent_column = 'test' "
                "WHERE category_name = 'Test Category'"
            )

    def test_constraint_violation(self, db_with_tables: DatabaseManager) -> None:
        """Test constraint violations (NOT NULL, UNIQUE)."""
        # Test NOT NULL constraint
        with pytest.raises(ConstraintError):
            db_with_tables.execute(
                query="INSERT INTO categories (category_id) VALUES (?)",
                params=(1,),  # Missing required category_name
            )

        # Test UNIQUE constraint
        db_with_tables.execute(
            query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            params=("1", "test_category"),
        )
        with pytest.raises(ConstraintError):
            db_with_tables.execute(
                query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                params=("1", "test_category"),
            )

    def test_table_not_found_error_select(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for SELECT from a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute(query="SELECT * FROM totally_missing_table")

    def test_table_not_found_error_insert(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for INSERT into a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute(
                query="INSERT INTO missing_table (id, name) VALUES (?, ?)", params=(1, "test")
            )

    def test_table_not_found_error_update(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for UPDATE on a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute(query="UPDATE missing_table SET name=? WHERE id=?", params=("test", 1))

    def test_table_not_found_error_delete(self, db_with_tables: DatabaseManager) -> None:
        """Test TableNotFoundError is raised for DELETE from a non-existent table."""
        with pytest.raises(TableNotFoundError):
            db_with_tables.execute(query="DELETE FROM missing_table WHERE id=?", params=(1,))
