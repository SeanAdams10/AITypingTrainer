"""
Tests for LibraryManager (categories, snippets, snippet parts) in models/library.py.
Covers all CRUD, validation, and error handling logic.
"""
import pytest
from models.library import LibraryManager, CategoryExistsError, CategoryNotFoundError, SnippetExistsError, SnippetNotFoundError
from models.library import LibraryCategory, LibrarySnippet
from models.database_manager import DatabaseManager

@pytest.fixture
def db_manager(tmp_path):
    db_file = tmp_path / "library_test.db"
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
    yield db
    db.close()

@pytest.fixture
def library(db_manager):
    return LibraryManager(db_manager)

def test_create_and_list_categories(library):
    cat_id = library.create_category("Alpha")
    cat2_id = library.create_category("Beta")
    cats = library.list_categories()
    assert len(cats) == 2
    assert {c.category_name for c in cats} == {"Alpha", "Beta"}

def test_create_duplicate_category(library):
    library.create_category("Alpha")
    with pytest.raises(CategoryExistsError):
        library.create_category("Alpha")

def test_rename_category(library):
    cat_id = library.create_category("Alpha")
    library.rename_category(cat_id, "Omega")
    cats = library.list_categories()
    assert any(c.category_name == "Omega" for c in cats)

def test_rename_category_to_duplicate(library):
    c1 = library.create_category("Alpha")
    c2 = library.create_category("Beta")
    with pytest.raises(CategoryExistsError):
        library.rename_category(c2, "Alpha")

def test_delete_category(library):
    cat_id = library.create_category("Alpha")
    library.delete_category(cat_id)
    cats = library.list_categories()
    assert not cats

def test_create_and_list_snippets(library):
    cat_id = library.create_category("Alpha")
    s_id = library.create_snippet(cat_id, "Hello", "world")
    s2_id = library.create_snippet(cat_id, "Bye", "moon")
    snippets = library.list_snippets(cat_id)
    assert len(snippets) == 2
    assert {s.snippet_name for s in snippets} == {"Hello", "Bye"}

def test_create_duplicate_snippet(library):
    cat_id = library.create_category("Alpha")
    library.create_snippet(cat_id, "Hello", "world")
    with pytest.raises(SnippetExistsError):
        library.create_snippet(cat_id, "Hello", "moon")

def test_edit_snippet_name_and_content(library):
    cat_id = library.create_category("Alpha")
    s_id = library.create_snippet(cat_id, "Hello", "world")
    library.edit_snippet(s_id, "Hello2", "mars")
    snippets = library.list_snippets(cat_id)
    assert any(s.snippet_name == "Hello2" and s.content == "mars" for s in snippets)

def test_edit_snippet_move_category(library):
    c1 = library.create_category("Alpha")
    c2 = library.create_category("Beta")
    s_id = library.create_snippet(c1, "Hello", "world")
    library.edit_snippet(s_id, "Hello", "world", category_id=c2)
    assert not library.list_snippets(c1)
    assert library.list_snippets(c2)

def test_delete_snippet(library):
    cat_id = library.create_category("Alpha")
    s_id = library.create_snippet(cat_id, "Hello", "world")
    library.delete_snippet(s_id)
    assert not library.list_snippets(cat_id)

def test_snippet_parts_split_and_list(library):
    cat_id = library.create_category("Alpha")
    longtext = "a" * 2500
    s_id = library.create_snippet(cat_id, "Long", longtext)
    parts = library.list_parts(s_id)
    assert len(parts) == 3
    assert parts[0].content == "a" * 1000
    assert parts[2].content == "a" * 500

def test_edit_snippet_resplits_parts(library):
    cat_id = library.create_category("Alpha")
    s_id = library.create_snippet(cat_id, "Hello", "a" * 2000)
    library.edit_snippet(s_id, "Hello", "b" * 1500)
    parts = library.list_parts(s_id)
    assert len(parts) == 2
    assert parts[0].content == "b" * 1000
    assert parts[1].content == "b" * 500

def test_delete_snippet_removes_parts(library):
    cat_id = library.create_category("Alpha")
    s_id = library.create_snippet(cat_id, "Hello", "a" * 2000)
    library.delete_snippet(s_id)
    parts = library.list_parts(s_id)
    assert not parts
