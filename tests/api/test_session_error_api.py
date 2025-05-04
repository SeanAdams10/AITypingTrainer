import pytest
from flask import Flask
from app import create_app
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
        # Insert a category and a snippet with snippet_id=1 for session error tests
        from db.database_manager import DatabaseManager
        db = DatabaseManager.get_instance()
        db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'TestCat') ON CONFLICT(category_id) DO NOTHING")
        db.execute_non_query("INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'TestSnippet') ON CONFLICT(snippet_id) DO NOTHING")
        db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc') ON CONFLICT(snippet_id, part_number) DO NOTHING")
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)

def test_post_session_error_valid(client):
    # Create a session first
    session_data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 10,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(session_data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    err_data = {
        'session_id': session_id,
        'error_type': 'substitution',
        'error_location': 5,
        'error_char': 'x',
        'expected_char': 'y',
        'timestamp': '2025-04-18T12:00:01'
    }
    rv2 = client.post('/api/session_errors', data=json.dumps(err_data), content_type='application/json')
    assert rv2.status_code == 201
    assert rv2.get_json()['success'] is True

def test_post_session_error_invalid(client):
    err_data = {'error_type': 'substitution'}  # Missing required fields
    rv = client.post('/api/session_errors', data=json.dumps(err_data), content_type='application/json')
    assert rv.status_code == 400

def test_get_session_errors_valid(client):
    # Create a session and an error
    session_data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 10,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(session_data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    err_data = {
        'session_id': session_id,
        'error_type': 'substitution',
        'error_location': 5,
        'error_char': 'x',
        'expected_char': 'y',
        'timestamp': '2025-04-18T12:00:01'
    }
    client.post('/api/session_errors', data=json.dumps(err_data), content_type='application/json')
    rv2 = client.get(f'/api/session_errors?session_id={session_id}')
    assert rv2.status_code == 200
    errors = rv2.get_json()
    assert isinstance(errors, list)
    assert errors[0]['error_char'] == 'x'

def test_get_session_errors_missing_param(client):
    rv = client.get('/api/session_errors')
    assert rv.status_code == 400
