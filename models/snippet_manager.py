"""
SnippetManager: Class for managing snippets in the database.
Provides methods for CRUD operations on snippets, utilizing the Snippet Pydantic model.
"""

import logging
from typing import Any, List, Optional

# Sorted imports: standard library, then third-party, then local application
from db.database_manager import DatabaseManager
from db.exceptions import DatabaseError
from models.snippet import Snippet


class SnippetManager:
    """Manages snippets in the database with CRUD operations and validation."""

    MAX_PART_LENGTH = 500  # Maximum length of each snippet part

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the SnippetManager with a database manager.

        Args:
            db_manager: An instance of DatabaseManager.
        """
        self.db = db_manager

    def _split_content_into_parts(self, content: str) -> List[str]:
        """Split content into parts of maximum MAX_PART_LENGTH characters each.

        Args:
            content: The content to split.

        Returns:
            List of strings, each with maximum length of MAX_PART_LENGTH.

        Raises:
            ValueError: If content is not a string (Pydantic model handles empty).
        """
        if not isinstance(content, str):
            # This should ideally be caught by Pydantic, but as a safeguard:
            raise ValueError("Content must be a string for splitting.")
        if not content:  # Pydantic's min_length=1 should prevent this
            return []

        parts: List[str] = []
        remaining: str = content

        while remaining:
            part: str = remaining[: self.MAX_PART_LENGTH]
            parts.append(part)
            remaining = remaining[self.MAX_PART_LENGTH :]

        return parts

    def save_snippet(self, snippet: Snippet) -> bool:
        """
        Insert or update a snippet in the DB. Returns True if successful.

        Args:
            snippet: The Snippet object to save.

        Returns:
            True if the snippet was inserted or updated successfully.

        Raises:
            ValueError: If validation fails (e.g., duplicate name, invalid data).
            DatabaseError: If a database operation fails.
        """
        exists = self.db.execute(
            "SELECT 1 FROM snippets WHERE snippet_id = ?", (snippet.snippet_id,)
        ).fetchone()
        if exists:
            self.db.execute(
                "UPDATE snippets SET category_id = ?, snippet_name = ? WHERE snippet_id = ?",
                (snippet.category_id, snippet.snippet_name, snippet.snippet_id),
            )
            self.db.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet.snippet_id,))
        else:
            self.db.execute(
                "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
                (snippet.snippet_id, snippet.category_id, snippet.snippet_name),
            )
        content_parts = self._split_content_into_parts(snippet.content)
        if not content_parts:
            raise ValueError("Content cannot be empty after splitting.")
        for i, part_content in enumerate(content_parts):
            self.db.execute(
                "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                (snippet.snippet_id, i, part_content),
            )
        return True

    def get_snippet_by_id(self, snippet_id: str) -> Optional[Snippet]:
        """Retrieves a snippet by its ID (UUID), assembling its content from parts.

        Args:
            snippet_id: The UUID of the snippet to retrieve.

        Returns:
            A Snippet object if found, otherwise None.

        Raises:
            DatabaseError: If a database query fails.
        """
        try:
            cursor = self.db.execute(
                "SELECT snippet_id, category_id, snippet_name FROM snippets WHERE snippet_id = ?",
                (snippet_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            snippet_keys = ["snippet_id", "category_id", "snippet_name"]
            snippet_dict = dict(zip(snippet_keys, row, strict=False))
            if hasattr(row, "keys"):  # pragma: no cover
                snippet_dict = {k: row[k] for k in row.keys()}

            parts_cursor = self.db.execute(
                "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
                (snippet_id,),
            )
            content_parts_rows = parts_cursor.fetchall()

            full_content = "".join(part_row[0] for part_row in content_parts_rows)

            snippet_dict["content"] = full_content
            return Snippet(**snippet_dict)
        except DatabaseError as e:
            logging.error(f"Database error retrieving snippet ID {snippet_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error retrieving snippet ID {snippet_id}: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while retrieving snippet ID {snippet_id}: {e}"
            ) from e

    def get_snippet_by_name(self, snippet_name: str, category_id: str) -> Optional[Snippet]:
        """Retrieves a snippet by its name and category UUID.

        Args:
            snippet_name: The name of the snippet.
            category_id: The UUID of the category the snippet belongs to.

        Returns:
            A Snippet object if found, otherwise None.

        Raises:
            DatabaseError: If a database query fails.
        """
        try:
            cursor = self.db.execute(
                "SELECT snippet_id FROM snippets WHERE snippet_name = ? AND category_id = ?",
                (snippet_name, category_id),
            )
            row = cursor.fetchone()
            if not row:
                return None

            snippet_id = row[0] if isinstance(row, tuple) else row["snippet_id"]
            return self.get_snippet_by_id(snippet_id)
        except DatabaseError as e:
            logging.error(
                f"Database error retrieving snippet by name '{snippet_name}' "
                f"in category {category_id}: {e}"
            )
            raise
        except Exception as e:
            logging.error(
                f"Unexpected error retrieving snippet by name '{snippet_name}' "
                f"in category {category_id}: {e}"
            )
            raise DatabaseError(
                f"An unexpected error occurred while retrieving snippet by name "
                f"'{snippet_name}' in category {category_id}: {e}"
            ) from e

    def list_snippets_by_category(self, category_id: str) -> List[Snippet]:
        """Lists all snippets belonging to a specific category (by UUID).

        Args:
            category_id: The UUID of the category.

        Returns:
            A list of Snippet objects.

        Raises:
            DatabaseError: If a database query fails.
        """
        try:
            cursor = self.db.execute(
                "SELECT snippet_id, category_id, snippet_name "
                "FROM snippets WHERE category_id = ? ORDER BY snippet_name ASC",
                (category_id,),
            )
            rows = cursor.fetchall()

            snippets: List[Snippet] = []
            snippet_keys = ["snippet_id", "category_id", "snippet_name"]
            for row in rows:
                snippet_meta_dict = dict(zip(snippet_keys, row, strict=False))
                if hasattr(row, "keys"):  # pragma: no cover
                    snippet_meta_dict = {k: row[k] for k in row.keys()}
                current_snippet_id = snippet_meta_dict["snippet_id"]

                parts_cursor = self.db.execute(
                    "SELECT content FROM snippet_parts WHERE snippet_id = ? ORDER BY part_number",
                    (current_snippet_id,),
                )
                content_parts_rows = parts_cursor.fetchall()
                full_content = "".join(part_row[0] for part_row in content_parts_rows)

                snippet_meta_dict["content"] = full_content
                snippets.append(Snippet(**snippet_meta_dict))
            return snippets
        except DatabaseError as e:
            logging.error(f"Database error listing snippets for cat ID {category_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error listing snippets for cat ID {category_id}: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while listing snippets for cat ID {category_id}: {e}"
            ) from e

    def search_snippets(self, query: str, category_id: Optional[int] = None) -> List[Snippet]:
        """Searches for snippets by a query string in their name or content.

        Args:
            query: The search term.
            category_id: Optional category ID to limit search.

        Returns:
            A list of matching Snippet objects.

        Raises:
            DatabaseError: If a database query fails.
        """
        try:
            search_term = f"%{query}%"
            sql_query = """
                SELECT DISTINCT s.snippet_id
                FROM snippets s
                JOIN snippet_parts sp ON s.snippet_id = sp.snippet_id
                WHERE (s.snippet_name LIKE ? OR sp.content LIKE ?)
            """
            params: List[Any] = [search_term, search_term]

            if category_id is not None:
                sql_query += " AND s.category_id = ?"
                params.append(category_id)

            sql_query += " ORDER BY s.snippet_name ASC;"

            cursor = self.db.execute(sql_query, tuple(params))
            rows = cursor.fetchall()

            snippet_ids = [row[0] if isinstance(row, tuple) else row["snippet_id"] for row in rows]

            snippets: List[Snippet] = []
            for snippet_id in snippet_ids:
                snippet = self.get_snippet_by_id(snippet_id)
                if snippet:
                    snippets.append(snippet)
            return snippets
        except DatabaseError as e:
            logging.error(f"Database error searching snippets with query '{query}': {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error searching snippets with query '{query}': {e}")
            raise DatabaseError(
                f"An unexpected error occurred while searching snippets: {e}"
            ) from e

    def delete_snippet(self, snippet_id: str) -> bool:
        """Deletes a snippet and its parts from the database.

        Args:
            snippet_id: The ID of the snippet to delete.

        Returns:
            True if deletion was successful.

        Raises:
            ValueError: If the snippet does not exist.
            DatabaseError: If a database operation fails.
        """
        if not self.get_snippet_by_id(snippet_id):
            raise ValueError(f"Snippet ID {snippet_id} not exist and cannot be deleted.")

        try:
            self.db.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,))
            self.db.execute("DELETE FROM snippets WHERE snippet_id = ?", (snippet_id,))
            return True
        except DatabaseError as e:
            logging.error(f"Database error deleting snippet {snippet_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error deleting snippet {snippet_id}: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while deleting snippet {snippet_id}: {e}"
            ) from e

    def snippet_exists(
        self, category_id: str, snippet_name: str, exclude_snippet_id: Optional[str] = None
    ) -> bool:
        """Checks if a snippet with the given name already exists in the category (by UUID).

        Args:
            category_id: The UUID of the category to check within.
            snippet_name: The name of the snippet to check for.
            exclude_snippet_id: Optional. If provided, exclude this snippet ID from the check
                                (used when updating an existing snippet's name).

        Returns:
            True if the snippet exists, False otherwise.

        Raises:
            DatabaseError: If the database query fails.
        """
        try:
            query = "SELECT 1 FROM snippets WHERE category_id = ? AND snippet_name = ?"
            params: list[Any] = [category_id, snippet_name]
            if exclude_snippet_id is not None:
                query += " AND snippet_id != ?"
                params.append(exclude_snippet_id)

            cursor = self.db.execute(query, tuple(params))
            return bool(cursor.fetchone())
        except DatabaseError as e:
            logging.error(f"Database error checking if snippet exists: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error checking if snippet exists: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while checking snippet existence: {e}"
            ) from e

    def get_all_snippets_summary(self) -> List[dict[str, Any]]:
        """Retrieves a summary list of all snippets (ID, name, category name).
        This is a lighter query than fetching full content for all snippets.

        Returns:
            A list of dictionaries, each with 'snippet_id', 'snippet_name', 'category_name'.

        Raises:
            DatabaseError: If the database query fails.
        """
        try:
            query = """
                SELECT s.snippet_id, s.snippet_name, c.category_name
                FROM snippets s
                JOIN categories c ON s.category_id = c.category_id
                ORDER BY c.category_name, s.snippet_name;
            """
            rows = self.db.execute(query).fetchall()
            return [{k: row[k] for k in row.keys()} for row in rows]
        except DatabaseError as e:
            logging.error(f"Database error retrieving all snippets summary: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error retrieving all snippets summary: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while retrieving all snippets summary: {e}"
            ) from e

    def list_all_snippets(self) -> List[Snippet]:
        """Lists all snippets in the database with full content."""
        try:
            cursor = self.db.execute("SELECT snippet_id FROM snippets ORDER BY snippet_name")
            rows = cursor.fetchall()
            snippets = []
            for row in rows:
                snippet_id = row[0]
                snippet = self.get_snippet_by_id(snippet_id)
                if snippet:
                    snippets.append(snippet)
            return snippets
        except DatabaseError as e:
            logging.error(f"Database error listing all snippets: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error listing all snippets: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while listing all snippets: {e}"
            ) from e

    def delete_snippet_by_id(self, snippet_id: str) -> None:
        """Deletes a snippet by its ID.

        Args:
            snippet_id: The ID of the snippet to delete.

        Raises:
            ValueError: If the snippet does not exist.
            DatabaseError: If a database operation fails.
        """
        if not self.get_snippet_by_id(snippet_id):
            raise ValueError(f"Snippet ID {snippet_id} does not exist and cannot be deleted.")

        try:
            self.db.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,))
            self.db.execute("DELETE FROM snippets WHERE snippet_id = ?", (snippet_id,))
        except DatabaseError as e:
            logging.error(f"Database error deleting snippet ID {snippet_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error deleting snippet ID {snippet_id}: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while deleting snippet ID {snippet_id}: {e}"
            ) from e

    def delete_all_snippets(self) -> None:
        """Deletes all snippets and their parts from the database."""
        try:
            self.db.execute("DELETE FROM snippet_parts")
            self.db.execute("DELETE FROM snippets")
        except DatabaseError as e:
            logging.error(f"Database error deleting all snippets: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error deleting all snippets: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while deleting all snippets: {e}"
            ) from e

    def create_dynamic_snippet(self, category_id: str) -> Snippet:
        """Creates a dynamic snippet with preset content."""
        return self.create_snippet(
            category_id, "Dynamic Exercises", "Type dynamically generated text here."
        )

    def get_starting_index(self, snippet_id: str, user_id: str, keyboard_id: str) -> int:
        """
        Returns the next starting index for a snippet for a given user and keyboard.
        Looks up the latest practice_session for this snippet, user, and keyboard,
        and returns the maximum snippet_index_end typed so far + 1.
        If no session exists, returns 0.
        If the index is >= snippet length - 1, returns 0 (wraps around).
        """
        snippet = self.get_snippet_by_id(snippet_id)
        if not snippet:
            return 0
        cursor = self.db.execute(
            """
            SELECT MAX(snippet_index_end) FROM practice_sessions
            WHERE snippet_id = ? AND user_id = ? AND keyboard_id = ?
            """,
            (snippet_id, user_id, keyboard_id),
        )
        row = cursor.fetchone()
        max_index = row[0] if row and row[0] is not None else None
        if max_index is None:
            return 0
        if max_index >= len(snippet.content) - 1:
            return 0
        return max_index + 1
