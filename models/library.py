"""
Library models and manager for Snippets Library (categories, snippets, snippet parts).
Implements all CRUD, validation, and business logic for the Snippets Library.
"""

from typing import List, Optional

from pydantic import BaseModel, field_validator


class LibraryCategory(BaseModel):
    category_id: Optional[int] = None
    category_name: str

    @field_validator("category_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Category name cannot be blank.")
        if len(v) > 50:
            raise ValueError("Category name must be 50 characters or fewer.")
        if not v.isascii():
            raise ValueError("Category name must be ASCII only.")
        return v.strip()


class LibrarySnippet(BaseModel):
    snippet_id: Optional[int] = None
    category_id: int
    snippet_name: str
    content: str

    @field_validator("snippet_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Snippet name cannot be blank.")
        if len(v) > 128:
            raise ValueError("Snippet name must be 128 characters or fewer.")
        if not v.isascii():
            raise ValueError("Snippet name must be ASCII only.")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Snippet content cannot be blank.")
        return v


class SnippetPart(BaseModel):
    part_id: Optional[int] = None
    snippet_id: int
    part_number: int
    content: str


class CategoryExistsError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class SnippetExistsError(Exception):
    pass


class SnippetNotFoundError(Exception):
    pass


class LibraryManager:
    """
    Manages categories, snippets, and snippet parts for the Snippets Library.
    All DB operations are parameterized. Validation is enforced via Pydantic and explicit checks.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    # CATEGORY CRUD
    def list_categories(self) -> List[LibraryCategory]:
        rows = self.db.fetchall(
            "SELECT category_id, category_name FROM text_category ORDER BY category_name"
        )
        return [
            LibraryCategory(category_id=row[0], category_name=row[1]) for row in rows
        ]

    def create_category(self, name: str) -> int:
        name = LibraryCategory.validate_name(name)
        if self.db.fetchone(
            "SELECT 1 FROM text_category WHERE category_name = ?", (name,)
        ):
            raise CategoryExistsError(f"Category '{name}' already exists.")
        cur = self.db.execute(
            "INSERT INTO text_category (category_name) VALUES (?)", (name,), commit=True
        )
        return cur.lastrowid

    def rename_category(self, category_id: int, new_name: str) -> None:
        new_name = LibraryCategory.validate_name(new_name)
        if not self.db.fetchone(
            "SELECT 1 FROM text_category WHERE category_id = ?", (category_id,)
        ):
            raise CategoryNotFoundError(f"Category {category_id} does not exist.")
        if self.db.fetchone(
            "SELECT 1 FROM text_category WHERE category_name = ? AND category_id != ?",
            (new_name, category_id),
        ):
            raise CategoryExistsError(f"Category '{new_name}' already exists.")
        self.db.execute(
            "UPDATE text_category SET category_name = ? WHERE category_id = ?",
            (new_name, category_id),
            commit=True,
        )

    def delete_category(self, category_id: int) -> None:
        if not self.db.fetchone(
            "SELECT 1 FROM text_category WHERE category_id = ?", (category_id,)
        ):
            raise CategoryNotFoundError(f"Category {category_id} does not exist.")
        # Cascade delete
        self.db.execute(
            "DELETE FROM snippet_parts WHERE snippet_id IN (SELECT snippet_id FROM text_snippets WHERE category_id = ?)",
            (category_id,),
            commit=True,
        )
        self.db.execute(
            "DELETE FROM text_snippets WHERE category_id = ?",
            (category_id,),
            commit=True,
        )
        self.db.execute(
            "DELETE FROM text_category WHERE category_id = ?",
            (category_id,),
            commit=True,
        )

    # SNIPPET CRUD
    def list_snippets(self, category_id: int) -> List[LibrarySnippet]:
        rows = self.db.fetchall(
            "SELECT snippet_id, category_id, snippet_name, content FROM text_snippets WHERE category_id = ? ORDER BY snippet_name",
            (category_id,),
        )
        return [
            LibrarySnippet(
                snippet_id=row[0],
                category_id=row[1],
                snippet_name=row[2],
                content=row[3],
            )
            for row in rows
        ]

    def create_snippet(self, category_id: int, snippet_name: str, content: str) -> int:
        snippet_name = LibrarySnippet.validate_name(snippet_name)
        content = LibrarySnippet.validate_content(content)
        if self.db.fetchone(
            "SELECT 1 FROM text_snippets WHERE category_id = ? AND snippet_name = ?",
            (category_id, snippet_name),
        ):
            raise SnippetExistsError(
                f"Snippet '{snippet_name}' already exists in this category."
            )
        cur = self.db.execute(
            "INSERT INTO text_snippets (category_id, snippet_name, content) VALUES (?, ?, ?)",
            (category_id, snippet_name, content),
            commit=True,
        )
        snippet_id = cur.lastrowid
        self._split_and_save_parts(snippet_id, content)
        return snippet_id

    def edit_snippet(
        self,
        snippet_id: int,
        snippet_name: str,
        content: str,
        category_id: Optional[int] = None,
    ) -> None:
        snippet_name = LibrarySnippet.validate_name(snippet_name)
        content = LibrarySnippet.validate_content(content)
        row = self.db.fetchone(
            "SELECT category_id FROM text_snippets WHERE snippet_id = ?", (snippet_id,)
        )
        if not row:
            raise SnippetNotFoundError(f"Snippet {snippet_id} does not exist.")
        old_category_id = row[0]
        if self.db.fetchone(
            "SELECT 1 FROM text_snippets WHERE category_id = ? AND snippet_name = ? AND snippet_id != ?",
            (category_id or old_category_id, snippet_name, snippet_id),
        ):
            raise SnippetExistsError(
                f"Snippet '{snippet_name}' already exists in this category."
            )
        # Update snippet
        self.db.execute(
            "UPDATE text_snippets SET snippet_name = ?, content = ?, category_id = ? WHERE snippet_id = ?",
            (snippet_name, content, category_id or old_category_id, snippet_id),
            commit=True,
        )
        # Re-split parts
        self.db.execute(
            "DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,), commit=True
        )
        self._split_and_save_parts(snippet_id, content)

    def delete_snippet(self, snippet_id: int) -> None:
        if not self.db.fetchone(
            "SELECT 1 FROM text_snippets WHERE snippet_id = ?", (snippet_id,)
        ):
            raise SnippetNotFoundError(f"Snippet {snippet_id} does not exist.")
        self.db.execute(
            "DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,), commit=True
        )
        self.db.execute(
            "DELETE FROM text_snippets WHERE snippet_id = ?", (snippet_id,), commit=True
        )

    # SNIPPET PARTS
    def list_parts(self, snippet_id: int) -> List[SnippetPart]:
        rows = self.db.fetchall(
            "SELECT part_id, snippet_id, part_number, content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
            (snippet_id,),
        )
        return [
            SnippetPart(
                part_id=row[0], snippet_id=row[1], part_number=row[2], content=row[3]
            )
            for row in rows
        ]

    def _split_and_save_parts(self, snippet_id: int, content: str) -> None:
        parts = [content[i : i + 1000] for i in range(0, len(content), 1000)]
        for idx, part in enumerate(parts, 1):
            self.db.execute(
                "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                (snippet_id, idx, part),
                commit=True,
            )
