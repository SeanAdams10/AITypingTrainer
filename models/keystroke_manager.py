from typing import Any, Dict, List, Optional

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke


class KeystrokeManager:
    """
    Manager class for handling keystroke operations in the database.
    """
    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        self.db_manager = db_manager or DatabaseManager()

    def add_keystroke(self, keystroke: Keystroke) -> bool:
        """
        Add a single keystroke to the database.
        """
        return keystroke.save()

    def save_keystrokes(self, session_id: str, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Save multiple keystrokes for a session.
        """
        return Keystroke.save_many(session_id, keystrokes)

    def delete_keystrokes_by_session(self, session_id: int) -> bool:
        """
        Delete all keystrokes for a given session ID.
        """
        try:
            self.db_manager.execute(
                "DELETE FROM session_keystrokes WHERE session_id = ?",
                (session_id,)
            )
            return True
        except Exception as e:
            print(f"Error deleting keystrokes for session {session_id}: {e}")
            return False

    def delete_all(self) -> bool:
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

    def count_keystrokes_per_session(self, session_id: int) -> int:
        """
        Count the number of keystrokes for a specific session.

        Args:
            session_id: The ID of the session to count keystrokes for

        Returns:
            int: The number of keystrokes for the session, or 0 if an error occurs
        """
        try:
            result = self.db_manager.fetchone(
                """
                SELECT COUNT(*)
                FROM session_keystrokes
                WHERE session_id = ?
                """,
                (session_id,)
            )
            return result[0] if result and result[0] is not None else 0
        except Exception as e:
            print(f"Error counting keystrokes for session {session_id}: {e}")
            return 0
