"""
Keystroke model for tracking keystrokes during practice sessions.
"""

import datetime
import logging
import sys
from typing import Any, Dict, List, Optional

from db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Keystroke:
    """
    Model class for tracking individual keystrokes in practice sessions.
    """

    def __init__(
        self,
        session_id: Optional[int] = None,
        keystroke_id: Optional[int] = None,
        keystroke_time: Optional[datetime.datetime] = None,
        keystroke_char: str = "",
        expected_char: str = "",
        is_correct: bool = False,
        error_type: Optional[str] = None,
        time_since_previous: Optional[int] = None,
    ) -> None:
        """Initialize a Keystroke instance.
        
        Args:
            session_id: The ID of the session this keystroke belongs to
            keystroke_id: The unique ID of the keystroke
            keystroke_time: When the keystroke occurred
            keystroke_char: The actual character that was typed
            expected_char: The expected character that should have been typed
            is_correct: Whether the keystroke was correct
            error_type: Type of error if the keystroke was incorrect
            time_since_previous: Time in ms since the previous keystroke
        """
        self.session_id: Optional[int] = session_id
        self.keystroke_id: Optional[int] = keystroke_id
        self.keystroke_time: datetime.datetime = (
            keystroke_time or datetime.datetime.now()
        )
        self.keystroke_char: str = keystroke_char
        self.expected_char: str = expected_char
        self.is_correct: bool = is_correct
        self.error_type: Optional[str] = error_type
        self.time_since_previous: Optional[int] = time_since_previous
        self.db: DatabaseManager = DatabaseManager()

    def save(self, db_manager: Optional[DatabaseManager] = None) -> bool:
        """Save this keystroke to the session_keystrokes table.
        
        Args:
            db_manager: Optional database manager to use. If None, creates a new one.
        
        Returns:
            bool: True if the save was successful, False otherwise
        """
        db = db_manager or self.db if hasattr(self, "db") else DatabaseManager()
        try:
            # Convert session_id to string to match schema
            session_id_str = str(self.session_id) if self.session_id is not None else ""
            
            if not session_id_str:
                print(
                    f"Error: Invalid or missing session_id ({self.session_id}) for keystroke save.",
                    file=sys.stderr,
                )
                return False

            # Insert the keystroke (let database auto-generate keystroke_id)
            db.execute(
                """
                INSERT INTO session_keystrokes 
                (session_id, key_char, timestamp)
                VALUES (?, ?, ?)
                """,
                (
                    session_id_str,
                    self.keystroke_char,
                    self.keystroke_time.timestamp()
                ),
            )
            return True
        except Exception as e:
            # No need to import sys here

            print(f"Error saving keystroke: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Keystroke":
        """Create a Keystroke instance from a dictionary, ensuring integer IDs."""
        # Handle datetime conversion
        keystroke_time = data.get("keystroke_time")
        if isinstance(keystroke_time, str):
            try:
                keystroke_time = datetime.datetime.fromisoformat(
                    keystroke_time.replace("Z", "+00:00")
                )
            except ValueError:
                keystroke_time = datetime.datetime.now()

        # Handle boolean conversion
        is_correct = data.get("is_correct")
        if isinstance(is_correct, str):
            is_correct = is_correct.lower() in ("true", "1", "t", "y", "yes")
        elif isinstance(is_correct, int):
            is_correct = bool(is_correct)
        if not isinstance(is_correct, bool):
            is_correct = bool(is_correct)

        # Ensure IDs are integers
        session_id = data.get("session_id")
        if session_id is not None and not isinstance(session_id, int):
            try:
                session_id = int(session_id)
            except (ValueError, TypeError):
                session_id = None

        keystroke_id = data.get("keystroke_id")
        if keystroke_id is not None and not isinstance(keystroke_id, int):
            try:
                keystroke_id = int(keystroke_id)
            except (ValueError, TypeError):
                keystroke_id = None

        return cls(
            session_id=session_id,
            keystroke_id=keystroke_id,
            keystroke_time=keystroke_time,
            keystroke_char=data.get("keystroke_char", ""),
            expected_char=data.get("expected_char", ""),
            is_correct=is_correct,
            time_since_previous=data.get("time_since_previous"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the keystroke to a dictionary with integer IDs."""
        return {
            "session_id": self.session_id,
            "keystroke_id": self.keystroke_id,
            "keystroke_time": (
                self.keystroke_time.isoformat() if self.keystroke_time else None
            ),
            "keystroke_char": self.keystroke_char,
            "expected_char": self.expected_char,
            "is_correct": self.is_correct,
            "time_since_previous": self.time_since_previous,
        }    @classmethod
    def save_many(cls, session_id: int, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Save multiple keystrokes at once for a practice session.

        Args:
            session_id: The ID of the practice session  
            keystrokes: A list of keystroke data dictionaries

        Returns:
            bool: True if successful, False otherwise
        """
        if not keystrokes:
            print(
                f"Error: Empty keystrokes list in save_many for session {session_id}.",
                file=sys.stderr,
            )
            return False

        try:
            db = DatabaseManager()
            session_id_str = str(session_id)
            
            # Insert keystrokes one by one (simple approach)
            for k_data in keystrokes:
                # Convert keystroke_time if it's a string
                k_time = k_data.get("keystroke_time")
                if isinstance(k_time, str):
                    try:
                        keystroke_time = datetime.datetime.fromisoformat(k_time)
                    except ValueError:
                        keystroke_time = datetime.datetime.now()
                else:
                    keystroke_time = k_time or datetime.datetime.now()

                # Insert the keystroke (let database auto-generate keystroke_id)
                db.execute(
                    """
                    INSERT INTO session_keystrokes 
                    (session_id, key_char, timestamp)
                    VALUES (?, ?, ?)
                    """,
                    (
                        session_id_str,
                        k_data.get("keystroke_char", ""),
                        keystroke_time.timestamp()
                    ),
                )

            return True

        except Exception as e:
            print(f"Error saving keystrokes: {e}", file=sys.stderr)
            return False

    @classmethod
    def get_for_session(cls, session_id: int) -> List["Keystroke"]:
        """Get all keystrokes for an integer practice session ID.
        
        Args:
            session_id: The ID of the session to get keystrokes for
            
        Returns:
            List[Keystroke]: List of Keystroke objects for the session
        """
        try:
            db = DatabaseManager()
            query = """
                SELECT *
                FROM session_keystrokes
                WHERE session_id = ?
                ORDER BY keystroke_id
            """
            results = db.execute_query(query, (session_id,))
            return [cls.from_dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error getting keystrokes for session {session_id}: {e}", file=sys.stderr)
            return []

    @classmethod
    def get_errors_for_session(cls, session_id: int) -> List["Keystroke"]:
        """Get all error keystrokes for an integer practice session ID.
        
        Args:
            session_id: The ID of the session to get error keystrokes for
            
        Returns:
            List[Keystroke]: List of Keystroke objects with errors for the session
        """
        try:
            db = DatabaseManager()
            query = """
                SELECT *
                FROM session_keystrokes
                WHERE session_id = ? AND is_correct = 0
                ORDER BY keystroke_id
            """
            results = db.execute_query(query, (session_id,))
            return [cls.from_dict(row) for row in results] if results else []
        except Exception as e:
            print(f"Error getting error keystrokes for session {session_id}: {e}", file=sys.stderr)
            return []
    
    @classmethod
    def delete_all_keystrokes(cls, db: DatabaseManager) -> bool:
        """
        Delete all keystrokes from the database.
        
        This will clear the session_keystrokes table.
        
        Args:
            db: DatabaseManager instance to use for the operation
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Deleting all keystrokes from database")
            db.execute("DELETE FROM session_keystrokes", ())
            return True
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error deleting keystrokes: %s", str(e))
            return False
