import pytest
import sqlite3
from flask import Flask
from api.error_api import error_api
from api.dbviewer_api import bp as dbviewer_bp
import json

@pytest.fixture
def temp_db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
    cursor.executemany("INSERT INTO test_table (name, value) VALUES (?, ?)", [
        ("Alice", 10), ("Bob", 20), ("Charlie", 30), ("David", 40), ("Eve", 50)
    ])
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture
def app(temp_db, monkeypatch):
    app = Flask(__name__)
    # Patch DatabaseManager.get_instance().get_connection to return temp_db
    from db import database_manager
    monkeypatch.setattr(database_manager.DatabaseManager, "get_connection", lambda self: temp_db)
    app.register_blueprint(dbviewer_bp)
    # Ensure test_table exists
    cursor = temp_db.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
    temp_db.commit()
    yield app

@pytest.fixture
def client(app):
    # Ensure test_table exists for dbviewer tests
    import sqlite3
    from db.database_manager import DatabaseManager
    db = DatabaseManager.get_instance()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
    conn.commit()
    return app.test_client()

def test_list_tables(client):
    resp = client.get("/api/dbviewer/tables")
    data = resp.get_json()
    assert data["success"]
    assert "test_table" in data["tables"]

def test_fetch_table_data(client):
    req = {"table_name": "test_table", "page": 1, "page_size": 2}
    resp = client.post("/api/dbviewer/table_data", data=json.dumps(req), content_type="application/json")
    data = resp.get_json()
    assert data["success"]
    assert len(data["rows"]) == 2
    assert data["total"] == 5

def test_fetch_table_data_filter(client):
    req = {"table_name": "test_table", "filters": {"name": "Alice"}}
    resp = client.post("/api/dbviewer/table_data", data=json.dumps(req), content_type="application/json")
    data = resp.get_json()
    assert data["success"]
    assert data["total"] == 1
    assert data["rows"][0]["name"] == "Alice"

def test_export_csv(client):
    req = {"table_name": "test_table", "filters": {"name": "Bob"}}
    resp = client.post("/api/dbviewer/export_csv", data=json.dumps(req), content_type="application/json")
    assert resp.status_code == 200
    assert b"Bob" in resp.data
    assert resp.headers["Content-Type"].startswith("text/csv")
