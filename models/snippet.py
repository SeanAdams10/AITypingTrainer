"""
Snippet model for text snippets used in typing practice.
"""
from typing import Dict, Any, Optional, Tuple
import re

from db.database_manager import DatabaseManager


class Snippet:
    """
    Model class for text snippets in the typing trainer application.
    """

    @classmethod
    def get_by_id(cls, snippet_id: int) -> Optional['Snippet']:
        """
        Get a snippet by its ID.
        Returns a Snippet object or None if not found.
        """
        db = DatabaseManager.get_instance()
        rows = db.execute_query(
            "SELECT * FROM text_snippets WHERE snippet_id = ?",
            (snippet_id,)
        )
        if not rows:
            return None
        # Reconstruct content from snippet_parts
        parts = db.execute_query(
            "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number ASC",
            (snippet_id,)
        )
        full_content = ''.join([p['content'] for p in parts]) if parts else rows[0].get('content', '')
        snippet_data = dict(rows[0])
        snippet_data['content'] = full_content
        return cls.from_dict(snippet_data)

    @classmethod
    def get_by_category(cls, category_id: int) -> list:
        """
        Get all snippets for a given category_id.
        Returns a list of Snippet objects.
        """
        db = DatabaseManager.get_instance()
        rows = db.execute_query(
            "SELECT * FROM text_snippets WHERE category_id = ?",
            (category_id,)
        )
        return [cls.from_dict(row) for row in rows]

    def __init__(
        self,
        snippet_id: Optional[int] = None,
        category_id: Optional[int] = None,
        snippet_name: str = "",
        content: str = "",
        validate: bool = True
    ) -> None:
        """Initialize a Snippet instance."""
        self.snippet_id: Optional[int] = snippet_id
        self.category_id: Optional[int] = category_id
        self.snippet_name: str = snippet_name
        self.content: str = content
        self.db: DatabaseManager = DatabaseManager()

        # Validate on creation when we have all required fields
        # and validation is requested
        # (snippet_name and content)
        if (validate and snippet_name is not None
                and content is not None):
            self.validate_snippet(snippet_name, content)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Snippet':
        """Create a Snippet instance from a dictionary."""
        return cls(
            snippet_id=data.get('snippet_id'),
            category_id=data.get('category_id'),
            snippet_name=data.get('snippet_name', ''),
            content=data.get('content', ''),
            validate=False
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the snippet to a dictionary."""
        return {
            'snippet_id': self.snippet_id,
            'category_id': self.category_id,
            'snippet_name': self.snippet_name,
            'content': self.content
        }

    @classmethod
    def delete_snippet(cls, snippet_id: int) -> bool:
        """Delete a snippet and all its snippet_parts."""
        # Get database instance
        db: DatabaseManager = DatabaseManager.get_instance()
        # Check snippet exists
        exists = db.execute_query(
            "SELECT snippet_id FROM text_snippets "
            "WHERE snippet_id = ?",
            (snippet_id,)
        )
        if not exists:
            raise ValueError("Snippet does not exist.")
        # Delete snippet_parts
        db.execute_update(
            "DELETE FROM snippet_parts WHERE snippet_id = ?",
            (snippet_id,)
        )
        # Delete snippet
        db.execute_update(
            "DELETE FROM text_snippets WHERE snippet_id = ?",
            (snippet_id,)
        )
        return True

    @staticmethod
    def validate_snippet(snippet_name: str, content: str) -> None:
        """
        Validate snippet_name and content for all business rules.
        Raise ValueError for any violation.
        """
        # Non-blank
        if not snippet_name:
            raise ValueError("snippet_name is required and cannot be blank")
        # ASCII-only
        if not all(ord(c) < 128 for c in snippet_name):
            raise ValueError(
                "snippet_name must be ASCII-only"
            )
        # Length restriction
        if len(snippet_name) > 128:
            raise ValueError(
                "snippet_name must be 128 characters or less"
            )
        # SQL injection / forbidden patterns
        forbidden_chars = [";", "'", "--", "/*", "*/"]
        forbidden_keywords = [
            "DROP", "SELECT", "INSERT",
            "DELETE", "UPDATE", "ALTER"
        ]
        lowered = snippet_name.lower()
        # Special characters: block anywhere
        for char in forbidden_chars:
            if char in snippet_name:
                raise ValueError(
                    "snippet_name contains forbidden or dangerous characters")
        # SQL keywords: block as standalone words (word boundaries)
        for keyword in forbidden_keywords:
            if re.search(rf"\\b{keyword.lower()}\\b", lowered):
                raise ValueError(
                    "snippet_name contains forbidden SQL keywords"
                )
        # Content non-blank
        if not content:
            raise ValueError(
                "content is required and cannot be blank"
            )

    def save(self) -> bool:
        """Save the snippet to the database.

        Creates a new snippet if snippet_id is None, otherwise updates the
        existing snippet. Returns True on success, False on failure.
        Raises:
            ValueError: If validation fails
            sqlite3.IntegrityError: If there's a uniqueness constraint
                violation
        """
        # Validate the snippet before saving
        self.validate_snippet(self.snippet_name, self.content)

        # Check for uniqueness of snippet_name in the same category
        query_unique = (
            "SELECT snippet_id FROM text_snippets "
            "WHERE snippet_name = ? AND category_id = ?"
        )
        unique = self.db.execute_query(
            query_unique, (self.snippet_name, self.category_id)
        )
        if unique and (
            self.snippet_id is None or
            unique[0]['snippet_id'] != self.snippet_id
        ):
            raise ValueError(
                "snippet_name must be unique within the category"
            )
        elif unique and (
            self.snippet_id is not None
            and unique[0]['snippet_id'] != self.snippet_id
        ):
            raise ValueError(
                "snippet_name must be unique within the category"
            )
        # If snippet_id is None, this is a new snippet
        if self.snippet_id is None:
            # Insert the snippet metadata
            query = (
                "INSERT INTO text_snippets (category_id, snippet_name) "
                "VALUES (?, ?)"
            )
            self.snippet_id = self.db.execute_insert(
                query,
                (self.category_id, self.snippet_name)
            )
            if not self.snippet_id:
                return False
            # Insert the content as a single part
            query = (
                "INSERT INTO snippet_parts (snippet_id, part_number, content) "
                "VALUES (?, ?, ?)"
            )
            return self.db.execute_update(
                query, (self.snippet_id, 1, self.content)
            )
        else:
            # Update existing snippet
            query1 = (
                "UPDATE text_snippets SET category_id = ?, snippet_name = ? "
                "WHERE snippet_id = ?"
            )
            success1 = self.db.execute_update(
                query1,
                (self.category_id, self.snippet_name, self.snippet_id)
            )
            if not success1:
                return False
            # Update content - first delete existing parts
            query2 = "DELETE FROM snippet_parts WHERE snippet_id = ?"
            success2 = self.db.execute_update(query2, (self.snippet_id,))
            if not success2:
                return False
            # Then insert the new content
            query3 = (
                "INSERT INTO snippet_parts (snippet_id, part_number, content) "
                "VALUES (?, ?, ?)"
            )
            return self.db.execute_update(
                query3,
                (self.snippet_id, 1, self.content)
            )

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

    def get_part_at_position(self, position: int) -> Tuple[int, int, str]:
        """
        Get the snippet part at the given position.
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
            if (current_pos <= position <
                    current_pos + part_length):
                # Found the part
                relative_position = position - current_pos
                return (part['part_number'],
                        relative_position,
                        part['content'])

            current_pos += part_length

        # Position is out of range
        return (-1, -1, "")
