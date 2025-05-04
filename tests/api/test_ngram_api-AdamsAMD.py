"""
Tests for the ngram API endpoints.
"""
import os
import tempfile
import json
from typing import Generator
import sqlite3
import pytest
from flask.testing import FlaskClient
from app import create_app

def ngram_test_client() -> Generator[FlaskClient, None, None]:
    """Pytest fixture for a Flask test client with a temporary DB and seeded data."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
    })
    from db import init_db
    with app.app_context():
        # Reset DatabaseManager singleton to use the test DB
        from db.database_manager import DatabaseManager
        # Accessing _instance is required for test DB isolation
        DatabaseManager._instance = None  # pylint: disable=protected-access
        init_db()
        db = DatabaseManager.get_instance()
        try:
            db.execute_non_query(
                "INSERT INTO text_category (category_id, category_name) VALUES (1, 'TestCat')"
            )
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' not in str(e):
                raise
        try:
            db.execute_non_query(
                "INSERT INTO text_snippets (snippet_id, category_id, snippet_name) VALUES (1, 1, 'TestSnippet')"
            )
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' not in str(e):
                raise
        try:
            db.execute_non_query(
                "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc')"
            )
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' not in str(e):
                raise
    with app.test_client() as test_client:
        yield test_client
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(name="client")
def fixture_client() -> Generator[FlaskClient, None, None]:
    """Fixture wrapper to avoid name shadowing in test functions."""
    yield from ngram_test_client()

def test_get_ngrams_valid(client: FlaskClient) -> None:
    """Test that /api/ngrams returns valid ngram data for a valid session."""
    session_data = {
        'snippet_id': 1,
        'snippet_index_start': 0,
        'snippet_index_end': 10,
        'practice_type': 'beginning'
    }
    rv = client.post(
        '/api/sessions',
        data=json.dumps(session_data),
        content_type='application/json'
    )
    if rv.status_code != 201:
        print('DEBUG: Session creation failed:', rv.status_code, rv.data)
    session_id = rv.get_json()['session_id']
    rv2 = client.get(f'/api/ngrams?session_id={session_id}')
    assert rv2.status_code == 200
    ngrams = rv2.get_json()
    assert isinstance(ngrams, list)
    for result in ngrams:
        assert 'ngram_size' in result
        assert 'speed_results' in result
        assert 'error_results' in result

def test_get_ngrams_missing_param(client: FlaskClient) -> None:
    """Test that /api/ngrams returns 400 if session_id is missing."""
    rv = client.get('/api/ngrams')
    assert rv.status_code == 400
