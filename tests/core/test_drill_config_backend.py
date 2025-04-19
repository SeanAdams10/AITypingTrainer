"""
Pytest tests for DrillConfigService (backend logic for drill configuration).
Covers: get_categories, get_snippets_by_category, get_session_info.
"""
import pytest
from services.drill_config_service import DrillConfigService, DrillCategory, DrillSnippet, DrillSessionInfo
from db.database_manager import DatabaseManager

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_drill_config.db"
    db = DatabaseManager.get_instance()
    db.set_db_path(str(db_path))
    db.init_db()
    # Insert sample categories, snippets, snippet_parts, and practice_sessions
    db.execute_non_query("INSERT INTO text_category (category_name) VALUES ('Alpha'), ('Beta')")
    db.execute_non_query("INSERT INTO text_snippets (category_id, snippet_name) VALUES (1, 'First'), (1, 'Second'), (2, 'Other')")
    db.execute_non_query("INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (1, 0, 'abc'), (1, 1, 'defg'), (2, 0, 'xyz')")
    db.execute_non_query("INSERT INTO practice_sessions (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time) VALUES ('sess1', 1, 0, 4, '2024-04-01T10:00:00'), ('sess2', 1, 4, 7, '2024-04-02T10:00:00')")
    yield str(db_path)

@pytest.fixture
def service(temp_db):
    return DrillConfigService(temp_db)

def test_get_categories(service):
    cats = service.get_categories()
    assert len(cats) == 2
    assert cats[0].category_name == 'Alpha'
    assert cats[1].category_name == 'Beta'

def test_get_snippets_by_category(service):
    snips = service.get_snippets_by_category(1)
    assert len(snips) == 2
    assert snips[0].snippet_name == 'First'
    assert snips[1].snippet_name == 'Second'
    snips2 = service.get_snippets_by_category(2)
    assert len(snips2) == 1
    assert snips2[0].snippet_name == 'Other'

def test_get_session_info(service):
    info = service.get_session_info(1)
    assert info.last_start_index == 4  # Most recent session
    assert info.last_end_index == 7
    assert info.snippet_length == 7  # 'abc' + 'defg'
    info2 = service.get_session_info(2)
    assert info2.last_start_index is None
    assert info2.last_end_index is None
    assert info2.snippet_length == 3

def test_handles_missing_data(service):
    # Category with no snippets
    snips = service.get_snippets_by_category(999)
    assert snips == []
    # Snippet with no parts or sessions
    info = service.get_session_info(999)
    assert info.last_start_index is None
    assert info.last_end_index is None
    assert info.snippet_length == 0
