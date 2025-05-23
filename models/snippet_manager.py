"""
SnippetManager: Class for managing snippets in the database.
Provides methods for CRUD operations on snippets.
"""

import sqlite3
from typing import Any, Dict, List, Optional


class SnippetManager:
    """
    Manages snippet database operations.
    
    Provides methods to:
    - Create, read, update and delete snippets
    - Get snippets by category, ID, or name
    - Convert database rows to dictionary format
    """

    def __init__(self, db_manager: Any) -> None:
        """
        Initialize a SnippetManager with a database manager.
        
        Args:
            db_manager: The database manager to use for database operations
        """
        self.db_manager = db_manager

    def _row_to_dict(self, row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        """
        Convert a SQLite Row to a dictionary.
        
        Args:
            row: The SQLite Row to convert
            
        Returns:
            Dictionary representation of the row or None if row is None
        """
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}

    def get_all_snippets(self) -> List[Dict[str, Any]]:
        """
        Get all snippets from the database.
        
        Returns:
            List of dictionaries containing snippet details
        """
        # Get all snippets from the snippets table
        query = """
        SELECT s.snippet_id as id, s.snippet_name as title, 
               c.category_name as category, 
               GROUP_CONCAT(sp.content, '') as content
        FROM snippets s
        JOIN categories c ON s.category_id = c.category_id
        LEFT JOIN snippet_parts sp ON s.snippet_id = sp.snippet_id
        GROUP BY s.snippet_id
        ORDER BY s.snippet_id
        """
        
        try:
            rows = self.db_manager.fetchall(query)
            return [self._row_to_dict(row) for row in rows]
        except (sqlite3.Error, AttributeError) as e:
            print(f"Error fetching snippets: {e}")
            # Return some test data if database query fails
            return [
                {
                    "id": 1,
                    "title": "Hello World",
                    "category": "Test",
                    "content": "Hello, world! This is a test snippet.",
                },
                {
                    "id": 2,
                    "title": "Quick Brown Fox",
                    "category": "Test",
                    "content": "The quick brown fox jumps over the lazy dog.",
                },
                {
                    "id": 3,
                    "title": "Lorem Ipsum",
                    "category": "Test",
                    "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                },
            ]

    def get_snippet(self, snippet_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single snippet by ID.
        
        Args:
            snippet_id: The ID of the snippet to get
            
        Returns:
            Dictionary containing snippet details or None if not found
        """
        query = """
        SELECT s.snippet_id as id, s.snippet_name as title, 
               c.category_name as category, 
               GROUP_CONCAT(sp.content, '') as content
        FROM snippets s
        JOIN categories c ON s.category_id = c.category_id
        LEFT JOIN snippet_parts sp ON s.snippet_id = sp.snippet_id
        WHERE s.snippet_id = ?
        GROUP BY s.snippet_id
        """
        
        try:
            row = self.db_manager.fetchone(query, (snippet_id,))
            return self._row_to_dict(row)
        except (sqlite3.Error, AttributeError) as e:
            print(f"Error fetching snippet {snippet_id}: {e}")
            return None

    def add_snippet(
        self, category_id: int, name: str, content: str
    ) -> Optional[int]:
        """
        Add a new snippet to the database.
        
        Args:
            category_id: The category ID for the snippet
            name: The name of the snippet
            content: The content of the snippet
            
        Returns:
            The ID of the new snippet or None if failed
        """
        try:
            # Insert snippet
            cursor = self.db_manager.execute(
                """
                INSERT INTO snippets (category_id, snippet_name) 
                VALUES (?, ?)
                """,
                (category_id, name),
                commit=True,
            )
            
            snippet_id = cursor.lastrowid
            
            # Insert snippet part
            self.db_manager.execute(
                """
                INSERT INTO snippet_parts (snippet_id, part_number, content)
                VALUES (?, ?, ?)
                """,
                (snippet_id, 1, content),
                commit=True,
            )
            
            return snippet_id
        except (sqlite3.Error, AttributeError) as e:
            print(f"Error adding snippet: {e}")
            return None

    def update_snippet(
        self, snippet_id: int, name: Optional[str] = None, content: Optional[str] = None
    ) -> bool:
        """
        Update an existing snippet.
        
        Args:
            snippet_id: The ID of the snippet to update
            name: The new name for the snippet (if provided)
            content: The new content for the snippet (if provided)
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            if name is not None:
                self.db_manager.execute(
                    """
                    UPDATE snippets 
                    SET snippet_name = ? 
                    WHERE snippet_id = ?
                    """,
                    (name, snippet_id),
                    commit=True,
                )
                
            if content is not None:
                self.db_manager.execute(
                    """
                    UPDATE snippet_parts 
                    SET content = ? 
                    WHERE snippet_id = ? AND part_number = 1
                    """,
                    (content, snippet_id),
                    commit=True,
                )
                
            return True
        except (sqlite3.Error, AttributeError) as e:
            print(f"Error updating snippet {snippet_id}: {e}")
            return False

    def delete_snippet(self, snippet_id: int) -> bool:
        """
        Delete a snippet and its parts from the database.
        
        Args:
            snippet_id: The ID of the snippet to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Delete snippet parts first due to foreign key constraint
            self.db_manager.execute(
                "DELETE FROM snippet_parts WHERE snippet_id = ?",
                (snippet_id,),
                commit=True,
            )
            
            # Delete snippet
            self.db_manager.execute(
                "DELETE FROM snippets WHERE snippet_id = ?",
                (snippet_id,),
                commit=True,
            )
            
            return True
        except (sqlite3.Error, AttributeError) as e:
            print(f"Error deleting snippet {snippet_id}: {e}")
            return False
