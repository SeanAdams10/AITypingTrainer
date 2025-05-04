import pytest
import os
import sys
import sqlite3
import json
from typing import Generator

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))) 

from app import create_app
from db.database_manager import DatabaseManager
from db import init_db


@pytest.fixture(scope="class")
def test_db_path(tmp_path_factory):
    """Create a temporary database path for all tests in the class."""
    db_dir = tmp_path_factory.mktemp("test_db")
    db_path = db_dir / "test_library_web.db"
    return str(db_path)


@pytest.fixture(scope="class")
def test_database_manager(test_db_path, monkeypatch):
    """Create and initialize a database manager with a test database for all tests in the class."""
    # Get the singleton instance and set the test path
    db_manager = DatabaseManager.get_instance()
    original_path = db_manager.db_path
    db_manager.set_db_path(test_db_path)
    
    # Initialize database tables
    with db_manager.get_connection() as conn:
        init_db()
        
        cursor = conn.cursor()
        
        # Add test category
        cursor.execute("INSERT INTO text_category (category_name) VALUES ('Test Category 1')")
        category_id = cursor.lastrowid
        
        # Add test snippet
        cursor.execute(
            "INSERT INTO text_snippets (category_id, snippet_name) VALUES (?, 'Test Snippet 1')",
            (category_id,)
        )
        snippet_id = cursor.lastrowid
        
        # Add test snippet content
        cursor.execute(
            "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, 1, 'Test content for snippet 1')",
            (snippet_id,)
        )
        
        conn.commit()
    
    yield db_manager
    
    # Teardown - restore original path
    db_manager.set_db_path(original_path)


@pytest.fixture(scope="function")
def app(test_database_manager):
    """Create a Flask app with the test database."""
    app = create_app({
        'TESTING': True,
        'DATABASE': test_database_manager.db_path
    })
    yield app


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the Flask app with the test database."""
    with app.test_client() as client:
        with app.app_context():
            yield client


class TestLibraryAPIIntegration:
    """Tests for the Library API integration."""
    
    def test_api_categories_endpoint(self, client):
        """Test that the API endpoint for categories returns proper data."""
        response = client.get('/api/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['categories']) > 0
        assert any(c['category_name'] == 'Test Category 1' for c in data['categories'])
    
    def test_api_snippets_endpoint(self, client):
        """Test that the API endpoint for snippets returns proper data."""
        # First get category ID
        response = client.get('/api/categories')
        categories = json.loads(response.data)['categories']
        category_id = next((c['category_id'] for c in categories if c['category_name'] == 'Test Category 1'), None)
        assert category_id is not None
        
        # Then get snippets for this category
        response = client.get(f'/api/snippets?category_id={category_id}')
        assert response.status_code == 200
        snippets = json.loads(response.data)
        assert len(snippets) > 0
        assert any(s['snippet_name'] == 'Test Snippet 1' for s in snippets)
    
    def test_api_add_category(self, client):
        """Test adding a category through the API."""
        response = client.post('/api/categories', 
                             json={'name': 'New Test Category'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['category_name'] == 'New Test Category'
        
        # Verify category was added
        response = client.get('/api/categories')
        categories = json.loads(response.data)['categories']
        assert any(c['category_name'] == 'New Test Category' for c in categories)
    
    def test_api_add_snippet(self, client):
        """Test adding a snippet through the API."""
        # First get category ID
        response = client.get('/api/categories')
        categories = json.loads(response.data)['categories']
        category_id = next((c['category_id'] for c in categories if c['category_name'] == 'Test Category 1'), None)
        assert category_id is not None
        
        # Add a snippet
        response = client.post('/api/snippets', 
                             json={
                                 'category_id': category_id,
                                 'snippet_name': 'New Test Snippet',
                                 'content': 'This is some test content for the new snippet.'
                             })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify snippet was added
        response = client.get(f'/api/snippets?category_id={category_id}')
        snippets = json.loads(response.data)
        assert any(s['snippet_name'] == 'New Test Snippet' for s in snippets)
