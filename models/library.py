"""
Library models and manager for Snippets Library (categories, snippets, snippet parts).
Implements all CRUD, validation, and business logic for the Snippets Library.
"""

from typing import List, Optional

from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager, CategoryNotFound, CategoryValidationError
from models.snippet import Snippet
from models.snippet_manager import SnippetManager


class LibraryManager:
    """
    Manages categories and snippets for the Snippets Library using the new models and
    managers.
    All DB operations are parameterized. Validation is enforced via Pydantic and explicit
    checks.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        self.category_manager = CategoryManager(db_manager)
        self.snippet_manager = SnippetManager(db_manager)

    # CATEGORY CRUD
    def list_categories(self) -> List[Category]:
        """List all categories using CategoryManager."""
        return self.category_manager.list_all_categories()

    def create_category(self, name: str) -> str:
        try:
            category = Category(category_name=name)
            self.category_manager.save_category(category)
            return category.category_id
        except CategoryValidationError:
            raise

    def rename_category(self, category_id: str, new_name: str) -> None:
        try:
            category = self.category_manager.get_category_by_id(category_id)
            category.category_name = new_name
            self.category_manager.save_category(category)
        except (CategoryValidationError, CategoryNotFound):
            raise

    def delete_category(self, category_id: str) -> bool:
        try:
            return self.category_manager.delete_category_by_id(category_id)
        except CategoryNotFound:
            raise

    # SNIPPET CRUD
    def list_snippets(self, category_id: str) -> List[Snippet]:
        return self.snippet_manager.list_snippets_by_category(category_id)

    def create_snippet(self, category_id: str, name: str, content: str) -> str:
        try:
            snippet = Snippet(category_id=category_id, snippet_name=name, content=content)
            self.snippet_manager.save_snippet(snippet)
            return snippet.snippet_id
        except Exception:
            raise

    def edit_snippet(
        self,
        snippet_id: str,
        snippet_name: str,
        content: str,
        category_id: Optional[str] = None,
    ) -> None:
        snippet = self.snippet_manager.get_snippet_by_id(snippet_id)
        if not snippet:
            raise Exception(f"Snippet {snippet_id} does not exist.")
        snippet.snippet_name = snippet_name
        snippet.content = content
        if category_id:
            snippet.category_id = category_id
        self.snippet_manager.save_snippet(snippet)

    def delete_snippet(self, snippet_id: str) -> bool:
        return self.snippet_manager.delete_snippet(snippet_id)

    def list_parts(self, snippet_id: str) -> List[str]:
        # Not implemented: SnippetManager does not have list_parts
        raise NotImplementedError("list_parts is not implemented in SnippetManager.")
