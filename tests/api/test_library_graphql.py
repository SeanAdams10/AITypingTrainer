"""
API tests for the Snippets Library GraphQL endpoint (/api/library_graphql).
Covers all CRUD, validation, and error handling for categories and snippets.
"""
import pytest
from flask import Flask
from models.database_manager import DatabaseManager
from api.library_graphql import library_graphql

@pytest.fixture
def app(tmp_path):
    app = Flask(__name__)
    db_file = tmp_path / "library_api_test.db"
    app.config["DATABASE"] = str(db_file)
    db = DatabaseManager(str(db_file))
    db.execute("""
        CREATE TABLE text_category (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        );
    """, commit=True)
    db.execute("""
        CREATE TABLE text_snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            content TEXT NOT NULL,
            UNIQUE (category_id, snippet_name),
            FOREIGN KEY (category_id) REFERENCES text_category(category_id) ON DELETE CASCADE
        );
    """, commit=True)
    db.execute("""
        CREATE TABLE snippet_parts (
            part_id INTEGER PRIMARY KEY AUTOINCREMENT,
            snippet_id INTEGER NOT NULL,
            part_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id) ON DELETE CASCADE
        );
    """, commit=True)
    app.register_blueprint(library_graphql)
    yield app
    db.close()

@pytest.fixture
def client(app):
    return app.test_client()

def graphql(client, query, variables=None):
    resp = client.post("/api/library_graphql", json={"query": query, "variables": variables or {}})
    assert resp.status_code == 200
    return resp.get_json()

def test_create_and_list_categories(client):
    q = """
    mutation { createCategory(categoryName: "Alpha") { ok error category { categoryId categoryName } } }
    """
    data = graphql(client, q)
    assert data["data"]["createCategory"]["ok"]
    q2 = "{ categories { categoryId categoryName } }"
    data2 = graphql(client, q2)
    cats = data2["data"]["categories"]
    assert any(c["categoryName"] == "Alpha" for c in cats)

def test_create_duplicate_category(client):
    q = "mutation { createCategory(categoryName: \"Alpha\") { ok error } }"
    graphql(client, q)
    data = graphql(client, q)
    assert not data["data"]["createCategory"]["ok"]
    assert "already exists" in data["data"]["createCategory"]["error"]

def test_rename_category(client):
    q = "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }"
    cat_id = graphql(client, q)["data"]["createCategory"]["category"]["categoryId"]
    q2 = f"mutation {{ renameCategory(categoryId: {cat_id}, categoryName: \"Omega\") {{ ok error }} }}"
    data = graphql(client, q2)
    assert data["data"]["renameCategory"]["ok"]
    q3 = "{ categories { categoryName } }"
    cats = graphql(client, q3)["data"]["categories"]
    assert any(c["categoryName"] == "Omega" for c in cats)

def test_rename_category_to_duplicate(client):
    q1 = "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }"
    q2 = "mutation { createCategory(categoryName: \"Beta\") { category { categoryId } } }"
    id1 = graphql(client, q1)["data"]["createCategory"]["category"]["categoryId"]
    id2 = graphql(client, q2)["data"]["createCategory"]["category"]["categoryId"]
    q3 = f"mutation {{ renameCategory(categoryId: {id2}, categoryName: \"Alpha\") {{ ok error }} }}"
    data = graphql(client, q3)
    assert not data["data"]["renameCategory"]["ok"]
    assert "already exists" in data["data"]["renameCategory"]["error"]

def test_delete_category(client):
    q = "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }"
    cat_id = graphql(client, q)["data"]["createCategory"]["category"]["categoryId"]
    q2 = f"mutation {{ deleteCategory(categoryId: {cat_id}) {{ ok error }} }}"
    data = graphql(client, q2)
    assert data["data"]["deleteCategory"]["ok"]
    cats = graphql(client, "{ categories { categoryId } }")["data"]["categories"]
    assert not cats

