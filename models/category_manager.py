"""
Category Manager for CRUD operations.
Handles all DB access for categories.
"""

from typing import List

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

    def _validate_name_uniqueness(self, category_name: str, category_id: int = None) -> None:
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

    def get_category_by_id(self, category_id: int) -> Category:
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
        retrieved_id = row[0]
        assert isinstance(retrieved_id, int), "category_id must be an integer."
        return Category(category_id=retrieved_id, category_name=row[1])

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
        retrieved_id = row[0]
        assert isinstance(retrieved_id, int), "category_id must be an integer."
        return Category(category_id=retrieved_id, category_name=row[1])

    def list_categories(self) -> List[Category]:
        """
        List all categories in the database.
        Returns:
            List[Category]: All categories, ordered by name.
        """
        rows = self.db_manager.execute(
            "SELECT category_id, category_name FROM categories ORDER BY category_name"
        ).fetchall()
        result = []
        for row in rows:
            retrieved_id = row[0]
            assert isinstance(retrieved_id, int), "category_id must be an integer."
            result.append(Category(category_id=retrieved_id, category_name=row[1]))
        return result

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
        temp_category_for_validation = Category(category_id=-1, category_name=category_name)
        validated_name = temp_category_for_validation.category_name

        self._validate_name_uniqueness(validated_name)

        cur = self.db_manager.execute("INSERT INTO categories (category_name) VALUES (?)", (validated_name,))
        category_id = cur.lastrowid
        assert isinstance(category_id, int), "category_id must be an integer."
        return Category(category_id=category_id, category_name=validated_name)

    def update_category(self, category_id: int, new_name: str) -> Category:
        """
        Update an existing category's name.
        The new name is validated for format by the Category model.
        This method handles database existence and uniqueness checks.

        Args:
            category_id: The ID of the category to update.
            new_name: The new name for the category.
        Returns:
            Category: The updated category.
        Raises:
            CategoryNotFound: If the category does not exist.
            CategoryValidationError: If the new name is invalid (per model) or not unique.
        """
        existing_category = self.get_category_by_id(category_id)

        temp_category_for_validation = Category(category_id=category_id, category_name=new_name)
        validated_new_name = temp_category_for_validation.category_name

        if existing_category.category_name == validated_new_name:
            return existing_category

        self._validate_name_uniqueness(validated_new_name, category_id=category_id)

        self.db_manager.execute(
            "UPDATE categories SET category_name = ? WHERE category_id = ?",
            (validated_new_name, category_id),
        )
        return Category(category_id=category_id, category_name=validated_new_name)

    def delete_category(self, category_id: int) -> None:
        """
        Delete a category and cascade delete its snippets and snippet parts.
        Args:
            category_id: The ID of the category to delete.
        Raises:
            CategoryNotFound: If the category does not exist.
        """
        self.get_category_by_id(category_id)

        self.db_manager.execute(
            (
                "DELETE FROM snippet_parts WHERE snippet_id IN (SELECT snippet_id FROM snippets "
                "WHERE category_id = ?)"
            ),
            (category_id,),
        )
        self.db_manager.execute("DELETE FROM snippets WHERE category_id = ?", (category_id,))
        self.db_manager.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
