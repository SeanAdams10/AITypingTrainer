"""
Category model class for text categories.
"""
from typing import Dict, List, Any, Optional
from db.database_manager import DatabaseManager
from models.snippet import Snippet


class Category:
    """
    Model class for text categories in the typing trainer application.
    """

    def __init__(self, category_id: Optional[int] = None,
                 name: str = "") -> None:
        """
        Initialize a Category instance.

        Args:
            category_id (Optional[int]): Unique ID of category.
            name (str): The name of the category.
        """
        self.db = DatabaseManager()
        self.category_id = category_id
        self.name = name

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """
        Create a Category instance from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing category data.

        Returns:
            Category: A new Category instance.
        """
        return cls(
            category_id=data.get("category_id"),
            name=data.get("category_name", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the category to a dictionary.
        """
        return {
            'category_id': self.category_id,
            'category_name': self.name
        }

    def save(self) -> bool:
        """
        Save the category to the database.

        If the category_id is None, a new category is created.
        If the category_id exists, the existing category is updated.

        Returns:
            bool: True if the save operation was successful, False otherwise.
        """
        try:
            Category._validate_name(self.name)
        except ValueError as e:
            print(f"Validation error: {e}")
            return False

        if self.category_id is None:
            # Insert new category
            query = """
                INSERT INTO text_category (category_name)
                VALUES (?)
            """
            success = self.db.execute_update(query, (self.name,))
            if success:
                # Retrieve the last inserted ID
                query_id = "SELECT last_insert_rowid()"
                result = self.db.execute_query(query_id)
                if result:
                    self.category_id = result[0]["last_insert_rowid()"]
            return success
        else:
            # Update existing category
            query = """
                UPDATE text_category
                SET category_name = ?
                WHERE category_id = ?
            """
            return self.db.execute_update(query, (self.name, self.category_id))

    def delete(self) -> bool:
        """
        Delete the category from the database.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        if self.category_id is None:
            return False

        # Check if there are any snippets associated with this category
        query_check = (
            "SELECT COUNT(*) as count FROM text_snippets WHERE category_id = ?"
        )
        result = self.db.execute_query(query_check, (self.category_id,))
        if result and result[0]["count"] > 0:
            # Cannot delete category with associated snippets
            return False

        query = "DELETE FROM text_category WHERE category_id = ?"
        return self.db.execute_update(query, (self.category_id,))

    @classmethod
    def get_by_id(cls, category_id: int) -> Optional['Category']:
        """
        Get a category by its ID.
        """
        db = DatabaseManager()
        query = "SELECT * FROM text_category WHERE category_id = ?"
        results = db.execute_query(query, (category_id,))
        if not results:
            return None
        return cls.from_dict(results[0])

    @classmethod
    def create_category(cls, name: str) -> int:
        """
        Create a new category with validation. Returns new category_id.
        """
        try:
            print('[DEBUG] Category.create_category called with name:', name)
            db = DatabaseManager.get_instance()
            cls._validate_name(name)
            # Check uniqueness
            check_query = """
                SELECT category_id
                FROM text_category
                WHERE category_name = ?
            """
            existing = db.execute_query(check_query, (name,))
            if existing:
                raise ValueError(f"Category '{name}' already exists")
            insert_query = """
                INSERT INTO text_category (category_name)
                VALUES (?)
            """
            category_id = db.execute_insert(insert_query, (name,))
            if category_id <= 0:
                raise ValueError("Failed to create category")
            return category_id
        except Exception as e:
            print('[DEBUG] Exception in create_category:', repr(e))
            raise

    @classmethod
    def list_categories(cls) -> list:
        """
        List all categories as (category_id, category_name) tuples.
        """
        db = DatabaseManager.get_instance()
        rows = db.execute_query(
            "SELECT category_id, category_name FROM text_category"
            " ORDER BY category_id ASC"
        )
        return [
            (row['category_id'], row['category_name'])
            for row in rows
        ]

    @classmethod
    def rename_category(cls, category_id: int, new_name: str) -> None:
        """
        Rename a category with validation.
        """
        cls._validate_name(new_name)
        db = DatabaseManager.get_instance()
        # Check exists
        check_exists = """
            SELECT category_name
            FROM text_category
            WHERE category_id = ?
        """
        exists = db.execute_query(check_exists, (category_id,))
        if not exists:
            raise ValueError(f"Category ID {category_id} does not exist")
        # Check uniqueness
        check_unique = """
            SELECT category_id
            FROM text_category
            WHERE category_name = ? AND category_id != ?
        """
        existing = db.execute_query(check_unique, (new_name, category_id))
        if existing:
            raise ValueError(f"Category name '{new_name}' already in use")
        update_query = """
            UPDATE text_category
            SET category_name = ?
            WHERE category_id = ?
        """
        updated = db.execute_update(update_query, (new_name, category_id))
        if not updated:
            raise ValueError("Failed to rename category.")

    @classmethod
    def delete_category(cls, category_id: int) -> None:
        """
        Delete a category and cascade to snippets and snippet_parts.
        """
        db = DatabaseManager.get_instance()
        # Delete all snippets (and their parts)
        snippets = Snippet.get_by_category(category_id)
        for snippet in snippets:
            Snippet.delete_snippet(snippet.snippet_id)
        db.execute_update(
            "DELETE FROM text_category WHERE category_id = ?",
            (category_id,)
        )

    @staticmethod
    def _validate_name(name: str) -> None:
        """
        Validate the category name.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Category name is required.")
        if len(name) > 64:
            raise ValueError("Category name must be 64 characters or less.")
        if not all(ord(c) < 128 for c in name):
            raise ValueError("Category name must be ASCII-only.")
        # Reject SQL metacharacters
        sql_meta = ["'", ";", "--"]
        if any(meta in name for meta in sql_meta):
            raise ValueError("Category name has invalid characters.")

    @classmethod
    def get_all(cls) -> List['Category']:
        """
        Get all categories.
        """
        db = DatabaseManager()
        query = "SELECT * FROM text_category ORDER BY category_name"
        results = db.execute_query(query)
        return [cls.from_dict(row) for row in results]

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Category']:
        """
        Get a category by its name.
        """
        db = DatabaseManager()
        query = "SELECT * FROM text_category WHERE category_name = ?"
        results = db.execute_query(query, (name,))
        if not results:
            return None
        return cls.from_dict(results[0])
