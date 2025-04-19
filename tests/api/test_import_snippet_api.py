from api.snippet_api import snippet_api
# Ensure category exists for import snippet tests
from db.database_manager import DatabaseManager
db = DatabaseManager.get_instance()
db.execute_non_query("INSERT INTO text_category (category_id, category_name) VALUES (1, 'Alpha') ON CONFLICT(category_id) DO NOTHING")

def test_import_snippet_api():
    assert snippet_api is not None
