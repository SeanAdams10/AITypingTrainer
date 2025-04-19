"""
Unit tests for LibraryService (backend/services.py).
Covers all validation, error, and CRUD cases. Uses in-memory SQLite DB.
"""
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.category import Category
from models.snippet import Snippet
from models.practice_generator import PracticeGenerator
from services.library_service import LibraryService, ValidationError

@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    LibraryService.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def service(db_session):
    return LibraryService(db_session)

def test_add_and_get_category(service):
    cat = service.add_category("Alpha")
    assert cat.name == "Alpha"
    cats = service.get_categories()
    assert any(c.name == "Alpha" for c in cats)

def test_add_duplicate_category(service):
    service.add_category("Beta")
    with pytest.raises(ValidationError):
        service.add_category("Beta")

def test_edit_category(service):
    cat1 = service.add_category("Gamma")
    cat2 = service.add_category("Gamma2")
    # Try to rename cat1 to cat2's name (should fail)
    with pytest.raises(ValidationError):
        service.edit_category(cat1.category_id, "Gamma2")

def test_delete_category(service):
    cat = service.add_category("Delta")
    service.delete_category(cat.category_id)
    cats = service.get_categories()
    assert not any(c.name == "Delta" for c in cats)

def test_add_and_get_snippet(service):
    cat = service.add_category("Cat1")
    snip = service.add_snippet(cat.category_id, "S1", "abc def")
    assert snip.name == "S1"
    snips = service.get_snippets(cat.category_id)
    assert any(s.name == "S1" for s in snips)

def test_add_snippet_duplicate_name(service):
    cat = service.add_category("Cat2")
    service.add_snippet(cat.category_id, "S2", "abc")
    with pytest.raises(ValidationError):
        service.add_snippet(cat.category_id, "S2", "def")

def test_edit_snippet(service):
    cat = service.add_category("Cat3")
    snip = service.add_snippet(cat.category_id, "S3", "abc")
    snip2 = service.edit_snippet(snip.snippet_id, "S3-2", "xyz")
    assert snip2.name == "S3-2"
    snip3 = service.edit_snippet(snip.snippet_id, "S3-2", "uvw", new_category_id=cat.category_id)
    assert snip3.name == "S3-2"
    # Edit to duplicate name
    service.add_snippet(cat.category_id, "S4", "123")
    with pytest.raises(ValidationError):
        service.edit_snippet(snip.snippet_id, "S4", "zzz")

def test_delete_snippet(service):
    cat = service.add_category("Cat4")
    snip = service.add_snippet(cat.category_id, "S5", "abc")
    service.delete_snippet(snip.snippet_id)
    snips = service.get_snippets(cat.category_id)
    assert not any(s.name == "S5" for s in snips)

def test_snippet_text_validation(service):
    cat = service.add_category("Cat5")
    with pytest.raises(ValidationError):
        service.add_snippet(cat.category_id, "S6", "abcé")  # non-ASCII
    with pytest.raises(ValidationError):
        service.add_snippet(cat.category_id, "", "abc")
    with pytest.raises(ValidationError):
        service.add_snippet(cat.category_id, "S7", "")
    # long name
    with pytest.raises(ValidationError):
        service.add_snippet(cat.category_id, "A"*51, "abc")
    # long category name
    with pytest.raises(ValidationError):
        service.add_category("B"*51)
