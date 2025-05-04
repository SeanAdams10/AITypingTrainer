import pytest
import sys
import os
import tempfile
import sqlite3
import json
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from desktop_ui.library_service import LibraryService
import requests
from app import app as flask_app

# This test suite requires the API server to be running
# It verifies that the API correctly processes requests from our LibraryService

@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    db_fd, db_path = tempfile.mkstemp()
    os.environ['DATABASE'] = db_path
    
    # Initialize the database with necessary tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create text_category table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS text_category (
        category_id INTEGER PRIMARY KEY,
        category_name TEXT NOT NULL UNIQUE
    )
    ''')
    
    # Create text_snippets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS text_snippets (
        snippet_id INTEGER PRIMARY KEY,
        category_id INTEGER NOT NULL,
        snippet_name TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES text_category(category_id) ON DELETE CASCADE,
        UNIQUE(category_id, snippet_name)
    )
    ''')
    
    # Create snippet_parts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS snippet_parts (
        part_id INTEGER PRIMARY KEY,
        snippet_id INTEGER NOT NULL,
        part_number INTEGER NOT NULL,
        part_text TEXT NOT NULL,
        FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id) ON DELETE CASCADE,
        UNIQUE(snippet_id, part_number)
    )
    ''')
    
    # Add sample data
    cursor.execute("INSERT INTO text_category (category_name) VALUES ('API Test Category')")
    category_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO text_snippets (category_id, snippet_name) VALUES (?, 'API Test Snippet')",
        (category_id,)
    )
    snippet_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO snippet_parts (snippet_id, part_number, part_text) VALUES (?, 1, 'API Test Content')",
        (snippet_id,)
    )
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def flask_client(temp_db):
    """Create a test client for the Flask app."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def api_service():
    """Create a real LibraryService instance."""
    return LibraryService()


@pytest.mark.api_integration
class TestAPIIntegration:
    """Integration tests that verify LibraryService correctly communicates with API endpoints."""
    
    @patch('desktop_ui.library_service.API_BASE_URL', 'http://localhost:5000')
    def test_get_categories_integration(self, flask_client, api_service):
        """Test that LibraryService can fetch categories from the API."""
        # This requires the API server to be running locally
        try:
            categories = api_service.get_categories()
            assert len(categories) > 0
            assert any(cat.name == 'API Test Category' for cat in categories)
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running - integration test skipped")
    
    @patch('desktop_ui.library_service.API_BASE_URL', 'http://localhost:5000')
    def test_crud_category_integration(self, flask_client, api_service):
        """Test the full CRUD cycle for categories through the API."""
        try:
            # Create a new category
            category_name = f"Test Category {os.urandom(4).hex()}"
            category_id = api_service.add_category(category_name)
            assert category_id is not None
            
            # Verify category was added
            categories = api_service.get_categories()
            assert any(cat.category_id == category_id and cat.name == category_name for cat in categories)
            
            # Update the category
            new_name = f"Updated {category_name}"
            api_service.edit_category(category_id, new_name)
            
            # Verify update
            categories = api_service.get_categories()
            assert any(cat.category_id == category_id and cat.name == new_name for cat in categories)
            
            # Delete the category
            api_service.delete_category(category_id)
            
            # Verify deletion
            categories = api_service.get_categories()
            assert not any(cat.category_id == category_id for cat in categories)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running - integration test skipped")
        except Exception as e:
            pytest.fail(f"API integration test failed: {str(e)}")
    
    @patch('desktop_ui.library_service.API_BASE_URL', 'http://localhost:5000')
    def test_crud_snippet_integration(self, flask_client, api_service):
        """Test the full CRUD cycle for snippets through the API."""
        try:
            # First create a category for our snippets
            category_name = f"Snippet Test Category {os.urandom(4).hex()}"
            category_id = api_service.add_category(category_name)
            
            # Create a new snippet
            snippet_name = f"Test Snippet {os.urandom(4).hex()}"
            snippet_content = "This is test content for API integration testing."
            snippet_id = api_service.add_snippet(category_id, snippet_name, snippet_content)
            assert snippet_id is not None
            
            # Verify snippet was added
            snippets = api_service.get_snippets(category_id)
            assert any(s.snippet_id == snippet_id and s.name == snippet_name for s in snippets)
            
            # Get snippet content
            parts = api_service.get_snippet_parts(snippet_id)
            assert len(parts) > 0
            assert ''.join(parts) == snippet_content
            
            # Update the snippet
            new_name = f"Updated {snippet_name}"
            new_content = "This content has been updated through the API."
            api_service.edit_snippet(snippet_id, new_name, new_content)
            
            # Verify update
            snippets = api_service.get_snippets(category_id)
            assert any(s.snippet_id == snippet_id and s.name == new_name for s in snippets)
            
            parts = api_service.get_snippet_parts(snippet_id)
            assert ''.join(parts) == new_content
            
            # Delete the snippet
            api_service.delete_snippet(snippet_id)
            
            # Verify deletion
            snippets = api_service.get_snippets(category_id)
            assert not any(s.snippet_id == snippet_id for s in snippets)
            
            # Clean up by deleting the category
            api_service.delete_category(category_id)
            
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running - integration test skipped")
        except Exception as e:
            pytest.fail(f"API integration test failed: {str(e)}")
