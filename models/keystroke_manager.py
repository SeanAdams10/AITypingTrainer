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
        return keystroke.save(self.db_manager)

    def save_keystrokes(self, session_id: str, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Save multiple keystrokes for a session.
        
        Args:
            session_id: The ID of the session to save keystrokes for (UUID string)
            keystrokes: List of keystroke data dictionaries
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create keystrokes manually and save each one to reuse the db_manager
            for keystroke_data in keystrokes:
                # Make sure the session_id in the keystroke data matches the parameter
                keystroke_data["session_id"] = session_id
                
                # Create a Keystroke object and save it
                keystroke = Keystroke.from_dict(keystroke_data)
                if not keystroke.save(self.db_manager):
                    return False
                    
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
                "DELETE FROM session_keystrokes WHERE session_id = ?",
                (session_id,)
            )
            return True
        except Exception as e:
            import sys
            print(f"Error deleting keystrokes for session {session_id}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
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
