"""Category Manager for CRUD operations.

Handles all DB access for categories.
"""

from typing import List, Optional

from db.database_manager import DatabaseManager
from models.category import Category


class CategoryValidationError(Exception):
    """Exception raised when category validation fails.

    This exception is raised for validation errors such as invalid name format
    or if a name that is not unique is attempted to be used.
    """

    def __init__(self, message: str = "Category validation failed") -> None:
        """Initialize the error with a helpful message."""
        self.message = message
        super().__init__(self.message)


class CategoryNotFound(Exception):
    """Exception raised when a requested category cannot be found.

    This exception is raised when attempting to access, modify or delete
    a category that does not exist in the database.
    """

    def __init__(self, message: str = "Category not found") -> None:
        """Initialize the error with a helpful message."""
        self.message = message
        super().__init__(self.message)


class CategoryManager:
    """Manager for CRUD on `Category` via `DatabaseManager`."""

    def __init__(self, *, db_manager: DatabaseManager) -> None:
        """Initialize CategoryManager with a DatabaseManager instance."""
        self.db_manager: DatabaseManager = db_manager

    def _validate_name_uniqueness(
        self, *, category_name: str, category_id: Optional[str] = None
    ) -> None:
        """Validate category name uniqueness in the database.

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

        if self.db_manager.execute(query=query, params=tuple(params)).fetchone():
            error_msg = f"Category name '{category_name}' must be unique."
            raise CategoryValidationError(error_msg)

    def get_category_by_id(self, *, category_id: str) -> Category:
        """Retrieve a single category by ID.

        Args:
            category_id: The ID of the category to retrieve.

        Returns:
            Category: The category with the specified ID.

        Raises:
            CategoryNotFound: If no category exists with the specified ID.
        """
        row = self.db_manager.execute(
            query="SELECT category_id, category_name FROM categories WHERE category_id = ?",
            params=(category_id,),
        ).fetchone()
        if not row:
            raise CategoryNotFound(f"Category with ID {category_id} not found.")
        return Category(
            category_id=str(row[0]) if row[0] is not None else None,  # type: ignore[index]
            category_name=str(row[1]),  # type: ignore[index]
            description="",
        )

    def get_category_by_name(self, *, category_name: str) -> Category:
        """Retrieve a single category by name.

        Args:
            category_name: The name of the category to retrieve.

        Returns:
            Category: The category with the specified name.

        Raises:
            CategoryNotFound: If no category exists with the specified name.
        """
        row = self.db_manager.execute(
            query="SELECT category_id, category_name FROM categories WHERE category_name = ?",
            params=(category_name,),
        ).fetchone()
        if not row:
            raise CategoryNotFound(f"Category with name '{category_name}' not found.")
        return Category(
            category_id=str(row[0]) if row[0] is not None else None,  # type: ignore[index]
            category_name=str(row[1]),  # type: ignore[index]
            description="",
        )

    def list_all_categories(self) -> List[Category]:
        """List all categories in the database.

        Returns:
            List[Category]: All categories, ordered by name.
        """
        rows = self.db_manager.execute(
            query="SELECT category_id, category_name FROM categories ORDER BY category_name"
        ).fetchall()
        return [
            Category(
                category_id=str(row[0]) if row[0] is not None else None,  # type: ignore[index]
                category_name=str(row[1]),  # type: ignore[index]
                description="",
            )
            for row in rows
        ]

    def save_category(self, *, category: Category) -> bool:
        """Insert or update a category in the DB.

        Args:
            category: The Category object to save.

        Returns:
            True if the category was inserted or updated successfully.

        Raises:
            CategoryValidationError: If the category name is not unique.
            ValueError: If validation fails (e.g., invalid data).
            DatabaseError: If a database operation fails.
        """
        # Explicitly validate uniqueness before DB operation
        self._validate_name_uniqueness(category_name=category.category_name, category_id=category.category_id)
        if category.category_id and self.__category_exists(category_id=category.category_id):
            return self.__update_category(category=category)
        else:
            return self.__insert_category(category=category)

    def __category_exists(self, *, category_id: str) -> bool:
        row = self.db_manager.execute(
            query="SELECT 1 FROM categories WHERE category_id = ?", params=(category_id,)
        ).fetchone()
        return row is not None

    def __insert_category(self, *, category: Category) -> bool:
        self.db_manager.execute(
            query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            params=(category.category_id, category.category_name),
        )
        return True

    def __update_category(self, *, category: Category) -> bool:
        self.db_manager.execute(
            query="UPDATE categories SET category_name = ? WHERE category_id = ?",
            params=(category.category_name, category.category_id),
        )
        return True

    def delete_category_by_id(self, *, category_id: str) -> bool:
        """Delete a category by its ID.

        Returns:
            bool: True if deleted, False if not found.

        Note:
            Cascades to delete associated snippets and snippet_parts if DB schema
            supports it.
        """
        # Ensure the category exists
        if not self.db_manager.execute(
            query="SELECT 1 FROM categories WHERE category_id = ?",
            params=(category_id,),
        ).fetchone():
            return False
        self.db_manager.execute(
            query="DELETE FROM categories WHERE category_id = ?",
            params=(category_id,),
        )
        return True

    def delete_category(self, *, category_id: str) -> bool:
        """Delete a category by its ID.

        This is an alias for delete_category_by_id for test compatibility.
        """
        return self.delete_category_by_id(category_id=category_id)

    def delete_all_categories(self) -> bool:
        """Delete all categories from the database.

        Returns True if any were deleted, False if already empty.
        """
        count_result = self.db_manager.execute(query="SELECT COUNT(*) FROM categories").fetchone()
        count = int(str(count_result[0])) if count_result else 0  # type: ignore[index]
        self.db_manager.execute(query="DELETE FROM categories")
        return count > 0

    def create_dynamic_category(self) -> str:
        """Create or retrieve a category named 'Custom Snippets' for dynamic content.

        This method ensures that a standard category exists for dynamic and custom
        snippets generated by the application. If the category already exists,
        it returns the existing category's ID. If not, it creates the category
        and returns the new ID.

        Returns:
            str: The category_id of the 'Custom Snippets' category

        Raises:
            CategoryValidationError: If there are validation issues
            DatabaseError: If database operations fail
        """
        category_name = "Custom Snippets"
        try:
            existing_category = self.get_category_by_name(category_name=category_name)
            existing_id = existing_category.category_id
            if existing_id is None:
                # Defensive: DB-created categories should always have IDs
                raise RuntimeError("Existing category missing category_id")
            return existing_id
        except CategoryNotFound:
            new_category = Category(
                category_name=category_name,
                description="Category for custom text snippets and user-generated content",
            )
            self.save_category(category=new_category)
            new_id = new_category.category_id
            if new_id is None:
                # Pydantic validator ensures ID generation; this guards mypy
                raise RuntimeError("New category creation did not produce category_id") from None
            return new_id
