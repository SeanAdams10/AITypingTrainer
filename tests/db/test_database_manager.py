"""
Tests for the DatabaseManager class.

This module contains comprehensive tests for the DatabaseManager class,
verifying its functionality, error handling, and edge cases.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import pytest
from pytest_mock import MockerFixture

from db.database_manager import DatabaseManager
from db.exceptions import (
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    DBConnectionError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
    TableNotFoundError,
)

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
    return DatabaseManager(temp_db_path)


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
        db_manager.execute(
            f"INSERT INTO {TEST_TABLE_NAME} VALUES (?, ?, ?, ?)",
            row
        )
    
    return db_manager


class TestDatabaseManagerInitialization:
    """Test cases for DatabaseManager initialization and basic functionality."""
    
    def test_init_with_memory_db(self) -> None:
        """Test initialization with in-memory database."""
        with DatabaseManager(":memory:") as db:
            assert db is not None
            # Verify we can execute a simple query
            result = db.fetchone("SELECT 1")
            assert result is not None
            assert result[0] == 1
    
    def test_init_with_temp_file(self, temp_db_path: str) -> None:
        """Test initialization with a temporary file database."""
        with DatabaseManager(temp_db_path) as db:
            assert db is not None
            # Verify the file was created
            assert os.path.exists(temp_db_path)
    
    def test_init_with_none_uses_memory(self) -> None:
        """Test that passing None as db_path uses in-memory database."""
        with DatabaseManager() as db:
            assert db is not None
            # Verify we can execute a simple query
            result = db.fetchone("SELECT 1")
            assert result is not None
    
    def test_init_with_invalid_path_raises_error(self) -> None:
        """Test that an invalid path raises a DBConnectionError."""
        with pytest.raises(DBConnectionError):
            DatabaseManager("/invalid/path/database.db")
    
    def test_context_manager_cleans_up(self, temp_db_path: str) -> None:
        """Test that the context manager properly cleans up resources."""
        with DatabaseManager(temp_db_path) as db:
            # Do something with the database
            db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        
        # The database file should still exist
        assert os.path.exists(temp_db_path)
        
        # But we shouldn't be able to use the connection anymore
        with pytest.raises(DBConnectionError):
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
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (TEST_TABLE_NAME,)
        )
        assert result is not None
        assert result[0] == TEST_TABLE_NAME
    
    def test_execute_insert(self, initialized_db: DatabaseManager) -> None:
        """Test executing an INSERT statement."""
        # Insert a new row
        initialized_db.execute(
            f"INSERT INTO {TEST_TABLE_NAME} (id, name, age, email) VALUES (?, ?, ?, ?)",
            (4, "David", 40, "david@example.com")
        )
        
        # Verify the row was inserted
        result = initialized_db.fetchone(
            f"SELECT name, age, email FROM {TEST_TABLE_NAME} WHERE id = ?",
            (4,)
        )
        assert result is not None
        assert result["name"] == "David"
        assert result["age"] == 40
        assert result["email"] == "david@example.com"
    
    def test_fetchone_returns_none_for_no_results(self, initialized_db: DatabaseManager) -> None:
        """Test that fetchone returns None when no results are found."""
        result = initialized_db.fetchone(
            f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?",
            (999,)
        )
        assert result is None
    
    def test_fetchall_returns_all_results(self, initialized_db: DatabaseManager) -> None:
        """Test that fetchall returns all matching rows."""
        results = initialized_db.fetchall(
            f"SELECT * FROM {TEST_TABLE_NAME} ORDER BY id"
        )
        
        assert len(results) == len(TEST_DATA)
        for i, row in enumerate(results):
            assert row["id"] == TEST_DATA[i][0]
            assert row["name"] == TEST_DATA[i][1]
            assert row["age"] == TEST_DATA[i][2]
            assert row["email"] == TEST_DATA[i][3]
    
    def test_fetchall_returns_empty_list_for_no_results(self, initialized_db: DatabaseManager) -> None:
        """Test that fetchall returns an empty list when no results are found."""
        results = initialized_db.fetchall(
            f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?",
            (999,)
        )
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
            db_manager.execute(
                "INSERT INTO child (id, parent_id, name) VALUES (1, 999, 'test')"
            )
    
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
        db_manager.execute(
            "INSERT INTO test_unique (id, email) VALUES (1, 'test@example.com')"
        )
        
        # Try to insert duplicate email
        with pytest.raises(ConstraintError):
            db_manager.execute(
                "INSERT INTO test_unique (id, email) VALUES (2, 'test@example.com')"
            )
    
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
    
    def test_database_type_error(self, initialized_db: DatabaseManager) -> None:
        """Test that type errors in query parameters raise DatabaseTypeError."""
        with pytest.raises(DatabaseTypeError):
            # Pass invalid parameter type (should be int, not str)
            initialized_db.execute(
                f"SELECT * FROM {TEST_TABLE_NAME} WHERE id = ?",
                ("not_an_integer",)
            )


class TestTransactionHandling:
    """Test cases for transaction handling in DatabaseManager."""
    
    def test_commit_transaction(self, db_manager: DatabaseManager) -> None:
        """Test that changes are committed after commit()."""
        # Create a test table
        db_manager.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # Start a transaction
        db_manager.begin_transaction()
        
        # Insert a row
        db_manager.execute("INSERT INTO test (id, name) VALUES (1, 'test')")
        
        # Verify the row is visible within the transaction
        result = db_manager.fetchone("SELECT name FROM test WHERE id = 1")
        assert result is not None
        assert result[0] == "test"
        
        # Commit the transaction
        db_manager.commit_transaction()
        
        # Verify the row is still visible after commit
        result = db_manager.fetchone("SELECT name FROM test WHERE id = 1")
        assert result is not None
        assert result[0] == "test"
    
    def test_rollback_transaction(self, db_manager: DatabaseManager) -> None:
        """Test that changes are rolled back after rollback()."""
        # Create a test table
        db_manager.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # Start a transaction
        db_manager.begin_transaction()
        
        # Insert a row
        db_manager.execute("INSERT INTO test (id, name) VALUES (1, 'test')")
        
        # Verify the row is visible within the transaction
        result = db_manager.fetchone("SELECT name FROM test WHERE id = 1")
        assert result is not None
        assert result[0] == "test"
        
        # Rollback the transaction
        db_manager.rollback_transaction()
        
        # Verify the row is no longer visible after rollback
        result = db_manager.fetchone("SELECT name FROM test WHERE id = 1")
        assert result is None
    
    def test_context_manager_commits_on_success(self, db_manager: DatabaseManager) -> None:
        """Test that the context manager commits on successful execution."""
        # Create a test table
        db_manager.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # Use a context manager
        with db_manager:
            db_manager.execute("INSERT INTO test (id, name) VALUES (1, 'test')")
        
        # Verify the row was committed
        result = db_manager.fetchone("SELECT name FROM test WHERE id = 1")
        assert result is not None
        assert result[0] == "test"
    
    def test_context_manager_rolls_back_on_exception(self, db_manager: DatabaseManager) -> None:
        """Test that the context manager rolls back on exception."""
        # Create a test table
        db_manager.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        
        # Use a context manager that raises an exception
        try:
            with db_manager:
                db_manager.execute("INSERT INTO test (id, name) VALUES (1, 'test')")
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify the row was not committed
        result = db_manager.fetchone("SELECT name FROM test WHERE id = 1")
        assert result is None
