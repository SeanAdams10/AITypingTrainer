print('DEBUG: Top of test_drill_config_api.py')
"""
Pytest tests for DrillConfig API endpoints.
Covers: categories, snippets by category, last session info, snippet length.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import pytest
from app import create_app
from api.category_api import category_api
from api.snippet_api import snippet_api
from db.database_manager import DatabaseManager

@pytest.fixture
def client(tmp_path):
    print('DEBUG: Entering client fixture')
    db_path = tmp_path / "test_drill_config_api.db"
    db = DatabaseManager.get_instance()
    db.set_db_path(str(db_path))
    db.init_db()
    # Insert sample data, and ensure snippet_id=1 exists for session tests
    db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'Alpha'), (2, 'Beta') ON CONFLICT(category_id) DO NOTHING")
    db.execute_non_query("INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'First'), (2, 1, 'Second'), (3, 2, 'Other') ON CONFLICT(snippet_id) DO NOTHING")
    db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc'), (1, 1, 'defg'), (2, 0, 'xyz') ON CONFLICT(snippet_id, part_number) DO NOTHING")
    db.execute_non_query("INSERT INTO practice_sessions (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time) VALUES ('sess1', 1, 0, 4, '2024-04-01T10:00:00'), ('sess2', 1, 4, 7, '2024-04-02T10:00:00')")
    app = create_app({'TESTING': True})
    yield app.test_client()

import traceback

def test_get_categories(client):
    print('DEBUG: Entering test_get_categories')
    try:
        resp = client.get('/api/categories')
        print('DEBUG /api/categories response:', resp.status_code, resp.data)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert "categories" in data
        categories = data["categories"]
        assert isinstance(categories, list)
        assert any(cat['category_name'] == 'Alpha' for cat in categories)
        assert any(cat['category_name'] == 'Beta' for cat in categories)
    except Exception as e:
        print('EXCEPTION in test_get_categories:', e)
        traceback.print_exc()
        raise

def test_get_snippets_by_category(client):
    resp = client.get('/api/snippets?category_id=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert data[0]['snippet_name'] == 'First'
    assert data[1]['snippet_name'] == 'Second'

def test_get_last_session_info(client):
    resp = client.get('/api/session/info?snippet_id=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['last_start_index'] == 4
    assert data['last_end_index'] == 7
    assert data['snippet_length'] == 7
    # For snippet with no sessions
    resp2 = client.get('/api/session/info?snippet_id=2')
    data2 = resp2.get_json()
    assert data2['last_start_index'] is None
    assert data2['last_end_index'] is None
    assert data2['snippet_length'] == 3

def test_handles_missing_and_invalid(client):
    # Nonexistent category
    resp = client.get('/api/snippets?category_id=999')
    assert resp.status_code == 200
    assert resp.get_json() == []
    # Nonexistent snippet
    resp2 = client.get('/api/session/info?snippet_id=999')
    data2 = resp2.get_json()
    assert data2['last_start_index'] is None
    assert data2['last_end_index'] is None
    assert data2['snippet_length'] == 0
    # Missing params
    resp3 = client.get('/api/snippets')
    assert resp3.status_code == 400
    resp4 = client.get('/api/session/info')
    assert resp4.status_code == 400
