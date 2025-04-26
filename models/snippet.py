"""
Snippet business logic and data model.
Implements all CRUD, validation, and DB abstraction.
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator
from pydantic.types import constr

class SnippetModel(BaseModel):
    snippet_id: Optional[int] = None
    category_id: int
    snippet_name: str = Field(..., min_length=1, max_length=128, pattern=r'^[\x00-\x7F]+$')
    content: str

    @field_validator('snippet_name')
    @classmethod
    def ascii_only(cls, v: str) -> str:
        if not all(ord(c) < 128 for c in v):
            raise ValueError('snippet_name must be ASCII-only')
        return v

class SnippetManager:
    def __init__(self, db_manager: Any) -> None:
        self.db = db_manager

    def create_snippet(self, category_id: int, snippet_name: str, content: str) -> int:
        # Validate uniqueness
        if self.snippet_exists(category_id, snippet_name):
            raise ValueError("Snippet name must be unique within category")
        cursor = self.db.execute(
            "INSERT INTO snippets (category_id, snippet_name, content) VALUES (?, ?, ?)",
            (category_id, snippet_name, content),
            commit=True
        )
        lastrowid = getattr(cursor, 'lastrowid', None)
        if lastrowid is None:
            raise RuntimeError("Failed to retrieve lastrowid after insert.")
        return int(lastrowid)

    def get_snippet(self, snippet_id: int) -> SnippetModel:
        cursor = self.db.execute("SELECT snippet_id, category_id, snippet_name, content FROM snippets WHERE snippet_id = ?", (snippet_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Snippet not found")
        # Convert row to dict for Pydantic model instantiation
        row_dict = {k: row[k] for k in row.keys()} if hasattr(row, 'keys') else dict(zip(['snippet_id', 'category_id', 'snippet_name', 'content'], row))
        return SnippetModel(**row_dict)

    def list_snippets(self, category_id: int) -> List[SnippetModel]:
        cursor = self.db.execute("SELECT snippet_id, category_id, snippet_name, content FROM snippets WHERE category_id = ?", (category_id,))
        rows = cursor.fetchall()
        # Convert each row to dict for Pydantic model instantiation
        return [SnippetModel(**({k: row[k] for k in row.keys()} if hasattr(row, 'keys') else 
                             dict(zip(['snippet_id', 'category_id', 'snippet_name', 'content'], row)))) 
                for row in rows]

    def edit_snippet(self, snippet_id: int, snippet_name: Optional[str] = None, content: Optional[str] = None) -> None:
        snippet = self.get_snippet(snippet_id)
        if snippet_name:
            if self.snippet_exists(snippet.category_id, snippet_name):
                raise ValueError("Snippet name must be unique within category")
            snippet.snippet_name = snippet_name
        if content:
            snippet.content = content
        self.db.execute(
            "UPDATE snippets SET snippet_name = ?, content = ? WHERE snippet_id = ?",
            (snippet.snippet_name, snippet.content, snippet_id),
            commit=True
        )

    def delete_snippet(self, snippet_id: int) -> None:
        self.db.execute("DELETE FROM snippets WHERE snippet_id = ?", (snippet_id,), commit=True)

    def snippet_exists(self, category_id: int, snippet_name: str) -> bool:
        cursor = self.db.execute(
            "SELECT 1 FROM snippets WHERE category_id = ? AND snippet_name = ?", 
            (category_id, snippet_name)
        )
        row = cursor.fetchone()
        return bool(row)