def test_create_and_list_snippets(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    q = f"""
    mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Hello\", content: \"world\") {{ ok error snippet {{ snippetId snippetName content }} }} }}
    """
    data = graphql(client, q)
    assert data["data"]["createSnippet"]["ok"]
    q2 = f"{{ snippets(categoryId: {cat_id}) {{ snippetId snippetName content }} }}"
    snips = graphql(client, q2)["data"]["snippets"]
    assert any(s["snippetName"] == "Hello" for s in snips)

def test_create_duplicate_snippet(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    q = f"mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Hello\", content: \"world\") {{ ok error }} }}"
    graphql(client, q)
    data = graphql(client, q)
    assert not data["data"]["createSnippet"]["ok"]
    assert "already exists" in data["data"]["createSnippet"]["error"]

def test_edit_snippet_name_and_content(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    s_id = graphql(client, f"mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Hello\", content: \"world\") {{ snippet {{ snippetId }} }} }}")["data"]["createSnippet"]["snippet"]["snippetId"]
    q = f"mutation {{ editSnippet(snippetId: {s_id}, snippetName: \"Hello2\", content: \"mars\") {{ ok error }} }}"
    data = graphql(client, q)
    assert data["data"]["editSnippet"]["ok"]
    snips = graphql(client, f"{{ snippets(categoryId: {cat_id}) {{ snippetId snippetName content }} }}")["data"]["snippets"]
    assert any(s["snippetName"] == "Hello2" and s["content"] == "mars" for s in snips)

def test_edit_snippet_move_category(client):
    c1 = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    c2 = graphql(client, "mutation { createCategory(categoryName: \"Beta\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    s_id = graphql(client, f"mutation {{ createSnippet(categoryId: {c1}, snippetName: \"Hello\", content: \"world\") {{ snippet {{ snippetId }} }} }}")["data"]["createSnippet"]["snippet"]["snippetId"]
    q = f"mutation {{ editSnippet(snippetId: {s_id}, snippetName: \"Hello\", content: \"world\", categoryId: {c2}) {{ ok error }} }}"
    data = graphql(client, q)
    assert data["data"]["editSnippet"]["ok"]
    snips1 = graphql(client, f"{{ snippets(categoryId: {c1}) {{ snippetId }} }}")["data"]["snippets"]
    snips2 = graphql(client, f"{{ snippets(categoryId: {c2}) {{ snippetId }} }}")["data"]["snippets"]
    assert not snips1 and snips2

def test_delete_snippet(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    s_id = graphql(client, f"mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Hello\", content: \"world\") {{ snippet {{ snippetId }} }} }}")["data"]["createSnippet"]["snippet"]["snippetId"]
    q = f"mutation {{ deleteSnippet(snippetId: {s_id}) {{ ok error }} }}"
    data = graphql(client, q)
    assert data["data"]["deleteSnippet"]["ok"]
    snips = graphql(client, f"{{ snippets(categoryId: {cat_id}) {{ snippetId }} }}")["data"]["snippets"]
    assert not snips

def test_snippet_parts_split_and_list(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    longtext = "a" * 2500
    s_id = graphql(client, f"mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Long\", content: \"{longtext}\") {{ snippet {{ snippetId }} }} }}")["data"]["createSnippet"]["snippet"]["snippetId"]
    parts = graphql(client, f"{{ snippetParts(snippetId: {s_id}) {{ partId partNumber content }} }}")["data"]["snippetParts"]
    assert len(parts) == 3
    assert parts[0]["content"] == "a" * 1000
    assert parts[2]["content"] == "a" * 500

def test_edit_snippet_resplits_parts(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    s_id = graphql(client, f"mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Hello\", content: \"{'a'*2000}\") {{ snippet {{ snippetId }} }} }}")["data"]["createSnippet"]["snippet"]["snippetId"]
    q = f"mutation {{ editSnippet(snippetId: {s_id}, snippetName: \"Hello\", content: \"{'b'*1500}\") {{ ok error }} }}"
    graphql(client, q)
    parts = graphql(client, f"{{ snippetParts(snippetId: {s_id}) {{ partId partNumber content }} }}")["data"]["snippetParts"]
    assert len(parts) == 2
    assert parts[0]["content"] == "b" * 1000
    assert parts[1]["content"] == "b" * 500

def test_delete_snippet_removes_parts(client):
    cat_id = graphql(client, "mutation { createCategory(categoryName: \"Alpha\") { category { categoryId } } }")["data"]["createCategory"]["category"]["categoryId"]
    s_id = graphql(client, f"mutation {{ createSnippet(categoryId: {cat_id}, snippetName: \"Hello\", content: \"{'a'*2000}\") {{ snippet {{ snippetId }} }} }}")["data"]["createSnippet"]["snippet"]["snippetId"]
    graphql(client, f"mutation {{ deleteSnippet(snippetId: {s_id}) {{ ok error }} }}")
    parts = graphql(client, f"{{ snippetParts(snippetId: {s_id}) {{ partId }} }}")["data"]["snippetParts"]
    assert not parts
