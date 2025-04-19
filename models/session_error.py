"""
SessionError model for tracking errors during typing practice sessions.
"""
from typing import Dict, Any, Optional
import datetime
from db.database_manager import DatabaseManager


class SessionError:
    """
    Model class for tracking individual errors in practice sessions.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        error_id: Optional[int] = None,
        error_type: str = "",
        error_location: Optional[int] = None,
        error_char: str = "",
        expected_char: str = "",
        timestamp: Optional[datetime.datetime] = None
    ):
        """Initialize a SessionError instance."""
        self.session_id = session_id
        self.error_id = error_id
        self.error_type = error_type  # e.g., 'substitution', 'omission', etc.
        self.error_location = error_location
        self.error_char = error_char
        self.expected_char = expected_char
        self.timestamp = timestamp or datetime.datetime.now()
        self.db = DatabaseManager()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionError':
        """Create a SessionError instance from a dictionary."""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                timestamp = datetime.datetime.now()
        return cls(
            session_id=data.get('session_id'),
            error_id=data.get('error_id'),
            error_type=data.get('error_type', ''),
            error_location=data.get('error_location'),
            error_char=data.get('error_char', ''),
            expected_char=data.get('expected_char', ''),
            timestamp=timestamp
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the session error to a dictionary."""
        return {
            'session_id': self.session_id,
            'error_id': self.error_id,
            'error_type': self.error_type,
            'error_location': self.error_location,
            'error_char': self.error_char,
            'expected_char': self.expected_char,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def save(self) -> bool:
        """Save the session error to the database."""
        if self.error_id is None:
            # Insert new error
            query = ("INSERT INTO practice_session_errors "
                     "(session_id, error_type, error_location, error_char, expected_char, timestamp) "
                     "VALUES (?, ?, ?, ?, ?, ?)")
            error_id = self.db.execute_insert(query, (
                self.session_id, self.error_type, self.error_location,
                self.error_char, self.expected_char, self.timestamp.isoformat()
            ))
            if error_id > 0:
                self.error_id = error_id
                return True
            return False
        else:
            # Update existing error
            query = ("UPDATE practice_session_errors SET "
                     "error_type = ?, error_location = ?, error_char = ?, expected_char = ?, timestamp = ? "
                     "WHERE error_id = ?")
            return self.db.execute_update(query, (
                self.error_type, self.error_location, self.error_char,
                self.expected_char, self.timestamp.isoformat(), self.error_id
            ))
    
    @classmethod
    def get_by_session(cls, session_id: str) -> list:
        """Get all errors for a given session."""
        db = DatabaseManager()
        query = "SELECT * FROM practice_session_errors WHERE session_id = ?"
        rows = db.execute_query(query, (session_id,))
        return [cls.from_dict(row) for row in rows]
    
    def delete(self) -> bool:
        """Delete this error from the database."""
        if self.error_id is None:
            return False
        query = "DELETE FROM practice_session_errors WHERE error_id = ?"
        return self.db.execute_update(query, (self.error_id,))
