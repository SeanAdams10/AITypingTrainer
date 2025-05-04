import pytest
from pydantic import BaseModel, ValidationError
import sqlite3
import string

# --- Pydantic model for validation ---
class SnippetModel(BaseModel):
    snippet_id: int | None = None
    category_id: int
    snippet_name: str
    content: str

    @classmethod
    def validate_name(cls, name: str) -> None:
        if not name:
            raise ValueError("Snippet name is required.")
        if len(name) > 128:
            raise ValueError("Snippet name must be <= 128 chars.")
        if not all(c in string.ascii_letters + string.digits + string.punctuation + ' ' for c in name):
            raise ValueError("Snippet name must be ASCII-only.")

    @classmethod
    def validate_content(cls, content: str) -> None:
        if not content:
            raise ValueError("Snippet content is required.")

# --- Helper functions for DB operations ---
def create_snippet(conn: sqlite3.Connection, category_id: int, name: str, content: str) -> int:
    SnippetModel.validate_name(name)
    SnippetModel.validate_content(content)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO snippet (category_id, snippet_name, content) VALUES (?, ?, ?)",
            (category_id, name, content)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        if "UNIQUE" in str(e):
            raise ValueError("Snippet name must be unique within category.")
        raise

def get_snippet(conn: sqlite3.Connection, snippet_id: int) -> SnippetModel:
    cursor = conn.cursor()
    cursor.execute("SELECT snippet_id, category_id, snippet_name, content FROM snippet WHERE snippet_id = ?", (snippet_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError("Snippet not found.")
    return SnippetModel(snippet_id=row[0], category_id=row[1], snippet_name=row[2], content=row[3])

def update_snippet(conn: sqlite3.Connection, snippet_id: int, name: str | None = None, content: str | None = None) -> None:
    cursor = conn.cursor()
    if name is not None:
        SnippetModel.validate_name(name)
        try:
            cursor.execute("UPDATE snippet SET snippet_name = ? WHERE snippet_id = ?", (name, snippet_id))
            conn.commit()
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise ValueError("Snippet name must be unique within category.")
            raise
    if content is not None:
        SnippetModel.validate_content(content)
        cursor.execute("UPDATE snippet SET content = ? WHERE snippet_id = ?", (content, snippet_id))
        conn.commit()

def delete_snippet(conn: sqlite3.Connection, snippet_id: int) -> None:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM snippet WHERE snippet_id = ?", (snippet_id,))
    conn.commit()

# --- Tests ---
def test_create_snippet_success(temp_db, sample_category):
    snippet_id = create_snippet(temp_db, sample_category.category_id, "Hello", "World")
    snippet = get_snippet(temp_db, snippet_id)
    assert snippet.snippet_name == "Hello"
    assert snippet.content == "World"
    assert snippet.category_id == sample_category.category_id

def test_create_snippet_duplicate_name(temp_db, sample_category):
    create_snippet(temp_db, sample_category.category_id, "A", "B")
    with pytest.raises(ValueError, match="unique within category"):
        create_snippet(temp_db, sample_category.category_id, "A", "C")

def test_create_snippet_name_validation(temp_db, sample_category):
    with pytest.raises(ValueError, match="required"):
        create_snippet(temp_db, sample_category.category_id, "", "abc")
    with pytest.raises(ValueError, match="<= 128"):
        create_snippet(temp_db, sample_category.category_id, "a"*129, "abc")
    with pytest.raises(ValueError, match="ASCII-only"):
        create_snippet(temp_db, sample_category.category_id, "héllo", "abc")

def test_create_snippet_content_required(temp_db, sample_category):
    with pytest.raises(ValueError, match="required"):
        create_snippet(temp_db, sample_category.category_id, "ValidName", "")

def test_update_snippet_name_and_content(temp_db, sample_category):
    snippet_id = create_snippet(temp_db, sample_category.category_id, "OldName", "OldContent")
    update_snippet(temp_db, snippet_id, name="NewName", content="NewContent")
    snippet = get_snippet(temp_db, snippet_id)
    assert snippet.snippet_name == "NewName"
    assert snippet.content == "NewContent"

def test_update_snippet_duplicate_name(temp_db, sample_category):
    id1 = create_snippet(temp_db, sample_category.category_id, "A", "B")
    id2 = create_snippet(temp_db, sample_category.category_id, "B", "C")
    with pytest.raises(ValueError, match="unique within category"):
        update_snippet(temp_db, id2, name="A")

def test_delete_snippet(temp_db, sample_category):
    snippet_id = create_snippet(temp_db, sample_category.category_id, "ToDelete", "Content")
    delete_snippet(temp_db, snippet_id)
    with pytest.raises(ValueError, match="not found"):
        get_snippet(temp_db, snippet_id)

def test_snippet_linked_to_category(temp_db, sample_category):
    snippet_id = create_snippet(temp_db, sample_category.category_id, "CatLink", "Content")
    snippet = get_snippet(temp_db, snippet_id)
    assert snippet.category_id == sample_category.category_id

def test_snippet_not_found(temp_db):
    with pytest.raises(ValueError, match="not found"):
        get_snippet(temp_db, 999)
