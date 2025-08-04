from typing import List, Optional

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke


class KeystrokeManager:
    """
    Manager class for handling keystroke operations in the database.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db_manager = db_manager or DatabaseManager()
        self.keystroke_list: List[Keystroke] = []

    def add_keystroke(self, keystroke: Keystroke) -> None:
        """
        Add a single keystroke to the in-memory list.
        """
        self.keystroke_list.append(keystroke)

    def get_keystrokes_for_session(self, session_id: str) -> List[Keystroke]:
        """
        Populate keystroke_list with all keystrokes for a session from the DB.
        """
        self.keystroke_list = Keystroke.get_for_session(session_id)
        return self.keystroke_list

    def save_keystrokes(self) -> bool:
        """
        Save all keystrokes in the in-memory list to the database.
        Returns True if all are saved successfully, False otherwise.
        """
        try:
            for keystroke in self.keystroke_list:
                self.db_manager.execute(
                    (
                        "INSERT INTO session_keystrokes "
                        "(session_id, keystroke_id, keystroke_time, "
                        "keystroke_char, expected_char, is_error, time_since_previous, text_index) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                    ),
                    (
                        keystroke.session_id,
                        keystroke.keystroke_id,  # Now a UUID string
                        keystroke.keystroke_time.isoformat(),
                        keystroke.keystroke_char,
                        keystroke.expected_char,
                        int(keystroke.is_error),
                        keystroke.time_since_previous,
                        keystroke.text_index,
                    ),
                )
            return True
        except Exception as e:
            import sys

            print(f"Error saving keystrokes: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return False

    def delete_keystrokes_by_session(self, session_id: str) -> bool:
        """
        Delete all keystrokes for a given session ID.

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
        """
        Delete all keystrokes from the session_keystrokes table.
        Returns True if successful, False otherwise.
        """
        try:
            self.db_manager.execute("DELETE FROM session_keystrokes")
            return True
        except Exception as e:
            print(f"Error deleting all keystrokes: {e}")
            return False

    def count_keystrokes_per_session(self, session_id: str) -> int:
        """
        Count the number of keystrokes for a specific session.

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
                    return result["count"] if result["count"] is not None else 0
                # Fallback: try to cast to tuple/list and access index 0
                try:
                    as_tuple = tuple(result)
                    return as_tuple[0] if as_tuple[0] is not None else 0
                except Exception:
                    return 0
            return 0
        except Exception as e:
            print(f"Error counting keystrokes for session {session_id}: {e}")
            return 0
