"""
Tests for the Database Viewer API endpoints.
Tests listing tables, fetching table data with pagination, sorting, filtering, 
and exporting to CSV.
"""

import os
import json
import pytest
import tempfile
import sys
import csv
from typing import Generator
from io import StringIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from flask import Flask
from api.dbviewer_api import dbviewer_api
from db.database_manager import DatabaseManager


@pytest.fixture
def test_client() -> Generator[Flask, None, None]:
    """Create a Flask test client with the dbviewer_api blueprint."""
    # Create a Flask app for testing
    app = Flask(__name__)
    
    # Create a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True
    
    # Setup database with test data
    db_manager = DatabaseManager(db_path)
    db_manager.init_tables()
    
    # Add some test data
    _populate_test_database(db_manager)
    
    # Make sure to close the database connection
    db_manager.close()
    
    # Register the blueprint
    app.register_blueprint(dbviewer_api)
    
    # Create a test client
    with app.test_client() as client:
        yield client
    
    # Clean up
    os.close(db_fd)
    try:
        os.unlink(db_path)
    except (PermissionError, FileNotFoundError):
        # On Windows, sometimes the file is still in use, so we'll just ignore the error
        pass


def _populate_test_database(db_manager: DatabaseManager) -> None:
    """Add test data to the database."""
    # Add categories
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
    
    # Add snippets
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
    
    # Add snippet parts
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


class TestDatabaseViewerAPI:
    """Tests for the Database Viewer API endpoints."""
    
    def test_list_tables(self, test_client):
        """Test the /api/dbviewer/tables endpoint."""
        response = test_client.get('/api/dbviewer/tables')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'tables' in data
        
        # Check for expected tables
        expected_tables = [
            "categories", "snippets", "snippet_parts", "practice_sessions",
            "session_keystrokes", "session_ngram_speed", "session_ngram_errors"
        ]
        for table in expected_tables:
            assert table in data['tables']
    
    def test_get_table_data_basic(self, test_client):
        """Test basic table data retrieval."""
        response = test_client.get('/api/dbviewer/table?name=categories')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['rows']) == 3
        assert data['total_rows'] == 3
        assert 'category_id' in data['columns']
        assert 'category_name' in data['columns']
    
    def test_get_table_data_pagination(self, test_client):
        """Test table data with pagination."""
        # Test first page with 2 items per page
        response = test_client.get('/api/dbviewer/table?name=categories&page=1&page_size=2')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['rows']) == 2
        assert data['total_rows'] == 3
        assert data['total_pages'] == 2
        assert data['current_page'] == 1
        
        # Test second page
        response = test_client.get('/api/dbviewer/table?name=categories&page=2&page_size=2')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['rows']) == 1
        assert data['total_rows'] == 3
        assert data['total_pages'] == 2
        assert data['current_page'] == 2
    
    def test_get_table_data_sorting(self, test_client):
        """Test table data with sorting."""
        # Test ascending sort by category_name
        response = test_client.get('/api/dbviewer/table?name=categories&sort_by=category_name&sort_order=asc')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        rows = data['rows']
        assert rows[0]['category_name'] == 'Another Category'
        assert rows[2]['category_name'] == 'Test Category 2'
        
        # Test descending sort by category_name
        response = test_client.get('/api/dbviewer/table?name=categories&sort_by=category_name&sort_order=desc')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        rows = data['rows']
        assert rows[0]['category_name'] == 'Test Category 2'
        assert rows[2]['category_name'] == 'Another Category'
    
    def test_get_table_data_filtering(self, test_client):
        """Test table data with filtering."""
        # Test filtering by category_name
        response = test_client.get('/api/dbviewer/table?name=categories&filter_column=category_name&filter_value=Another')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['rows']) == 1
        assert data['rows'][0]['category_name'] == 'Another Category'
    
    def test_get_table_data_errors(self, test_client):
        """Test error handling for table data endpoint."""
        # Test missing table name
        response = test_client.get('/api/dbviewer/table')
        assert response.status_code == 400
        
        # Test nonexistent table
        response = test_client.get('/api/dbviewer/table?name=nonexistent_table')
        assert response.status_code == 404
        
        # Test invalid page number
        response = test_client.get('/api/dbviewer/table?name=categories&page=0')
        assert response.status_code == 400
        
        # Test invalid sort order
        response = test_client.get('/api/dbviewer/table?name=categories&sort_order=invalid')
        assert response.status_code == 400
    
    def test_export_table_to_csv(self, test_client):
        """Test exporting table data to CSV."""
        response = test_client.get('/api/dbviewer/export?name=categories')
        assert response.status_code == 200
        assert response.headers['Content-Type'].startswith('text/csv')
        assert 'attachment; filename="categories.csv"' in response.headers['Content-Disposition']
        
        # Parse CSV data
        csv_data = response.data.decode('utf-8')
        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)
        
        # Check data
        assert len(rows) == 3
        categories = {row['category_name'] for row in rows}
        expected_categories = {'Test Category 1', 'Test Category 2', 'Another Category'}
        assert categories == expected_categories
        
        # Test filtering
        response = test_client.get('/api/dbviewer/export?name=categories&filter_column=category_name&filter_value=Another')
        assert response.status_code == 200
        
        csv_data = response.data.decode('utf-8')
        reader = csv.DictReader(StringIO(csv_data))
        rows = list(reader)
        
        # Check filtered data
        assert len(rows) == 1
        assert 'Another Category' in rows[0]['category_name']
