import pytest
import urllib.parse
from flask import Flask
from db.database_manager import DatabaseManager
from api.category_api import category_api

@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test_api_category.db"
    db = DatabaseManager.get_instance()
    db.set_db_path(str(db_path))
    db.init_db()
    app = Flask(__name__)
    app.register_blueprint(category_api)
    app.config['TESTING'] = True
    yield app

@pytest.fixture
def client(app):
    # Ensure at least one category exists for category tests
    from db.database_manager import DatabaseManager
    db = DatabaseManager.get_instance()
    db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'Alpha') ON CONFLICT(category_id) DO NOTHING")
    return app.test_client()

@pytest.fixture
def client_empty(app):
    # No categories inserted; yields a client with an empty DB
    return app.test_client()

@pytest.mark.parametrize("name,expected_status", [
    ("TestCat", 200),
    ("", 400),
    ("A"*65, 400),
    ("Café", 400),
    ("Robert'); DROP TABLE text_category;--", 400),
])
def test_create_category(client, name, expected_status):
    resp = client.post("/api/categories", json={"name": name})
    assert resp.status_code == expected_status
    if expected_status == 200:
        data = resp.get_json()
        assert data["success"] is True
        assert data["category_name"] == name
    else:
        data = resp.get_json()
        assert data["success"] is False


def test_create_duplicate_category(client):
    resp1 = client.post("/api/categories", json={"name": "DupCat"})
    assert resp1.status_code == 200
    resp2 = client.post("/api/categories", json={"name": "DupCat"})
    assert resp2.status_code == 409
    data = resp2.get_json()
    assert data["success"] is False
    assert data["message"].startswith("Category name must be unique")


def test_list_categories(client_empty):
    # Should start empty
    resp = client_empty.get("/api/categories")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["categories"] == []
    # Add and check
    client_empty.post("/api/categories", json={"name": "Cat1"})
    client_empty.post("/api/categories", json={"name": "Cat2"})
    resp2 = client_empty.get("/api/categories")
    cats = resp2.get_json()["categories"]
    names = [c["category_name"] for c in cats]
    assert set(names) >= {"Cat1", "Cat2"}


def test_rename_category(client):
    # Create
    resp = client.post("/api/categories", json={"name": "OldName"})
    cat_id = resp.get_json()["category_id"]
    # Happy path
    resp2 = client.put(f"/api/categories/{cat_id}", json={"name": "NewName"})
    assert resp2.status_code == 200
    data = resp2.get_json()
    assert data["category_name"] == "NewName"
    # Blank
    resp3 = client.put(f"/api/categories/{cat_id}", json={"name": ""})
    assert resp3.status_code == 400
    # Duplicate
    client.post("/api/categories", json={"name": "Another"})
    resp4 = client.put(f"/api/categories/{cat_id}", json={"name": "Another"})
    assert resp4.status_code == 400
    # Non-ASCII
    resp5 = client.put(f"/api/categories/{cat_id}", json={"name": "Nãme"})
    assert resp5.status_code == 400
    # SQL meta
    resp6 = client.put(f"/api/categories/{cat_id}", json={"name": "Robert'); DROP TABLE text_category;--"})
    assert resp6.status_code == 400


def test_rename_nonexistent_category(client):
    resp = client.put("/api/categories/9999", json={"name": "DoesNotExist"})
    assert resp.status_code == 404 or resp.status_code == 400


def test_delete_category(client):
    resp = client.post("/api/categories", json={"name": "DelMe"})
    cat_id = resp.get_json()["category_id"]
    resp2 = client.delete(f"/api/categories/{cat_id}")
    assert resp2.status_code == 200
    data = resp2.get_json()
    assert data["success"] is True
    # Should be gone
    resp3 = client.delete(f"/api/categories/{cat_id}")
    assert resp3.status_code == 404


def test_delete_nonexistent_category(client):
    resp = client.delete("/api/categories/9999")
    assert resp.status_code == 404
