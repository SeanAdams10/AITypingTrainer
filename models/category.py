"""
Category data model and manager for CRUD operations.
Handles all business logic, validation, and DB access for categories.
"""
from typing import List, Dict, Any, Optional, cast
from pydantic import BaseModel, ValidationError, field_validator
from pydantic.types import constr
import sqlite3
import string

class CategoryValidationError(Exception):
    pass

class CategoryNotFound(Exception):
    pass

class Category(BaseModel):
    """Category data model with validation.
    
    Attributes:
        category_id: Unique identifier for the category
        category_name: Name of the category (must be ASCII, 1-64 chars, unique)
    """
    category_id: int
    category_name: str
    
    @field_validator('category_name')
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
    DB_PATH = "aitrainer.db"  # Should be set via config/fixture in tests

    @staticmethod
    def get_db_conn():
        return sqlite3.connect(CategoryManager.DB_PATH)

    @staticmethod
    def get_category(category_id: int) -> Category:
        """Retrieve a single category by ID.
        
        Args:
            category_id: The ID of the category to retrieve
            
        Returns:
            Category: The category with the specified ID
            
        Raises:
            CategoryNotFound: If no category exists with the specified ID
        """
        with CategoryManager.get_db_conn() as conn:
            row = conn.execute("SELECT category_id, category_name FROM categories WHERE category_id = ?", (category_id,)).fetchone()
            if not row:
                raise CategoryNotFound(f"Category with ID {category_id} not found")
            return Category(category_id=row[0], category_name=row[1])
    
    @staticmethod
    def list_categories() -> List[Category]:
        with CategoryManager.get_db_conn() as conn:
            rows = conn.execute("SELECT category_id, category_name FROM categories").fetchall()
            return [Category(category_id=row[0], category_name=row[1]) for row in rows]

    @staticmethod
    def create_category(category_name: str) -> Category:
        CategoryManager._validate_name(category_name)
        with CategoryManager.get_db_conn() as conn:
            # Check uniqueness
            if conn.execute("SELECT 1 FROM categories WHERE category_name = ?", (category_name,)).fetchone():
                raise CategoryValidationError("Category name must be unique.")
            cur = conn.execute(
                "INSERT INTO categories (category_name) VALUES (?)",
                (category_name,)
            )
            conn.commit()
            return Category(category_id=cur.lastrowid, category_name=category_name)

    @staticmethod
    def rename_category(category_id: int, new_name: str) -> Category:
        CategoryManager._validate_name(new_name)
        with CategoryManager.get_db_conn() as conn:
            # Check existence
            row = conn.execute("SELECT category_id FROM categories WHERE category_id = ?", (category_id,)).fetchone()
            if not row:
                raise CategoryNotFound()
            # Check uniqueness
            if conn.execute("SELECT 1 FROM categories WHERE category_name = ? AND category_id != ?", (new_name, category_id)).fetchone():
                raise CategoryValidationError("Category name must be unique.")
            conn.execute(
                "UPDATE categories SET category_name = ? WHERE category_id = ?",
                (new_name, category_id)
            )
            conn.commit()
            return Category(category_id=category_id, category_name=new_name)

    @staticmethod
    def delete_category(category_id: int) -> None:
        with CategoryManager.get_db_conn() as conn:
            # Check existence
            row = conn.execute("SELECT category_id FROM categories WHERE category_id = ?", (category_id,)).fetchone()
            if not row:
                raise CategoryNotFound()
            # Cascade delete snippets and snippet parts
            conn.execute("DELETE FROM snippet_parts WHERE snippet_id IN (SELECT snippet_id FROM snippets WHERE category_id = ?)", (category_id,))
            conn.execute("DELETE FROM snippets WHERE category_id = ?", (category_id,))
            conn.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
            conn.commit()

    @staticmethod
    def _validate_name(name: str) -> None:
        if not name or not name.strip():
            raise CategoryValidationError("Category name cannot be blank.")
        if len(name) > 64:
            raise CategoryValidationError("Category name must be at most 64 characters.")
        if not all(ord(c) < 128 for c in name):
            raise CategoryValidationError("Category name must be ASCII-only.")
