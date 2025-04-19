import pytest
from flask import Flask
from api.snippet_api import snippet_api
from api.category_api import category_api
import json
import sqlite3
import datetime
from db.database_manager import DatabaseManager

@pytest.fixture
def app(tmp_path, monkeypatch):
    # Set up Flask app and temp DB with strong isolation
    db_file = tmp_path / "test_api_db.sqlite3"
    
    # Create a consistent patched version of DatabaseManager
    original_init = DatabaseManager.__init__
    original_get_connection = DatabaseManager.get_connection
    original_get_instance = DatabaseManager.get_instance
    
    # Override __init__ to always use our test database path
    def patched_init(self, db_path=None):
        if not hasattr(self, 'db_path') or self.db_path != str(db_file):
            self.db_path = str(db_file)
            sqlite3.register_adapter(datetime.datetime, self._adapt_datetime)
            sqlite3.register_converter("timestamp", self._convert_datetime)
    
    # Override get_connection to log and ensure we always use test DB
    def patched_get_connection(self):
        print(f"[TEST] Getting connection to {self.db_path}")
        conn = sqlite3.connect(
            self.db_path, detect_types=sqlite3.PARSE_DECLTYPES
        )
        conn.row_factory = sqlite3.Row
        return conn
    
    # Always return the existing instance to maintain singleton pattern
    def patched_get_instance():
        if DatabaseManager._instance is None:
            DatabaseManager._instance = DatabaseManager()
        if not hasattr(DatabaseManager._instance, 'db_path') or DatabaseManager._instance.db_path != str(db_file):
            DatabaseManager._instance.db_path = str(db_file)
        return DatabaseManager._instance
    
    # Apply all the patches
    monkeypatch.setattr(DatabaseManager, "__init__", patched_init)
    monkeypatch.setattr(DatabaseManager, "get_connection", patched_get_connection)
    monkeypatch.setattr(DatabaseManager, "get_instance", patched_get_instance)
    
    # Reset and then create our app
    DatabaseManager.reset_instance()
    
    # Set up Flask app
    app = Flask(__name__)
    app.register_blueprint(snippet_api)
    app.register_blueprint(category_api)
    
    # Initialize the test database
    db = DatabaseManager()
    db.initialize_database()
    
    # Verify the database is properly initialized
    tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='text_category'")
    assert tables, 'text_category table does not exist in test DB after initialization!'
    
    # Provide the app to tests
    yield app

@pytest.fixture
def client(app):
    # Ensure category_id=1 exists for snippet tests
    from db.database_manager import DatabaseManager
    db = DatabaseManager.get_instance()
    db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'Alpha') ON CONFLICT(category_id) DO NOTHING")
    return app.test_client()

@pytest.fixture
def category_id(client):
    # Create a category directly using the model (bypassing API)
    from models.category import Category
    print("Creating test category directly via model...")
    try:
        category_id = Category.create_category("APIcat")
        print(f"Created test category with ID: {category_id}")
        return category_id
    except Exception as e:
        import traceback
        print(f"ERROR creating test category: {e}")
        print(traceback.format_exc())
        assert False, f"Failed to create test category: {e}"

@pytest.mark.parametrize("name,content,expect_success", [
    ("ApiAlpha", "Some content", True),
    ("", "Some content", False),
    ("A"*129, "Content", False),
    ("NonAsciié", "Content", False),
    ("ApiAlpha", "", False),
])
def test_api_snippet_create_validation(client, category_id, name, content, expect_success):
    resp = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": name, "content": content})
    if expect_success:
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "snippet_id" in data
    else:
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "message" in data

@pytest.mark.parametrize("name1,name2,should_succeed", [
    ("ApiUnique1", "ApiUnique2", True),
    ("ApiDup", "ApiDup", False),
])
def test_api_snippet_name_uniqueness(client, category_id, name1, name2, should_succeed):
    resp1 = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": name1, "content": "abc"})
    assert resp1.status_code == 200
    resp2 = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": name2, "content": "def"})
    if should_succeed:
        assert resp2.status_code == 200
    else:
        assert resp2.status_code == 400
        data = resp2.get_json()
        assert data["success"] is False
        assert "unique" in data["message"].lower()

def test_api_snippet_get_and_delete(client, category_id):
    # Create
    resp = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": "ApiToDelete", "content": "abc"})
    assert resp.status_code == 200
    snippet_id = resp.get_json()["snippet_id"]
    # Get
    resp = client.get(f"/api/snippets/{snippet_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["snippet_id"] == snippet_id
    # Delete
    resp = client.delete(f"/api/snippets/{snippet_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    # Confirm deleted
    resp = client.get(f"/api/snippets/{snippet_id}")
    assert resp.status_code == 404

def test_api_snippet_update(client, category_id):
    # Create
    resp = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": "ApiToUpdate", "content": "abc"})
    assert resp.status_code == 200
    snippet_id = resp.get_json()["snippet_id"]
    # Update
    resp = client.put(f"/api/snippets/{snippet_id}", json={"snippet_name": "ApiUpdated", "content": "updated content"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    # Confirm update
    resp = client.get(f"/api/snippets/{snippet_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["snippet_name"] == "ApiUpdated"
    assert data["content"] == "updated content"

def test_api_snippet_sql_injection(client, category_id):
    inj = "Robert'); DROP TABLE text_snippets;--"
    resp = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": inj, "content": "abc"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["success"] is False
    assert "dangerous" in data["message"] or "forbidden" in data["message"]

def test_api_snippet_long_content(client, category_id):
    long_content = "x" * 20000
    resp = client.post("/api/snippets", json={"category_id": category_id, "snippet_name": "ApiLongContent", "content": long_content})
    assert resp.status_code == 200
    snippet_id = resp.get_json()["snippet_id"]
    resp = client.get(f"/api/snippets/{snippet_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content"] == long_content
