"""
Category Manager for CRUD operations.
Handles all DB access for categories.
"""

from typing import List, Optional
import uuid

from db.database_manager import DatabaseManager
from models.category import Category


class CategoryValidationError(Exception):
    """Exception raised when category validation fails.

    This exception is raised for validation errors such as invalid name format
    or if a name that is not unique is attempted to be used.
    """

    def __init__(self, message: str = "Category validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class CategoryNotFound(Exception):
    """Exception raised when a requested category cannot be found.

    This exception is raised when attempting to access, modify or delete
    a category that does not exist in the database.
    """

    def __init__(self, message: str = "Category not found") -> None:
        self.message = message
        super().__init__(self.message)


class CategoryManager:
    """
    Manager for CRUD operations on Category, using DatabaseManager for DB access.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize CategoryManager with a DatabaseManager instance.
        """
        self.db_manager: DatabaseManager = db_manager

    def _validate_name_uniqueness(self, category_name: str, category_id: Optional[str] = None) -> None:
        """
        Validate category name for database uniqueness.
        This complements the Pydantic model's format validation.

        Args:
            category_name: The category name to validate.
            category_id: The ID of the category being updated, if any.

        Raises:
            CategoryValidationError: If the name is not unique.
        """
        query = "SELECT 1 FROM categories WHERE category_name = ?"
        params = [category_name]
        if category_id is not None:
            query += " AND category_id != ?"
            params.append(category_id)

        if self.db_manager.execute(query, tuple(params)).fetchone():
            raise CategoryValidationError(f"Category name '{category_name}' must be unique.")

    def get_category_by_id(self, category_id: str) -> Category:
        """
        Retrieve a single category by ID.
        Args:
            category_id: The ID of the category to retrieve.
        Returns:
            Category: The category with the specified ID.
        Raises:
            CategoryNotFound: If no category exists with the specified ID.
        """
        row = self.db_manager.execute(
            "SELECT category_id, category_name FROM categories WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        if not row:
            raise CategoryNotFound(f"Category with ID {category_id} not found.")
        return Category(category_id=row[0], category_name=row[1])

    def get_category_by_name(self, category_name: str) -> Category:
        """
        Retrieve a single category by name.
        Args:
            category_name: The name of the category to retrieve.
        Returns:
            Category: The category with the specified name.
        Raises:
            CategoryNotFound: If no category exists with the specified name.
        """
        row = self.db_manager.execute(
            "SELECT category_id, category_name FROM categories WHERE category_name = ?",
            (category_name,),
        ).fetchone()
        if not row:
            raise CategoryNotFound(f"Category with name '{category_name}' not found.")
        return Category(category_id=row[0], category_name=row[1])

    def list_all_categories(self) -> List[Category]:
        """
        List all categories in the database.
        Returns:
            List[Category]: All categories, ordered by name.
        """
        rows = self.db_manager.execute(
            "SELECT category_id, category_name FROM categories ORDER BY category_name"
        ).fetchall()
        return [Category(category_id=row[0], category_name=row[1]) for row in rows]

    def create_category(self, category_name: str) -> Category:
        """
        Create a new category with the given name.
        The category name is validated for format by the Category model upon instantiation.
        This method handles database uniqueness check and insertion.

        Args:
            category_name: The name of the new category.
        Returns:
            Category: The created category.
        Raises:
            CategoryValidationError: If the name is invalid (per model) or not unique.
        """
        temp_category = Category(category_name=category_name)
        validated_name = temp_category.category_name

        self._validate_name_uniqueness(validated_name)

        # Save to DB
        self.save_category(temp_category)
        return temp_category

    def create_dynamic_category(self) -> Category:
        """Create a special category for dynamic exercises called 'Dynamic Exercises'."""
        return self.create_category("Dynamic Exercises")

    def save_category(self, category: Category) -> None:
        """
        Insert or update category in DB
        """
        exists = self.db_manager.execute(
            "SELECT 1 FROM categories WHERE category_id = ?",
            (category.category_id,)
        ).fetchone()
        if exists:
            self.db_manager.execute(
                "UPDATE categories SET category_name = ? WHERE category_id = ?",
                (category.category_name, category.category_id),
            )
        else:
            self.db_manager.execute(
                "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                (category.category_id, category.category_name),
            )
