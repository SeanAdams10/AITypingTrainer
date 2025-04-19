"""
API tests for Snippets Library Flask endpoints.
Uses Flask test client and in-memory SQLite DB. All tests are isolated and do not touch prod DB.
"""
import pytest

# NOTE: SQLAlchemy and api_module usage removed for compatibility.
# If you need SQLAlchemy, ensure it is installed and models are defined.

from app import create_app  # Assumes your Flask app factory is in app.py
from api.category_api import category_api
from api.snippet_api import snippet_api
from api.dbviewer_api import bp as dbviewer_bp

def create_test_app():
    """
    Creates a test app instance.
    
    Returns:
        app (Flask): A Flask app instance with testing configuration.
    """
    # Use the standard app factory for testing
    app = create_app({'TESTING': True})
    return app

@pytest.fixture
def flask_client():
    """
    Fixture for Flask test client.
    
    Yields:
        flask_client (Flask test client): A test client instance for the Flask app.
    """
    app = create_test_app()
    # Ensure category and snippet exist for library tests
    from db.database_manager import DatabaseManager
    db = DatabaseManager.get_instance()
    db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'Alpha') ON CONFLICT(category_id) DO NOTHING")
    db.execute_non_query("INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'TestSnippet') ON CONFLICT(snippet_id) DO NOTHING")
    db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc') ON CONFLICT(snippet_id, part_number) DO NOTHING")
    with app.test_client() as flask_client:
        yield flask_client

def test_category_crud(flask_client):
    """
    Test CRUD operations for categories.
    """
    # Create
    r = flask_client.post('/api/categories', json={'name': 'Alpha'})
    assert r.status_code == 201
    cat_id = r.get_json()['category_id']
    # Get
    r = flask_client.get('/api/categories')
    cats = r.get_json()
    assert any(c['name'] == 'Alpha' for c in cats)
    # Edit
    r = flask_client.put('/api/categories/' + str(cat_id), json={'name': 'Beta'})
    assert r.status_code == 200
    assert r.get_json()['name'] == 'Beta'
    # Duplicate
    flask_client.post('/api/categories', json={'name': 'Gamma'})
    r = flask_client.put('/api/categories/' + str(cat_id), json={'name': 'Gamma'})
    assert r.status_code == 400
    # Delete
    r = flask_client.delete('/api/categories/' + str(cat_id))
    assert r.status_code == 204
    # Not found
    r = flask_client.delete('/api/categories/9999')
    assert r.status_code == 400

def test_snippet_crud_and_validation(flask_client):
    """
    Test CRUD and validation for snippets.
    """
    # Setup category
    cat_id = flask_client.post('/api/categories', json={'name': 'Alpha'}).get_json()['category_id']
    # Add snippet
    r = flask_client.post('/api/snippets', json={
        'category_id': cat_id, 'name': 'S1', 'text': 'abc def'
    })
    assert r.status_code == 201
    snip_id = r.get_json()['snippet_id']
    # Get snippets
    r = flask_client.get(f'/api/snippets?category_id={cat_id}')
    snips = r.get_json()
    assert any(s['name'] == 'S1' for s in snips)
    # Edit snippet
    r = flask_client.put(f'/api/snippets/{snip_id}', json={
        'name': 'S1-2', 'text': 'xyz', 'category_id': cat_id
    })
    assert r.status_code == 200
    assert r.get_json()['name'] == 'S1-2'
    # Duplicate name
    flask_client.post('/api/snippets', json={'category_id': cat_id, 'name': 'S2', 'text': 'foo'})
    r = flask_client.put(f'/api/snippets/{snip_id}', json={
        'name': 'S2', 'text': 'bar', 'category_id': cat_id
    })
    assert r.status_code == 400
    # Delete
    r = flask_client.delete(f'/api/snippets/{snip_id}')
    assert r.status_code == 204
    # Validation
    r = flask_client.post('/api/snippets', json={'category_id': cat_id, 'name': '', 'text': 'abc'})
    assert r.status_code == 400
    r = flask_client.post('/api/snippets', json={'category_id': cat_id, 'name': 'S3', 'text': ''})
    assert r.status_code == 400
    # Not found
    r = flask_client.delete('/api/snippets/9999')
    assert r.status_code == 400
