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
        # Ensure all tables are created in the temp DB
        from db import db_manager
        db_manager.set_db_path(db_path)
        db_manager.init_db()
        db_manager.initialize_database()
        # Insert a category and a snippet with snippet_id=1 for keystroke tests using model logic
        from models.category import Category
        from models.snippet import Snippet
        from db.database_manager import DatabaseManager
        if not Category.get_by_id(1):
            Category(category_id=1, name='TestCat').save()
        if not Snippet.get_by_id(1):
            Snippet(snippet_id=1, category_id=1, snippet_name='TestSnippet', content='abc').save()
        # Ensure snippet_parts table has required part
        db = DatabaseManager.get_instance()
        parts = db.execute_query("SELECT * FROM snippet_parts WHERE snippet_id = ? AND part_number = ?", (1, 0))
        if not parts:
            db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)", (1, 0, 'abc'))


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

import string
import itertools
import time

@pytest.mark.parametrize("field,value", [
    ("keystroke_char", ""),
    ("keystroke_char", "\u20ac"), # non-ASCII
    ("expected_char", "\t"), # control char
    ("session_id", "not-a-uuid"),
    ("session_id", "99999999-9999-9999-9999-999999999999"), # non-existent
    ("is_correct", None),
    ("time_since_previous", -1),
    ("time_since_previous", 2**31),
])
def test_post_keystroke_edge_cases(client, field, value):
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
    kdata[field] = value
    # If session_id is the field, override
    if field == "session_id":
        kdata["session_id"] = value
    rv = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    assert rv.status_code in (400, 404)

def test_post_keystroke_sql_injection(client):
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
        'keystroke_char': "a'; DROP TABLE keystrokes;--",
        'expected_char': 'a',
        'is_correct': True,
        'time_since_previous': 100
    }
    rv = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    assert rv.status_code in (201, 400)

def test_post_keystroke_malformed_json(client):
    rv = client.post('/api/keystrokes', data="{not: valid,}", content_type='application/json')
    assert rv.status_code == 400

def test_post_keystroke_large_payload(client):
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
        'keystroke_char': 'a'*10000,
        'expected_char': 'a',
        'is_correct': True,
        'time_since_previous': 100
    }
    rv = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    assert rv.status_code in (201, 400)

def test_post_duplicate_keystroke(client):
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
    rv1 = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    rv2 = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
    assert rv2.status_code in (201, 400)

def test_post_keystrokes_rapid_fire(client):
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
    import datetime
    base_time = datetime.datetime(2025, 4, 18, 12, 0, 0)
    for i in range(50):
        kdata["keystroke_id"] = i
        kdata["keystroke_time"] = (base_time + datetime.timedelta(milliseconds=i*10)).isoformat()
        kdata["keystroke_char"] = chr(97 + (i % 26))  # cycle a-z
        kdata["expected_char"] = chr(97 + (i % 26))
        kdata["time_since_previous"] = 100 + i
        rv = client.post('/api/keystrokes', data=json.dumps(kdata), content_type='application/json')
        assert rv.status_code == 201
    rv2 = client.get(f'/api/keystrokes?session_id={session_id}')
    assert rv2.status_code == 200
    keystrokes = rv2.get_json()
    assert len(keystrokes) >= 50

# If any test or helper uses Keystroke.get_by_session, update to Keystroke.get_for_session

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
