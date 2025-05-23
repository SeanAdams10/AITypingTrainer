"""
Category data model and manager for CRUD operations.
Handles all business logic, validation, and DB access for categories.
"""

from typing import List

from pydantic import BaseModel, field_validator

from db.database_manager import DatabaseManager


class CategoryValidationError(Exception):
    """Exception raised when category validation fails.

    This exception is raised for validation errors such as invalid name format,
    duplicate category names, etc.
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


class Category(BaseModel):
    """Category data model with validation.

    Attributes:
        category_id: Unique identifier for the category
        category_name: Name of the category (must be ASCII, 1-64 chars, unique)
    """

    category_id: int  # This must be an int, not None
    category_name: str

    @field_validator("category_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate category name constraints.

        Args:
            v: The category name to validate

        Returns:
            str: The validated category name

        Raises:
            ValueError: If validation fails
        """
        if not v or not v.strip():
            raise ValueError("Category name cannot be blank.")
        if len(v) > 64:
            raise ValueError("Category name must be at most 64 characters.")
        if not all(ord(c) < 128 for c in v):
            raise ValueError("Category name must be ASCII-only.")
        return v.strip()


class CategoryManager:
    """
    Manager for CRUD operations and validation on Category, using DatabaseManager for DB access.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize CategoryManager with a DatabaseManager instance.
        """
        self.db_manager: DatabaseManager = db_manager

    def get_category(self, category_id: int) -> Category:
        """
        Retrieve a single category by ID.
        Args:
            category_id: The ID of the category to retrieve
        Returns:
            Category: The category with the specified ID
        Raises:
            CategoryNotFound: If no category exists with the specified ID
        """
        row = self.db_manager.execute(
            "SELECT category_id, category_name FROM categories WHERE category_id = ?",
            (category_id,),
        ).fetchone()
        if not row:
            raise CategoryNotFound(f"Category with ID {category_id} not found")
        # Ensure category_id is an int to satisfy type checker
        retrieved_id = row[0]
        assert isinstance(retrieved_id, int), "category_id must be an integer"
        return Category(category_id=retrieved_id, category_name=row[1])

    def list_categories(self) -> List[Category]:
        """
        List all categories in the database.
        Returns:
            List[Category]: All categories
        """
        rows = self.db_manager.execute(
            "SELECT category_id, category_name FROM categories"
        ).fetchall()
        result = []
        for row in rows:
            # Ensure category_id is an int to satisfy type checker
            retrieved_id = row[0]
            assert isinstance(retrieved_id, int), "category_id must be an integer"
            result.append(Category(category_id=retrieved_id, category_name=row[1]))
        return result

    def create_category(self, category_name: str) -> Category:
        """
        Create a new category with the given name.
        Args:
            category_name: The name of the new category
        Returns:
            Category: The created category
        Raises:
            CategoryValidationError: If the name is invalid or not unique
        """
        self._validate_name(category_name)
        # Check uniqueness
        if self.db_manager.execute(
            "SELECT 1 FROM categories WHERE category_name = ?", (category_name,)
        ).fetchone():
            raise CategoryValidationError("Category name must be unique.")
        cur = self.db_manager.execute(
            "INSERT INTO categories (category_name) VALUES (?)",
            (category_name,)
        )
        # Ensure category_id is an int to satisfy type checker
        category_id = cur.lastrowid
        assert isinstance(category_id, int), "category_id must be an integer"
        return Category(category_id=category_id, category_name=category_name)

    def rename_category(self, category_id: int, new_name: str) -> Category:
        """
        Rename an existing category.
        Args:
            category_id: The ID of the category to rename
            new_name: The new name for the category
        Returns:
            Category: The updated category
        Raises:
            CategoryNotFound: If the category does not exist
            CategoryValidationError: If the new name is invalid or not unique
        """
        self._validate_name(new_name)
        # Check existence
        row = self.db_manager.execute(
            "SELECT category_id FROM categories WHERE category_id = ?", (category_id,)
        ).fetchone()
        if not row:
            raise CategoryNotFound()
        # Check uniqueness
        if self.db_manager.execute(
            "SELECT 1 FROM categories WHERE category_name = ? AND category_id != ?",
            (new_name, category_id),
        ).fetchone():
            raise CategoryValidationError("Category name must be unique.")
        self.db_manager.execute(
            "UPDATE categories SET category_name = ? WHERE category_id = ?",
            (new_name, category_id)
        )
        # Ensure category_id is an int to satisfy the type checker
        assert isinstance(category_id, int), "category_id must be an integer"
        return Category(category_id=category_id, category_name=new_name)

    def delete_category(self, category_id: int) -> None:
        """
        Delete a category and cascade delete its snippets and snippet parts.
        Args:
            category_id: The ID of the category to delete
        Raises:
            CategoryNotFound: If the category does not exist
        """
        # Check existence
        row = self.db_manager.execute(
            "SELECT category_id FROM categories WHERE category_id = ?", (category_id,)
        ).fetchone()
        if not row:
            raise CategoryNotFound()
        # Cascade delete
        self.db_manager.execute(
            (
                "DELETE FROM snippet_parts WHERE snippet_id IN (SELECT snippet_id FROM snippets "
                "WHERE category_id = ?)"
            ),
            (category_id,)
        )
        self.db_manager.execute(
            "DELETE FROM snippets WHERE category_id = ?", (category_id,)
        )
        self.db_manager.execute(
            "DELETE FROM categories WHERE category_id = ?", (category_id,)
        )

    @staticmethod
    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate category name constraints.
        
        Args:
            name: The category name to validate
                
        Raises:
            CategoryValidationError: If validation fails
                - If name is empty or whitespace
                - If name exceeds 64 characters
                - If name contains non-ASCII characters
        
        Note:
            This is a static method as it doesn't require access to instance state.
        """
        if not name or not name.strip():
            raise CategoryValidationError("Category name cannot be blank.")
        if len(name) > 64:
            raise CategoryValidationError(
                "Category name must be at most 64 characters."
            )
        if not all(ord(c) < 128 for c in name):
            raise CategoryValidationError("Category name must be ASCII-only.")
