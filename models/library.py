"""
Library models and manager for Snippets Library (categories, snippets, snippet parts).
Implements all CRUD, validation, and business logic for the Snippets Library.
"""

# Standard library imports
import logging
from sqlite3 import DatabaseError
from typing import List, Optional

# Local application imports
from db.database_manager import DatabaseManager
from models.category import Category
from models.category_manager import CategoryManager, CategoryNotFound, CategoryValidationError
from models.snippet import Snippet
from models.snippet_manager import SnippetManager


class LibraryManager:
    """
    Manages categories and snippets for the Snippets Library using the new
    models and managers.
    All DB operations are parameterized. Validation is enforced via Pydantic and
    explicit checks.
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
        """
        Create a new category with the given name.

        Args:
            name: The name of the category to create

        Returns:
            str: The ID of the created category

        Raises:
            CategoryValidationError: If the category name is invalid
        """
        category = Category(category_name=name, description="")
        self.category_manager.save_category(category)
        if category.category_id is None:
            raise ValueError("Failed to create category: No ID returned")
        return str(category.category_id)

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
        """
        Create a new snippet in the specified category.

        Args:
            category_id: The ID of the category to create the snippet in
            name: The name of the snippet
            content: The content of the snippet

        Returns:
            str: The ID of the created snippet

        Raises:
            ValueError: If the category doesn't exist or snippet creation fails
            DatabaseError: If there's an error saving the snippet
        """
        try:
            # Verify category exists first
            category = self.category_manager.get_category_by_id(category_id)
            if category is None:
                raise ValueError(f"Category with ID {category_id} not found")

            snippet = Snippet(
                category_id=category_id,
                snippet_name=name,
                content=content,
                description="",  # Empty description by default
            )
            self.snippet_manager.save_snippet(snippet)
            if snippet.snippet_id is None:
                raise ValueError("Failed to create snippet: No ID returned")
            return str(snippet.snippet_id)
        except DatabaseError as e:
            logging.error(f"Database error creating snippet: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error creating snippet: {e}")
            raise DatabaseError(f"Failed to create snippet: {str(e)}") from e

    def edit_snippet(
        self,
        snippet_id: str,
        snippet_name: str,
        content: str,
        category_id: Optional[str] = None,
    ) -> None:
        """
        Edit an existing snippet.

        Args:
            snippet_id: The ID of the snippet to edit
            snippet_name: New name for the snippet
            content: New content for the snippet
            category_id: Optional new category ID for the snippet

        Raises:
            ValueError: If the snippet with the given ID doesn't exist
            DatabaseError: If there's an error saving the snippet
            Exception: For other unexpected errors
        """
        snippet = self.snippet_manager.get_snippet_by_id(snippet_id)
        if snippet is None:
            raise ValueError(f"Snippet with ID {snippet_id} not found")

        try:
            snippet.snippet_name = snippet_name
            snippet.content = content
            if category_id:
                snippet.category_id = category_id
            self.snippet_manager.save_snippet(snippet)
        except Exception as e:
            # Re-raise with more context
            error_msg = f"Failed to update snippet {snippet_id}: {str(e)}"
            raise DatabaseError(error_msg) from e

    def delete_snippet(self, snippet_id: str) -> bool:
        return self.snippet_manager.delete_snippet(snippet_id)

    def list_parts(self, snippet_id: str) -> List[str]:
        # Not implemented: SnippetManager does not have list_parts
        raise NotImplementedError("list_parts is not implemented in SnippetManager.")
