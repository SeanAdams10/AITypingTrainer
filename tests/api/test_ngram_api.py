import pytest
from flask import Flask
from app import create_app
from api.category_api import category_api
from api.session_api import session_api
import tempfile
import os
import json

@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
    })
    from db import init_db
    with app.app_context():
        init_db()
        # Insert a category and a snippet with snippet_id=1 for ngram tests
        from db.database_manager import DatabaseManager
        db = DatabaseManager.get_instance()
        db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'TestCat') ON CONFLICT(category_id) DO NOTHING")
        db.execute_non_query("INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'TestSnippet') ON CONFLICT(snippet_id) DO NOTHING")
        db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc') ON CONFLICT(snippet_id, part_number) DO NOTHING")
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)

def test_get_ngrams_valid(client):
    # Create a session first
    session_data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 10,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(session_data), content_type='application/json')
    if rv.status_code != 201:
        print('DEBUG: Session creation failed:', rv.status_code, rv.data)
    session_id = rv.get_json()['session_id']
    rv2 = client.get(f'/api/ngrams?session_id={session_id}')
    assert rv2.status_code == 200
    ngrams = rv2.get_json()
    assert isinstance(ngrams, list)
    # Each ngram result should have ngram_size, speed_results, error_results
    for result in ngrams:
        assert 'ngram_size' in result
        assert 'speed_results' in result
        assert 'error_results' in result

def test_get_ngrams_missing_param(client):
    rv = client.get('/api/ngrams')
    assert rv.status_code == 400
