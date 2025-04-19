import pytest
from flask import Flask
from app import create_app
from api.session_api import session_api
from api.keystroke_api import keystroke_api
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
        # Insert a category and a snippet with snippet_id=1 for keystroke tests
        from db.database_manager import DatabaseManager
        db = DatabaseManager.get_instance()
        db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'TestCat') ON CONFLICT(category_id) DO NOTHING")
        db.execute_non_query("INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'TestSnippet') ON CONFLICT(snippet_id) DO NOTHING")
        db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc') ON CONFLICT(snippet_id, part_number) DO NOTHING")
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)

def test_post_keystroke_valid(client):
    # Create a session first
    session_data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 10,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(session_data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    kdata = {
        'session_id': session_id,
        'keystroke_time': '2025-04-18T12:00:00',
        'keystroke_char': 'a',
        'expected_char': 'a',
        'is_correct': True,
        'time_since_previous': 100
    }
    rv2 = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    assert rv2.status_code == 201
    assert rv2.get_json()['success'] is True

def test_post_keystroke_invalid(client):
    kdata = {'keystroke_char': 'a'}  # Missing required fields
    rv = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    assert rv.status_code == 400

def test_get_keystrokes_valid(client):
    # Create a session and a keystroke
    session_data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 10,
        'practice_type': 'beginning'
    }
    rv = client.post('/api/sessions', data=json.dumps(session_data), content_type='application/json')
    session_id = rv.get_json()['session_id']
    kdata = {
        'session_id': session_id,
        'keystroke_time': '2025-04-18T12:00:00',
        'keystroke_char': 'a',
        'expected_char': 'a',
        'is_correct': True,
        'time_since_previous': 100
    }
    client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    rv2 = client.get(f'/api/keystrokes?session_id={session_id}')
    assert rv2.status_code == 200
    keystrokes = rv2.get_json()
    assert isinstance(keystrokes, list)
    assert keystrokes[0]['keystroke_char'] == 'a'

def test_get_keystrokes_missing_param(client):
    rv = client.get('/api/keystrokes')
    assert rv.status_code == 400
