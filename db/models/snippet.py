"""
Snippet model for text snippets used in typing practice.
"""
from typing import Dict, List, Any, Optional, Tuple
import datetime
import sqlite3
from ..database_manager import DatabaseManager


class Snippet:
    """
    Model class for text snippets in the typing trainer application.
    """
    
    def __init__(
        self, 
        snippet_id: Optional[int] = None, 
        category_id: Optional[int] = None,
        snippet_name: str = "",
        created_at: Optional[datetime.datetime] = None,
        content: str = ""
    ):
        """Initialize a Snippet instance."""
        self.snippet_id = snippet_id
        self.category_id = category_id
        self.snippet_name = snippet_name
        self.created_at = created_at or datetime.datetime.now()
        self.content = content
        self.db = DatabaseManager()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Snippet':
        """Create a Snippet instance from a dictionary."""
        # Handle created_at conversion from string if needed
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = datetime.datetime.now()
        
        return cls(
            snippet_id=data.get('snippet_id'),
            category_id=data.get('category_id'),
            snippet_name=data.get('snippet_name', ''),
            created_at=created_at,
            content=data.get('content', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the snippet to a dictionary."""
        return {
            'snippet_id': self.snippet_id,
            'category_id': self.category_id,
            'snippet_name': self.snippet_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'content': self.content
        }
    
    def save(self) -> bool:
        """Save the snippet to the database."""
        if self.snippet_id is None:
            # New snippet
            # First, insert the snippet metadata
            query1 = """
                INSERT INTO text_snippets (category_id, snippet_name)
                VALUES (?, ?)
            """
            
            snippet_id = self.db.execute_insert(query1, (self.category_id, self.snippet_name))
            if snippet_id <= 0:
                return False
            
            self.snippet_id = snippet_id
            
            # Now, handle the content by splitting it into parts
            max_part_size = 8000  # SQLite has limits on text size
            content_parts = []
            
            for i in range(0, len(self.content), max_part_size):
                part_content = self.content[i:i+max_part_size]
                part_number = i // max_part_size
                content_parts.append((self.snippet_id, part_number, part_content))
            
            # Insert all parts
            for part in content_parts:
                query2 = """
                    INSERT INTO snippet_parts (snippet_id, part_number, content)
                    VALUES (?, ?, ?)
                """
                self.db.execute_insert(query2, part)
            
            return True
        else:
            # Update existing snippet metadata
            query1 = """
                UPDATE text_snippets
                SET category_id = ?, snippet_name = ?
                WHERE snippet_id = ?
            """
            
            success1 = self.db.execute_update(query1, (
                self.category_id, self.snippet_name, self.snippet_id
            ))
            
            if not success1:
                return False
            
            # Handle content update - delete existing parts and insert new ones
            query_delete = "DELETE FROM snippet_parts WHERE snippet_id = ?"
            self.db.execute_update(query_delete, (self.snippet_id,))
            
            # Split content into parts and insert
            max_part_size = 8000
            content_parts = []
            
            for i in range(0, len(self.content), max_part_size):
                part_content = self.content[i:i+max_part_size]
                part_number = i // max_part_size
                content_parts.append((self.snippet_id, part_number, part_content))
            
            # Insert all parts
            for part in content_parts:
                query2 = """
                    INSERT INTO snippet_parts (snippet_id, part_number, content)
                    VALUES (?, ?, ?)
                """
                self.db.execute_insert(query2, part)
            
            return True
    
    def delete(self) -> bool:
        """Delete the snippet from the database."""
        if self.snippet_id is None:
            return False
        
        # Delete all snippet parts first (due to foreign key constraints)
        query1 = "DELETE FROM snippet_parts WHERE snippet_id = ?"
        success1 = self.db.execute_update(query1, (self.snippet_id,))
        
        if not success1:
            return False
        
        # Then delete the snippet metadata
        query2 = "DELETE FROM text_snippets WHERE snippet_id = ?"
        return self.db.execute_update(query2, (self.snippet_id,))
    
    @classmethod
    def get_by_id(cls, snippet_id: int) -> Optional['Snippet']:
        """Get a snippet by its ID."""
        db = DatabaseManager()
        
        # First get the metadata
        query1 = """
            SELECT s.*, c.category_name
            FROM text_snippets s
            JOIN text_category c ON s.category_id = c.category_id
            WHERE s.snippet_id = ?
        """
        results = db.execute_query(query1, (snippet_id,))
        
        if not results:
            return None
        
        # Then get the content parts
        query2 = """
            SELECT content
            FROM snippet_parts
            WHERE snippet_id = ?
            ORDER BY part_number
        """
        parts = db.execute_query(query2, (snippet_id,))
        
        # Create the snippet object
        snippet_data = results[0]
        content = ''.join([part['content'] for part in parts])
        
        snippet = cls(
            snippet_id=snippet_data['snippet_id'],
            category_id=snippet_data['category_id'],
            snippet_name=snippet_data['snippet_name'],
            created_at=snippet_data.get('created_at'),
            content=content
        )
        
        return snippet
    
    @classmethod
    def get_by_category(cls, category_id: int, search_term: str = '') -> List['Snippet']:
        """Get snippets by category ID, optionally filtered by search term."""
        db = DatabaseManager()
        
        if search_term:
            query = """
                SELECT s.*, c.category_name
                FROM text_snippets s
                JOIN text_category c ON s.category_id = c.category_id
                WHERE s.category_id = ? AND s.snippet_name LIKE ?
                ORDER BY s.created_at DESC
            """
            results = db.execute_query(query, (category_id, f"%{search_term}%"))
        else:
            query = """
                SELECT s.*, c.category_name
                FROM text_snippets s
                JOIN text_category c ON s.category_id = c.category_id
                WHERE s.category_id = ?
                ORDER BY s.created_at DESC
            """
            results = db.execute_query(query, (category_id,))
        
        # Create snippet objects, but without content for efficiency
        # Content will be loaded separately when needed
        snippets = []
        for row in results:
            snippet = cls(
                snippet_id=row['snippet_id'],
                category_id=row['category_id'],
                snippet_name=row['snippet_name'],
                created_at=row.get('created_at')
            )
            snippets.append(snippet)
        
        return snippets
    
    def get_part_by_position(self, position: int) -> Tuple[int, int, str]:
        """
        Get the snippet part containing the given character position.
        
        Returns:
            Tuple of (part_number, relative_position, content)
        """
        if self.snippet_id is None:
            return (-1, -1, "")
        
        # First, load all parts if we don't have content
        if not self.content:
            query = """
                SELECT part_number, content
                FROM snippet_parts
                WHERE snippet_id = ?
                ORDER BY part_number
            """
            parts = self.db.execute_query(query, (self.snippet_id,))
            
            self.content = ''.join([part['content'] for part in parts])
        
        # Find the part containing the position
        current_pos = 0
        db = DatabaseManager()
        query = """
            SELECT part_number, content
            FROM snippet_parts
            WHERE snippet_id = ?
            ORDER BY part_number
        """
        parts = db.execute_query(query, (self.snippet_id,))
        
        for part in parts:
            part_length = len(part['content'])
            if current_pos <= position < current_pos + part_length:
                # Found the part
                relative_position = position - current_pos
                return (part['part_number'], relative_position, part['content'])
            
            current_pos += part_length
        
        # Position is out of range
        return (-1, -1, "")
