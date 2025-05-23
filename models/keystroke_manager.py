from typing import List, Dict, Any, Optional
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

    def save_keystrokes(self, session_id: int, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Save multiple keystrokes for a session.
        """
        return Keystroke.save_many(session_id, keystrokes)

    def delete_keystrokes_by_session(self, session_id: int) -> bool:
        """
        Delete all keystrokes for a given session ID.
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM session_keystrokes WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting keystrokes for session {session_id}: {e}")
            return False
