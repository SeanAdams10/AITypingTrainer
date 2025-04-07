"""
Keystroke model for tracking keystrokes during practice sessions.
"""
from typing import Dict, List, Any, Optional, Union
import datetime
from ..database_manager import DatabaseManager


class Keystroke:
    """
    Model class for tracking individual keystrokes in practice sessions.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        keystroke_id: Optional[int] = None,
        keystroke_time: Optional[datetime.datetime] = None,
        keystroke_char: str = "",
        expected_char: str = "",
        is_correct: bool = False,
        time_since_previous: Optional[int] = None
    ):
        """Initialize a Keystroke instance."""
        self.session_id = session_id
        self.keystroke_id = keystroke_id
        self.keystroke_time = keystroke_time or datetime.datetime.now()
        self.keystroke_char = keystroke_char
        self.expected_char = expected_char
        self.is_correct = is_correct
        self.time_since_previous = time_since_previous
        self.db = DatabaseManager()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Keystroke':
        """Create a Keystroke instance from a dictionary."""
        # Handle datetime conversion
        keystroke_time = data.get('keystroke_time')
        if isinstance(keystroke_time, str):
            try:
                keystroke_time = datetime.datetime.fromisoformat(keystroke_time.replace('Z', '+00:00'))
            except ValueError:
                keystroke_time = datetime.datetime.now()
        
        # Handle boolean conversion
        is_correct = data.get('is_correct')
        if isinstance(is_correct, str):
            is_correct = is_correct.lower() in ('true', '1', 't', 'y', 'yes')
        elif isinstance(is_correct, int):
            is_correct = bool(is_correct)
        
        return cls(
            session_id=data.get('session_id'),
            keystroke_id=data.get('keystroke_id'),
            keystroke_time=keystroke_time,
            keystroke_char=data.get('keystroke_char', ''),
            expected_char=data.get('expected_char', ''),
            is_correct=is_correct,
            time_since_previous=data.get('time_since_previous')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the keystroke to a dictionary."""
        return {
            'session_id': self.session_id,
            'keystroke_id': self.keystroke_id,
            'keystroke_time': self.keystroke_time.isoformat() if self.keystroke_time else None,
            'keystroke_char': self.keystroke_char,
            'expected_char': self.expected_char,
            'is_correct': self.is_correct,
            'time_since_previous': self.time_since_previous
        }
    
    @classmethod
    def save_many(cls, session_id: str, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Save multiple keystrokes at once for a practice session.
        
        Args:
            session_id: The ID of the practice session
            keystrokes: A list of keystroke data dictionaries
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not session_id or not keystrokes:
            return False
        
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare the insertion queries
            keystroke_query = """
                INSERT INTO practice_session_keystrokes
                (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            error_query = """
                INSERT INTO practice_session_errors
                (session_id, error_id, keystroke_id, keystroke_char, expected_char)
                VALUES (?, ?, ?, ?, ?)
            """
            
            # Insert keystrokes
            error_count = 0
            for i, k in enumerate(keystrokes):
                # Convert keystroke_time from ISO format to datetime if necessary
                k_time = k.get('keystroke_time')
                if isinstance(k_time, str):
                    try:
                        k_time = datetime.datetime.fromisoformat(k_time.replace('Z', '+00:00'))
                    except ValueError:
                        k_time = datetime.datetime.now()
                
                # Determine if the keystroke is correct
                is_correct = k.get('is_correct', False)
                
                # Insert keystroke
                cursor.execute(keystroke_query, (
                    session_id,
                    i,  # keystroke_id is the index
                    k_time,
                    k.get('keystroke_char', ''),
                    k.get('expected_char', ''),
                    is_correct,
                    k.get('time_since_previous')
                ))
                
                # If it's an error, add to errors table
                if not is_correct:
                    cursor.execute(error_query, (
                        session_id,
                        error_count,  # error_id
                        i,  # keystroke_id
                        k.get('keystroke_char', ''),
                        k.get('expected_char', '')
                    ))
                    error_count += 1
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving keystrokes: {e}")
            conn.rollback()
            return False
            
        finally:
            conn.close()
    
    @classmethod
    def get_for_session(cls, session_id: str) -> List['Keystroke']:
        """Get all keystrokes for a practice session."""
        db = DatabaseManager()
        query = """
            SELECT *
            FROM practice_session_keystrokes
            WHERE session_id = ?
            ORDER BY keystroke_id
        """
        results = db.execute_query(query, (session_id,))
        
        return [cls.from_dict(row) for row in results]
    
    @classmethod
    def get_errors_for_session(cls, session_id: str) -> List['Keystroke']:
        """Get all error keystrokes for a practice session."""
        db = DatabaseManager()
        query = """
            SELECT k.*
            FROM practice_session_keystrokes k
            JOIN practice_session_errors e ON k.session_id = e.session_id AND k.keystroke_id = e.keystroke_id
            WHERE k.session_id = ?
            ORDER BY k.keystroke_id
        """
        results = db.execute_query(query, (session_id,))
        
        return [cls.from_dict(row) for row in results]
