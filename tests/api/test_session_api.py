import pytest
from flask import Flask
from app import create_app
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
    # Ensure all tables are created for the test DB
    from db import init_db
    with app.app_context():
        from db import init_db
        init_db()
        # Insert a category and a snippet with snippet_id=1 for session tests
        from db.database_manager import DatabaseManager
        db = DatabaseManager.get_instance()
        db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'TestCat') ON CONFLICT(category_id) DO NOTHING")
        db.execute_non_query("INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'TestSnippet') ON CONFLICT(snippet_id) DO NOTHING")
        db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc') ON CONFLICT(snippet_id, part_number) DO NOTHING")
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)

def test_create_session_valid(client):
    data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 100,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(data), content_type='application/json')
    if rv.status_code != 201:
        print('DEBUG: Session creation failed:', rv.status_code, rv.data)
    assert rv.status_code == 201
    resp = rv.get_json()
    assert 'session_id' in resp

def test_create_session_invalid(client):
    data = {'snippet_index_start': 0}
    rv = client.post('/api/sessions', data=json.dumps(data), content_type='application/json')
    assert rv.status_code == 400

def test_get_session_not_found(client):
    rv = client.get('/api/sessions/nonexistent')
    assert rv.status_code == 404

def test_create_and_get_session(client):
    data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 100,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    rv2 = client.get(f'/api/sessions/{session_id}')
    assert rv2.status_code == 200
    session = rv2.get_json()
    assert session['snippet_id'] == 1
    assert session['snippet_index_start'] == 0
    assert session['snippet_index_end'] == 100

def test_update_session_valid(client):
    data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 100,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    update = {
        'end_time': '2025-04-18T12:00:00',
        'total_time': 30.5,
        'session_wpm': 60.0,
        'session_cpm': 320.0,
        'expected_chars': 100,
        'actual_chars': 98,
        'errors': 2,
        'accuracy': 98.0
    }
    rv2 = client.put(f'/api/sessions/{session_id}', data=json.dumps(update), content_type='application/json')
    assert rv2.status_code == 200
    rv3 = client.get(f'/api/sessions/{session_id}')
    session = rv3.get_json()
    assert session['total_time'] == 30.5
    assert session['errors'] == 2

def test_update_session_invalid(client):
    data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 100,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    update = {'end_time': 'bad-date'}  # Missing required fields
    rv2 = client.put(f'/api/sessions/{session_id}', data=json.dumps(update), content_type='application/json')
    assert rv2.status_code == 400
