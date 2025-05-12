"""
Unit tests for the DatabaseViewerService class.
Tests listing tables, fetching table data with pagination, sorting, filtering,
and exporting to CSV.
"""

import os
import pytest
import csv
import tempfile
from typing import List, Dict, Any, Generator
from io import StringIO

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from db.database_manager import DatabaseManager
from services.database_viewer_service import DatabaseViewerService, TableNotFoundError, InvalidParameterError


@pytest.fixture
def db_manager(tmp_path) -> Generator[DatabaseManager, None, None]:
    """Create a test database with sample data for testing."""
    db_path = str(tmp_path / "test_db_viewer.db")
    db_manager = DatabaseManager(db_path)
    
    # Initialize tables
    db_manager.init_tables()
    
    # Add sample data for categories
    db_manager.execute(
        "INSERT INTO categories (category_name) VALUES (?)",
        ("Test Category 1",),
        commit=True
    )
    db_manager.execute(
        "INSERT INTO categories (category_name) VALUES (?)",
        ("Test Category 2",),
        commit=True
    )
    db_manager.execute(
        "INSERT INTO categories (category_name) VALUES (?)",
        ("Another Category",),
        commit=True
    )
    
    # Add sample data for snippets
    cat1_id = 1
    cat2_id = 2
    db_manager.execute(
        "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
        (cat1_id, "Snippet 1"),
        commit=True
    )
    db_manager.execute(
        "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
        (cat1_id, "Snippet 2"),
        commit=True
    )
    db_manager.execute(
        "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
        (cat2_id, "Another Snippet"),
        commit=True
    )
    
    # Add sample snippet parts
    snippet1_id = 1
    snippet2_id = 2
    db_manager.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snippet1_id, 1, "Test content for snippet 1"),
        commit=True
    )
    db_manager.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
        (snippet2_id, 1, "Test content for snippet 2"),
        commit=True
    )
    
    yield db_manager
    db_manager.close()


@pytest.fixture
def service(db_manager) -> DatabaseViewerService:
    """Create a DatabaseViewerService instance with the test database."""
    return DatabaseViewerService(db_manager)


class TestDatabaseViewerService:
    """Tests for the DatabaseViewerService class."""
    
    def test_list_tables(self, service: DatabaseViewerService) -> None:
        """Test that list_tables returns all tables in the database."""
        tables = service.list_tables()
        # Check for core tables that should be present
        expected_tables = [
            "categories", "snippets", "snippet_parts", "practice_sessions", 
            "session_keystrokes", "session_ngram_speed", "session_ngram_errors"
        ]
        for table in expected_tables:
            assert table in tables
    
    def test_get_table_data_basic(self, service: DatabaseViewerService) -> None:
        """Test retrieving table data without pagination/sorting."""
        data = service.get_table_data("categories")
        assert len(data["rows"]) == 3
        assert data["total_rows"] == 3
        assert "category_id" in data["columns"]
        assert "category_name" in data["columns"]
    
    def test_get_table_data_pagination(self, service: DatabaseViewerService) -> None:
        """Test pagination of table data."""
        # Test first page with 2 items per page
        data = service.get_table_data("categories", page=1, page_size=2)
        assert len(data["rows"]) == 2
        assert data["total_rows"] == 3
        assert data["total_pages"] == 2
        assert data["current_page"] == 1
        
        # Test second page
        data = service.get_table_data("categories", page=2, page_size=2)
        assert len(data["rows"]) == 1
        assert data["total_rows"] == 3
        assert data["total_pages"] == 2
        assert data["current_page"] == 2
    
    def test_get_table_data_sorting(self, service: DatabaseViewerService) -> None:
        """Test sorting of table data."""
        # Test ascending sort by category_name
        data = service.get_table_data("categories", sort_by="category_name", sort_order="asc")
        assert data["rows"][0]["category_name"] == "Another Category"
        assert data["rows"][2]["category_name"] == "Test Category 2"
        
        # Test descending sort by category_name
        data = service.get_table_data("categories", sort_by="category_name", sort_order="desc")
        assert data["rows"][0]["category_name"] == "Test Category 2"
        assert data["rows"][2]["category_name"] == "Another Category"
    
    def test_get_table_data_filtering(self, service: DatabaseViewerService) -> None:
        """Test filtering of table data."""
        # Test filtering by category_name
        data = service.get_table_data("categories", filter_column="category_name", filter_value="Another")
        assert len(data["rows"]) == 1
        assert data["rows"][0]["category_name"] == "Another Category"
        
        # Test filtering by category_id
        data = service.get_table_data("categories", filter_column="category_id", filter_value="1")
        assert len(data["rows"]) == 1
        assert data["rows"][0]["category_id"] == 1
    
    def test_get_table_data_nonexistent_table(self, service: DatabaseViewerService) -> None:
        """Test that appropriate error is raised for nonexistent table."""
        with pytest.raises(TableNotFoundError):
            service.get_table_data("nonexistent_table")
    
    def test_get_table_data_invalid_parameters(self, service: DatabaseViewerService) -> None:
        """Test that appropriate errors are raised for invalid parameters."""
        # Invalid page number
        with pytest.raises(InvalidParameterError):
            service.get_table_data("categories", page=0)
        
        # Invalid sort order
        with pytest.raises(InvalidParameterError):
            service.get_table_data("categories", sort_order="invalid")
        
        # Invalid sort column
        with pytest.raises(InvalidParameterError):
            service.get_table_data("categories", sort_by="nonexistent_column")
        
        # Invalid filter column
        with pytest.raises(InvalidParameterError):
            service.get_table_data("categories", filter_column="nonexistent_column", filter_value="test")
    
    def test_get_table_schema(self, service: DatabaseViewerService) -> None:
        """Test that get_table_schema returns correct schema for a table."""
        schema = service.get_table_schema("categories")
        assert len(schema) == 2
        assert schema[0]["name"] == "category_id"
        assert schema[1]["name"] == "category_name"
        
        with pytest.raises(TableNotFoundError):
            service.get_table_schema("nonexistent_table")
    
    def test_export_table_data_to_csv(self, service: DatabaseViewerService) -> None:
        """Test exporting table data to CSV."""
        output = StringIO()
        service.export_table_to_csv("categories", output)
        output.seek(0)
        
        reader = csv.reader(output)
        rows = list(reader)
        
        # Check header row and data rows
        assert len(rows) == 4  # Header + 3 data rows
        assert rows[0] == ["category_id", "category_name"]
        
        # Test with filtering
        output = StringIO()
        service.export_table_to_csv("categories", output, filter_column="category_name", filter_value="Another")
        output.seek(0)
        
        reader = csv.reader(output)
        rows = list(reader)
        
        assert len(rows) == 2  # Header + 1 filtered data row
        assert "Another" in rows[1][1]  # Should contain "Another Category"
