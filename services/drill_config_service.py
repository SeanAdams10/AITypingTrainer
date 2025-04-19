"""
DrillConfigService: Backend service for Drill Configuration logic.
Handles retrieval of categories, snippets, last session indices, and snippet length.
"""
from typing import List, Optional, Dict, Any
from db.database_manager import DatabaseManager
from pydantic import BaseModel

class DrillCategory(BaseModel):
    category_id: int
    category_name: str

class DrillSnippet(BaseModel):
    snippet_id: int
    snippet_name: str

class DrillSessionInfo(BaseModel):
    last_start_index: Optional[int]
    last_end_index: Optional[int]
    snippet_length: int

class DrillConfigService:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db = DatabaseManager.get_instance()
        if db_path:
            self.db.set_db_path(db_path)

    def get_categories(self) -> list[DrillCategory]:
        rows = self.db.execute_query("SELECT category_id, category_name FROM text_category ORDER BY category_name ASC")
        return [DrillCategory(**row) for row in rows]

    def get_snippets_by_category(self, category_id: int) -> list[DrillSnippet]:
        rows = self.db.execute_query(
            "SELECT snippet_id, snippet_name FROM text_snippets WHERE category_id = ? ORDER BY snippet_name ASC",
            (category_id,)
        )
        return [DrillSnippet(**row) for row in rows]

    def get_session_info(self, snippet_id: int) -> DrillSessionInfo:
        # Get last session indices
        session = self.db.execute_query(
            "SELECT snippet_index_start, snippet_index_end FROM practice_sessions WHERE snippet_id = ? ORDER BY start_time DESC LIMIT 1",
            (snippet_id,)
        )
        last_start = session[0]['snippet_index_start'] if session else None
        last_end = session[0]['snippet_index_end'] if session else None
        # Get snippet length (sum of all parts)
        length_row = self.db.execute_query(
            "SELECT SUM(LENGTH(content)) as total_length FROM snippet_parts WHERE snippet_id = ?",
            (snippet_id,)
        )
        snippet_length = length_row[0]['total_length'] if length_row and length_row[0]['total_length'] is not None else 0
        return DrillSessionInfo(last_start_index=last_start, last_end_index=last_end, snippet_length=snippet_length)
