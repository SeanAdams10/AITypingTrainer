"""
SnippetManager: Class for managing snippets in the database.
Provides methods for CRUD operations on snippets, utilizing the Snippet Pydantic model.
"""

import logging
from typing import Any, List, Optional

from pydantic import ValidationError

# Sorted imports: standard library, then third-party, then local application
from db.database_manager import DatabaseManager
from db.exceptions import (  # DBConnectionError, # Unused; DatabaseTypeError, # Unused; SchemaError, # Unused
    ConstraintError,
    DatabaseError,
    ForeignKeyError,
    IntegrityError,
)
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

    def create_snippet(self, category_id: int, snippet_name: str, content: str) -> Snippet:
        """Creates a new snippet after validation and saves it to the database.

        Args:
            category_id: The ID of the category for the new snippet.
            snippet_name: The name for the new snippet.
            content: The text content for the new snippet.

        Returns:
            The created Snippet object with its new snippet_id.

        Raises:
            ValueError: If validation fails (e.g., duplicate name, invalid data).
            DatabaseError: If a database operation fails.
        """
        snippet_data = {
            "category_id": category_id,
            "snippet_name": snippet_name,
            "content": content,
        }
        try:
            validated_snippet = Snippet(**snippet_data)
        except ValidationError as e:
            # Log the Pydantic validation error for snippet data {snippet_data}: {e}
            logging.error(f"Pydantic validation error for snippet data {snippet_data}: {e}")
            # Re-raise as ValueError to match test expectations
            raise ValueError(str(e)) from e

        if self.snippet_exists(validated_snippet.category_id, validated_snippet.snippet_name):
            raise ValueError(
                f"Snippet name '{validated_snippet.snippet_name}' already exists "
                f"in category ID {validated_snippet.category_id}."
            )

        content_parts = self._split_content_into_parts(validated_snippet.content)
        if not content_parts:
            raise ValueError("Content cannot be empty after splitting.")

        try:
            cursor = self.db.execute(
                "INSERT INTO snippets (category_id, snippet_name) VALUES (?, ?)",
                (validated_snippet.category_id, validated_snippet.snippet_name),
            )

            last_row_id = getattr(cursor, "lastrowid", None)
            if last_row_id is None:
                logging.error("Failed to retrieve lastrowid after snippet insert.")
                raise DatabaseError("Failed to create snippet: could not get new snippet ID.")

            new_snippet_id = int(last_row_id)

            for i, part_content in enumerate(content_parts):
                self.db.execute(
                    "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",  # Added part_number
                    (new_snippet_id, i, part_content),  # Pass i as part_number
                )

            validated_snippet.snippet_id = new_snippet_id
            return validated_snippet
        except ForeignKeyError as e:  # Add this except block
            logging.error(f"Database foreign key error creating snippet: {e}")
            raise IntegrityError(
                f"Could not create snippet due to a foreign key constraint: {e}"
            ) from e
        except (IntegrityError, ConstraintError) as e:
            logging.error(f"Database integrity error creating snippet: {e}")
            raise IntegrityError(
                f"Could not create snippet due to a database constraint: {e}"
            ) from e
        except DatabaseError as e:
            logging.error(f"Database error creating snippet: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error creating snippet: {e}")
            raise DatabaseError(
                f"An unexpected error occurred while creating the snippet: {e}"
            ) from e

    def get_snippet_by_id(self, snippet_id: int) -> Optional[Snippet]:
        """Retrieves a snippet by its ID, assembling its content from parts.

        Args:
            snippet_id: The ID of the snippet to retrieve.

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

    def get_snippet_by_name(self, snippet_name: str, category_id: int) -> Optional[Snippet]:
        """Retrieves a snippet by its name and category ID.

        Args:
            snippet_name: The name of the snippet.
            category_id: The ID of the category the snippet belongs to.

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

            # Assuming snippet_id is the first column
            snippet_id = row[0] if isinstance(row, tuple) else row["snippet_id"]
            return self.get_snippet_by_id(snippet_id)
        except DatabaseError as e:
            logging.error(
                f"Database error retrieving snippet by name '{snippet_name}' in category {category_id}: {e}"
            )
            raise
        except Exception as e:
            logging.error(
                f"Unexpected error retrieving snippet by name '{snippet_name}' in category {category_id}: {e}"
            )
            raise DatabaseError(
                f"An unexpected error occurred while retrieving snippet by name: {e}"
            ) from e

    def list_snippets_by_category(self, category_id: int) -> List[Snippet]:
        """Lists all snippets belonging to a specific category.

        Args:
            category_id: The ID of the category.

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

    def update_snippet(
        self,
        snippet_id: int,
        snippet_name: Optional[str] = None,
        content: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> Snippet:
        """Updates a snippet's name, content, and/or category.

        Args:
            snippet_id: ID of the snippet to update.
            snippet_name: New name for the snippet (optional).
            content: New content for the snippet (optional).
            category_id: New category ID for the snippet (optional).

        Returns:
            The updated Snippet object.

        Raises:
            ValueError: If snippet not found, validation fails, or category does not exist.
            DatabaseError: If a database operation fails.
        """
        current_snippet = self.get_snippet_by_id(snippet_id)
        if not current_snippet:
            raise ValueError(f"Snippet with ID {snippet_id} not found for update.")

        update_fields: dict[str, Any] = {}
        if category_id is not None and category_id != current_snippet.category_id:
            cat_exists_row = self.db.execute(
                "SELECT 1 FROM categories WHERE category_id = ?", (category_id,)
            ).fetchone()
            if not cat_exists_row:
                raise ValueError(f"Target category ID {category_id} does not exist.")
            update_fields["category_id"] = category_id
            current_snippet.category_id = category_id

        if snippet_name is not None and snippet_name != current_snippet.snippet_name:
            if self.snippet_exists(
                current_snippet.category_id, snippet_name, exclude_snippet_id=snippet_id
            ):
                raise ValueError(
                    f"Snippet name '{snippet_name}' already exists "
                    f"in category ID {current_snippet.category_id}."
                )
            update_fields["snippet_name"] = snippet_name

        updated_data = current_snippet.model_copy(update=update_fields).model_dump()
        if content is not None:
            updated_data["content"] = content

        try:
            validated_update = Snippet(**updated_data)
        except ValueError as e:
            raise ValueError(f"Validation error during snippet update: {e}") from e

        try:
            if "category_id" in update_fields or "snippet_name" in update_fields:
                sql_set_parts = []
                sql_params: List[Any] = []  # Ensure sql_params is consistently typed
                if "category_id" in update_fields:
                    sql_set_parts.append("category_id = ?")
                    sql_params.append(validated_update.category_id)
                if "snippet_name" in update_fields:
                    sql_set_parts.append("snippet_name = ?")
                    sql_params.append(validated_update.snippet_name)

                if sql_set_parts:
                    sql_params.append(snippet_id)
                    self.db.execute(
                        f"UPDATE snippets SET {', '.join(sql_set_parts)} WHERE snippet_id = ?",
                        tuple(sql_params),
                    )

            if content is not None:
                self.db.execute("DELETE FROM snippet_parts WHERE snippet_id = ?", (snippet_id,))
                content_parts = self._split_content_into_parts(validated_update.content)
                if not content_parts:
                    raise ValueError("Content cannot be empty after splitting for update.")
                for i, part_content in enumerate(content_parts):
                    self.db.execute(
                        "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                        (snippet_id, i, part_content),
                    )

            updated_snippet = self.get_snippet_by_id(snippet_id)
            if updated_snippet is None:  # Should not happen if update was successful
                logging.error(f"Snippet {snippet_id} not found after presumed successful update.")
                raise DatabaseError(f"Snippet {snippet_id} disappeared after update.")
            return updated_snippet

        except (IntegrityError, ConstraintError) as e:
            logging.error(f"DB integrity error for snippet {snippet_id}: {e}")
            raise IntegrityError(
                f"Could not update snippet (DB constraint for ID {snippet_id}): {e}"
            ) from e
        except DatabaseError as e:
            logging.error(f"DB error updating snippet {snippet_id}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error updating snippet {snippet_id}: {e}")
            raise DatabaseError(f"Unexpected error for snippet {snippet_id} update: {e}") from e

    def delete_snippet(self, snippet_id: int) -> bool:
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
        self, category_id: int, snippet_name: str, exclude_snippet_id: Optional[int] = None
    ) -> bool:
        """Checks if a snippet with the given name already exists in the category.

        Args:
            category_id: The ID of the category to check within.
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
            params: List[Any] = [category_id, snippet_name]
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
