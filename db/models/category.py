"""
Category model class for text categories.
"""
from typing import Dict, List, Any, Optional
import sqlite3
from ..database_manager import DatabaseManager


class Category:
    """
    Model class for text categories in the typing trainer application.
    """
    
    def __init__(self, category_id: Optional[int] = None, category_name: str = ""):
        """Initialize a Category instance."""
        self.category_id = category_id
        self.category_name = category_name
        self.db = DatabaseManager()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        """Create a Category instance from a dictionary."""
        return cls(
            category_id=data.get('category_id'),
            category_name=data.get('category_name', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the category to a dictionary."""
        return {
            'category_id': self.category_id,
            'category_name': self.category_name
        }
    
    def save(self) -> bool:
        """Save the category to the database."""
        if self.category_id is None:
            # New category
            query = "INSERT INTO text_category (category_name) VALUES (?)"
            category_id = self.db.execute_insert(query, (self.category_name,))
            if category_id > 0:
                self.category_id = category_id
                return True
            return False
        else:
            # Update existing category
            query = "UPDATE text_category SET category_name = ? WHERE category_id = ?"
            return self.db.execute_update(query, (self.category_name, self.category_id))
    
    def delete(self) -> bool:
        """Delete the category from the database."""
        if self.category_id is None:
            return False
        
        query = "DELETE FROM text_category WHERE category_id = ?"
        return self.db.execute_update(query, (self.category_id,))
    
    @classmethod
    def get_by_id(cls, category_id: int) -> Optional['Category']:
        """Get a category by its ID."""
        db = DatabaseManager()
        query = "SELECT * FROM text_category WHERE category_id = ?"
        results = db.execute_query(query, (category_id,))
        
        if not results:
            return None
        
        return cls.from_dict(results[0])
    
    @classmethod
    def get_all(cls) -> List['Category']:
        """Get all categories."""
        db = DatabaseManager()
        query = "SELECT * FROM text_category ORDER BY category_name"
        results = db.execute_query(query)
        
        return [cls.from_dict(row) for row in results]
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional['Category']:
        """Get a category by its name."""
        db = DatabaseManager()
        query = "SELECT * FROM text_category WHERE category_name = ?"
        results = db.execute_query(query, (name,))
        
        if not results:
            return None
        
        return cls.from_dict(results[0])
