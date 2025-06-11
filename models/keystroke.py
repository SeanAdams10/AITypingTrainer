"""
Keystroke model for tracking keystrokes during practice sessions.
"""

import datetime
import logging
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from db.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Keystroke(BaseModel):
    """
    Pydantic model for tracking individual keystrokes in practice sessions.
    """

    session_id: Optional[str] = None
    keystroke_id: Optional[str] = None  # Changed from int to str (UUID)
    keystroke_time: datetime.datetime = Field(default_factory=datetime.datetime.now)
    keystroke_char: str = ""
    expected_char: str = ""
    is_error: bool = False
    time_since_previous: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Keystroke":
        """Create a Keystroke instance from a dictionary, ensuring UUID IDs."""
        # Handle datetime conversion
        keystroke_time = data.get("keystroke_time")
        if isinstance(keystroke_time, str):
            try:
                keystroke_time = datetime.datetime.fromisoformat(
                    keystroke_time.replace("Z", "+00:00")
                )
            except ValueError:
                keystroke_time = datetime.datetime.now()
        if not isinstance(keystroke_time, datetime.datetime):
            keystroke_time = datetime.datetime.now()

        # Handle boolean conversion
        is_error = data.get("is_error")
        if isinstance(is_error, str):
            is_error = is_error.lower() in ("true", "1", "t", "y", "yes")
        elif isinstance(is_error, int):
            is_error = bool(is_error)
        if not isinstance(is_error, bool):
            is_error = bool(is_error)

        # Ensure IDs are UUID strings
        session_id = data.get("session_id")
        if session_id is not None and not isinstance(session_id, str):
            try:
                session_id = str(session_id)
            except (ValueError, TypeError):
                session_id = None
        if not isinstance(session_id, str) or session_id.startswith("{"):
            session_id = None

        keystroke_id = data.get("keystroke_id")
        if keystroke_id is None:
            keystroke_id = str(uuid.uuid4())
        elif not isinstance(keystroke_id, str):
            try:
                keystroke_id = str(keystroke_id)
            except (ValueError, TypeError):
                keystroke_id = str(uuid.uuid4())

        return cls(
            session_id=session_id,
            keystroke_id=keystroke_id,
            keystroke_time=keystroke_time,
            keystroke_char=data.get("keystroke_char", ""),
            expected_char=data.get("expected_char", ""),
            is_error=is_error,
            time_since_previous=data.get("time_since_previous"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the keystroke to a dictionary with UUID IDs."""
        return {
            "session_id": self.session_id,
            "keystroke_id": self.keystroke_id,
            "keystroke_time": (self.keystroke_time.isoformat() if self.keystroke_time else None),
            "keystroke_char": self.keystroke_char,
            "expected_char": self.expected_char,
            "is_error": self.is_error,
            "time_since_previous": self.time_since_previous,
        }

    @classmethod
    def get_for_session(cls, session_id: str) -> List["Keystroke"]:
        """Get all keystrokes for a practice session ID.

        Args:
            session_id: The ID of the session to get keystrokes for

        Returns:
            List[Keystroke]: List of Keystroke objects for the session
        """
        db = DatabaseManager()
        query = "SELECT * FROM session_keystrokes WHERE session_id = ? ORDER BY keystroke_id"
        results = db.fetchall(query, (session_id,))
        return [cls.from_dict(dict(row)) for row in results] if results else []

    @classmethod
    def get_errors_for_session(cls, session_id: str) -> List["Keystroke"]:
        """Get all error keystrokes for a practice session ID.

        Args:
            session_id: The ID of the session to get error keystrokes for

        Returns:
            List[Keystroke]: List of Keystroke objects with errors for the session
        """
        db = DatabaseManager()
        query = (
            "SELECT * FROM session_keystrokes WHERE session_id = ? AND is_error = 1 "
            "ORDER BY keystroke_id"
        )
        results = db.fetchall(query, (session_id,))
        return [cls.from_dict(dict(row)) for row in results] if results else []

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
        except Exception as e:
            logger.error("Error deleting keystrokes: %s", str(e))
            return False
