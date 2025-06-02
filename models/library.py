"""
Library models and manager for Snippets Library (categories, snippets, snippet parts).
Implements all CRUD, validation, and business logic for the Snippets Library.
"""

import uuid
from typing import List, Optional

from pydantic import BaseModel, field_validator

from db.database_manager import DatabaseManager


class LibraryCategory(BaseModel):
    category_id: Optional[str] = None  # UUID
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
    snippet_id: Optional[str] = None  # UUID
    category_id: str  # UUID
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
    snippet_id: str  # UUID
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

    def __init__(self, db_manager: "DatabaseManager") -> None:
        """Initialize the LibraryManager with a database manager.

        Args:
            db_manager: The database manager instance to use for database operations
        """
        self.db = db_manager

    # CATEGORY CRUD
    def list_categories(self) -> List[LibraryCategory]:
        rows = self.db.fetchall("SELECT category_id, name FROM categories ORDER BY name")
        return [LibraryCategory(category_id=row[0], category_name=row[1]) for row in rows]

    def create_category(self, name: str) -> str:
        name = LibraryCategory.validate_name(name)
        if self.db.fetchone("SELECT 1 FROM categories WHERE name = ?", (name,)):
            raise CategoryExistsError(f"Category '{name}' already exists.")
        category_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO categories (category_id, name) VALUES (?, ?)", (category_id, name)
        )
        return category_id

    def rename_category(self, category_id: str, new_name: str) -> None:
        new_name = LibraryCategory.validate_name(new_name)
        if not self.db.fetchone("SELECT 1 FROM categories WHERE category_id = ?", (category_id,)):
            raise CategoryNotFoundError(f"Category {category_id} does not exist.")
        if self.db.fetchone(
            "SELECT 1 FROM categories WHERE name = ? AND category_id != ?",
            (new_name, category_id),
        ):
            raise CategoryExistsError(f"Category '{new_name}' already exists.")
        self.db.execute(
            "UPDATE categories SET name = ? WHERE category_id = ?", (new_name, category_id)
        )

    def delete_category(self, category_id: str) -> None:
        if not self.db.fetchone("SELECT 1 FROM categories WHERE category_id = ?", (category_id,)):
            raise CategoryNotFoundError(f"Category {category_id} does not exist.")
        self.db.execute(
            "DELETE FROM snippet_parts WHERE snippet_id IN ("
            "SELECT snippet_id FROM snippets WHERE category_id = ?)",
            (category_id,),
        )
        self.db.execute("DELETE FROM snippets WHERE category_id = ?", (category_id,))
        self.db.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))

    # SNIPPET CRUD
    def list_snippets(self, category_id: str) -> List[LibrarySnippet]:
        rows = self.db.fetchall(
            "SELECT s.snippet_id, s.category_id, s.snippet_name, p.content "
            "FROM snippets s "
            "LEFT JOIN snippet_parts p ON s.snippet_id = p.snippet_id AND p.part_number = 1 "
            "WHERE s.category_id = ? ORDER BY s.snippet_name",
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

    def create_snippet(self, category_id: str, name: str, content: str) -> str:
        # Validate snippet
        name = LibrarySnippet.validate_name(name)
        LibrarySnippet.validate_content(content)

        # Validate category_id
        if not self.db.fetchone("SELECT 1 FROM categories WHERE category_id = ?", (category_id,)):
            raise CategoryNotFoundError(f"Category {category_id} does not exist.")

        # Check for duplicate snippet name in category
        if self.db.fetchone(
            "SELECT 1 FROM snippets WHERE category_id = ? AND name = ?",
            (category_id, name),
        ):
            raise SnippetExistsError(f"Snippet '{name}' already exists in this category.")

        # Insert snippet
        snippet_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            (snippet_id, category_id, name),
        )

        self._split_and_save_parts(snippet_id, content)

        return snippet_id

    def edit_snippet(
        self,
        snippet_id: str,
        snippet_name: str,
        content: str,
        category_id: Optional[str] = None,
    ) -> None:
        snippet_name = LibrarySnippet.validate_name(snippet_name)
        content = LibrarySnippet.validate_content(content)
        row = self.db.fetchone(
            "SELECT category_id FROM snippets WHERE snippet_id = ?", (snippet_id,)
        )
        if not row:
            raise SnippetNotFoundError(f"Snippet {snippet_id} does not exist.")
        old_category_id = row[0]
        if self.db.fetchone(
            "SELECT 1 FROM snippets WHERE category_id = ? AND snippet_name = ? AND snippet_id != ?",
            (category_id or old_category_id, snippet_name, snippet_id),
        ):
            raise SnippetExistsError(f"Snippet '{snippet_name}' already exists in this category.")
        # Update snippet metadata
        self.db.execute(
            "UPDATE snippets SET snippet_name = ?, category_id = ? WHERE snippet_id = ?",
            (snippet_name, category_id or old_category_id, snippet_id),
        )
        # Re-split parts
        self.db.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,))
        self._split_and_save_parts(snippet_id, content)

    def delete_snippet(self, snippet_id: str) -> None:
        if not self.db.fetchone("SELECT 1 FROM snippets WHERE snippet_id = ?", (snippet_id,)):
            raise SnippetNotFoundError(f"Snippet {snippet_id} does not exist.")
        self.db.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,))
        self.db.execute("DELETE FROM snippets WHERE snippet_id = ?", (snippet_id,))

    # SNIPPET PARTS
    def list_parts(self, snippet_id: str) -> List[SnippetPart]:
        rows = self.db.fetchall(
            "SELECT part_id, snippet_id, part_number, content "
            "FROM snippet_parts WHERE snippet_id = ? "
            "ORDER BY part_number",
            (snippet_id,),
        )
        return [
            SnippetPart(part_id=row[0], snippet_id=row[1], part_number=row[2], content=row[3])
            for row in rows
        ]

    def _split_and_save_parts(self, snippet_id: str, content: str) -> None:
        parts = [content[i : i + 1000] for i in range(0, len(content), 1000)]
        for idx, part in enumerate(parts, 1):
            self.db.execute(
                "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                (snippet_id, idx, part),
            )
