"""Keystroke manager for database-backed keystroke operations."""

import uuid
from typing import Any, List, Optional, Tuple

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_collection import KeystrokeCollection


class KeystrokeManager:
    """Manager class for handling keystroke operations in the database."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        """Initialize the manager with an optional DatabaseManager instance."""
        self.db_manager = db_manager or DatabaseManager()
        self.keystrokes = KeystrokeCollection()

    def get_keystrokes_for_session(self, session_id: str) -> List[Keystroke]:
        """Populate keystrokes collection with all keystrokes for a session from the DB."""
        self.keystrokes.raw_keystrokes = self.get_for_session(session_id)
        return self.keystrokes.raw_keystrokes

    def get_for_session(self, session_id: str) -> List[Keystroke]:
        """Get all keystrokes for a practice session ID.

        Args:
            session_id: The ID of the session to get keystrokes for

        Returns:
            List[Keystroke]: List of Keystroke objects for the session
        """
        query = """
            SELECT *
            FROM session_keystrokes
            WHERE session_id = ?
            ORDER BY key_index asc
        """
        results = self.db_manager.fetchall(query, (session_id,))
        return [Keystroke.from_dict(dict(row)) for row in results] if results else []

    def save_keystrokes(self) -> bool:
        """Save all keystrokes in the in-memory list to the database.

        Returns True if all are saved successfully, False otherwise.
        """
        try:
            if not self.keystrokes.raw_keystrokes:
                return True

            # Standard query for session_keystrokes table with all columns
            query = (
                "INSERT INTO session_keystrokes "
                "(session_id, keystroke_id, keystroke_time, "
                "keystroke_char, expected_char, is_error, time_since_previous, "
                "text_index, key_index) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )

            # Prepare parameter tuples for bulk insert
            params: List[Tuple[Any, ...]] = []
            for idx, ks in enumerate(self.keystrokes.raw_keystrokes):
                if not ks.keystroke_id:
                    ks.keystroke_id = str(uuid.uuid4())
                params.append(
                    (
                        ks.session_id,
                        ks.keystroke_id,
                        ks.keystroke_time.isoformat(),
                        ks.keystroke_char,
                        ks.expected_char,
                        int(ks.is_error),
                        ks.time_since_previous,
                        getattr(ks, "text_index", idx),  # Use text_index or idx as fallback
                        getattr(ks, "key_index", idx),  # Use key_index or idx as fallback
                    )
                )

            # Execute the bulk insert
            self._execute_bulk_insert(query, params)
            return True
        except Exception as e:
            import sys

            print(f"Error saving keystrokes: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return False

    def delete_keystrokes_by_session(self, session_id: str) -> bool:
        """Delete all keystrokes for a given session ID.

        Args:
            session_id: UUID string of the session to delete keystrokes for

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.db_manager.execute(
                "DELETE FROM session_keystrokes WHERE session_id = ?", (session_id,)
            )
            return True
        except Exception as e:
            import sys

            # Log error to stderr
            error_msg = f"Error deleting keystrokes for session {session_id}: {e}"
            print(error_msg, file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return False

    def delete_all_keystrokes(self) -> bool:
        """Delete all keystrokes from the session_keystrokes table.

        Returns True if successful, False otherwise.
        """
        try:
            self.db_manager.execute("DELETE FROM session_keystrokes")
            return True
        except Exception as e:
            print(f"Error deleting all keystrokes: {e}")
            return False

    def count_keystrokes_per_session(self, session_id: str) -> int:
        """Count the number of keystrokes for a specific session.

        Args:
            session_id: The ID of the session to count keystrokes for (UUID string)

        Returns:
            int: The number of keystrokes for the session, or 0 if an error occurs
        """
        try:
            result = self.db_manager.fetchone(
                """
                SELECT COUNT(*) as count
                FROM session_keystrokes
                WHERE session_id = ?
                """,
                (session_id,),
            )
            # Support both Row (dict-like) and tuple/list return types
            if result is not None:
                if hasattr(result, "keys") and "count" in result:
                    val = result["count"]
                    return int(str(val)) if val is not None else 0
                # Fallback: try to cast to tuple/list and access index 0
                try:
                    as_tuple = tuple(result)
                    val2 = as_tuple[0] if len(as_tuple) > 0 else 0
                    return int(str(val2))
                except Exception:
                    return 0
            return 0
        except Exception as e:
            print(f"Error counting keystrokes for session {session_id}: {e}")
            return 0

    def get_errors_for_session(self, session_id: str) -> List[Keystroke]:
        """Get all error keystrokes for a practice session ID.

        Args:
            session_id: The ID of the session to get error keystrokes for

        Returns:
            List[Keystroke]: List of Keystroke objects with errors for the session
        """
        query = (
            "SELECT * FROM session_keystrokes WHERE session_id = ? AND is_error = 1 "
            "ORDER BY keystroke_id"
        )
        results = self.db_manager.fetchall(query, (session_id,))
        return [Keystroke.from_dict(dict(row)) for row in results] if results else []

    def _execute_bulk_insert(self, query: str, params: List[Tuple[Any, ...]]) -> None:
        """Execute bulk insert operation with fallback to individual inserts.

        Args:
            query: SQL insert query
            params: List of parameter tuples for the query
        """
        try:
            # Try to use execute_many if supported
            has_execute_many_support = (
                hasattr(self.db_manager, "execute_many_supported")
                and self.db_manager.execute_many_supported
            )
            if has_execute_many_support:
                self.db_manager.execute_many(query, params)
            elif hasattr(self.db_manager, "execute_many"):
                self.db_manager.execute_many(query, params)
            else:
                # Fallback to individual executions
                for param_tuple in params:
                    self.db_manager.execute(query, param_tuple)
        except Exception:
            # If bulk insert fails, fall back to individual executions
            for param_tuple in params:
                self.db_manager.execute(query, param_tuple)
