"""
PracticeSession model class for tracking typing practice sessions.
"""
from typing import Dict, List, Any, Optional, Union
import datetime
from ..database_manager import DatabaseManager


class PracticeSession:
    """
    Model class for practice sessions in the typing trainer application.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        snippet_id: Optional[int] = None,
        snippet_index_start: int = 0,
        snippet_index_end: int = 0,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        total_time: Optional[float] = None,
        session_wpm: Optional[float] = None,
        session_cpm: Optional[float] = None,
        expected_chars: Optional[int] = None,
        actual_chars: Optional[int] = None,
        errors: Optional[int] = None,
        accuracy: Optional[float] = None,
        practice_type: str = 'beginning'
    ):
        """Initialize a PracticeSession instance."""
        self.session_id = session_id
        self.snippet_id = snippet_id
        self.snippet_index_start = snippet_index_start
        self.snippet_index_end = snippet_index_end
        self.start_time = start_time or datetime.datetime.now()
        self.end_time = end_time
        self.total_time = total_time
        self.session_wpm = session_wpm
        self.session_cpm = session_cpm
        self.expected_chars = expected_chars
        self.actual_chars = actual_chars
        self.errors = errors
        self.accuracy = accuracy
        self.practice_type = practice_type
        self.db = DatabaseManager()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PracticeSession':
        """Create a PracticeSession instance from a dictionary."""
        # Handle datetime conversions
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            try:
                start_time = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                start_time = datetime.datetime.now()
        
        end_time = data.get('end_time')
        if isinstance(end_time, str) and end_time:
            try:
                end_time = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                end_time = None
        
        return cls(
            session_id=data.get('session_id'),
            snippet_id=data.get('snippet_id'),
            snippet_index_start=data.get('snippet_index_start', 0),
            snippet_index_end=data.get('snippet_index_end', 0),
            start_time=start_time,
            end_time=end_time,
            total_time=data.get('total_time'),
            session_wpm=data.get('session_wpm'),
            session_cpm=data.get('session_cpm'),
            expected_chars=data.get('expected_chars'),
            actual_chars=data.get('actual_chars'),
            errors=data.get('errors'),
            accuracy=data.get('accuracy'),
            practice_type=data.get('practice_type', 'beginning')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the practice session to a dictionary."""
        return {
            'session_id': self.session_id,
            'snippet_id': self.snippet_id,
            'snippet_index_start': self.snippet_index_start,
            'snippet_index_end': self.snippet_index_end,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_time': self.total_time,
            'session_wpm': self.session_wpm,
            'session_cpm': self.session_cpm,
            'expected_chars': self.expected_chars,
            'actual_chars': self.actual_chars,
            'errors': self.errors,
            'accuracy': self.accuracy,
            'practice_type': self.practice_type
        }
    
    def start(self) -> bool:
        """Start a new practice session."""
        if self.session_id is not None:
            return False  # Session already started
        
        if self.snippet_id is None:
            return False  # Cannot start without a snippet
        
        # Generate a session ID
        self.session_id = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{self.snippet_id}"
        self.start_time = datetime.datetime.now()
        
        query = """
            INSERT INTO practice_sessions 
            (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time, practice_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        success = self.db.execute_update(query, (
            self.session_id,
            self.snippet_id,
            self.snippet_index_start,
            self.snippet_index_end,
            self.start_time,
            self.practice_type
        ))
        
        return success
    
    def end(self, stats: Dict[str, Any]) -> bool:
        """End a practice session and record the stats."""
        if self.session_id is None:
            return False  # Session not started
        
        self.end_time = datetime.datetime.now()
        
        # Calculate total time in seconds
        if self.start_time:
            self.total_time = (self.end_time - self.start_time).total_seconds()
        
        # Update session with stats
        self.session_wpm = stats.get('wpm')
        self.session_cpm = stats.get('cpm')
        self.expected_chars = stats.get('expected_chars')
        self.actual_chars = stats.get('actual_chars')
        self.errors = stats.get('errors')
        self.accuracy = stats.get('accuracy')
        
        query = """
            UPDATE practice_sessions
            SET end_time = ?, total_time = ?, session_wpm = ?, session_cpm = ?,
                expected_chars = ?, actual_chars = ?, errors = ?, accuracy = ?
            WHERE session_id = ?
        """
        
        success = self.db.execute_update(query, (
            self.end_time,
            self.total_time,
            self.session_wpm,
            self.session_cpm,
            self.expected_chars,
            self.actual_chars,
            self.errors,
            self.accuracy,
            self.session_id
        ))
        
        return success
    
    @classmethod
    def get_by_id(cls, session_id: str) -> Optional['PracticeSession']:
        """Get a practice session by its ID."""
        db = DatabaseManager()
        query = "SELECT * FROM practice_sessions WHERE session_id = ?"
        results = db.execute_query(query, (session_id,))
        
        if not results:
            return None
        
        return cls.from_dict(results[0])
    
    @classmethod
    def get_latest_by_snippet(cls, snippet_id: int) -> Optional['PracticeSession']:
        """Get the most recent practice session for a snippet."""
        db = DatabaseManager()
        query = """
            SELECT *
            FROM practice_sessions
            WHERE snippet_id = ?
            ORDER BY start_time DESC
            LIMIT 1
        """
        results = db.execute_query(query, (snippet_id,))
        
        if not results:
            return None
        
        return cls.from_dict(results[0])
    
    @classmethod
    def get_progress_data(cls, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get practice session data for progress tracking, optionally filtered by category_id.
        """
        db = DatabaseManager()
        
        if category_id is None:
            # Get all practice sessions with category info
            query = """
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time, 
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id, tc.category_name, ts.snippet_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                WHERE ps.end_time IS NOT NULL
                ORDER BY ps.start_time
            """
            return db.execute_query(query)
        else:
            # Get practice sessions filtered by category
            query = """
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time, 
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id, tc.category_name, ts.snippet_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                WHERE ps.end_time IS NOT NULL AND ts.category_id = ?
                ORDER BY ps.start_time
            """
            return db.execute_query(query, (category_id,))
    
    @classmethod
    def delete_by_snippet_id(cls, snippet_id: int) -> bool:
        """
        Delete all practice sessions associated with a specific snippet.
        """
        db = DatabaseManager()
        try:
            # First get all session_ids for this snippet
            query_get_sessions = "SELECT session_id FROM practice_sessions WHERE snippet_id = ?"
            sessions = db.execute_query(query_get_sessions, (snippet_id,))
            
            if not sessions:
                return True  # No sessions to delete
                
            # Get connection to execute multiple operations
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # For each session, delete related data first
            for session in sessions:
                session_id = session['session_id']
                
                # Delete keystrokes
                cursor.execute("DELETE FROM practice_session_keystrokes WHERE session_id = ?", (session_id,))
                
                # Delete any errors records
                cursor.execute("DELETE FROM practice_session_errors WHERE session_id = ?", (session_id,))
                
                # Delete any bigram speed records
                cursor.execute("DELETE FROM session_bigram_speed WHERE session_id = ?", (session_id,))
                
                # Delete any trigram speed records
                cursor.execute("DELETE FROM session_trigram_speed WHERE session_id = ?", (session_id,))
                
                # Delete any bigram error records
                cursor.execute("DELETE FROM session_bigram_error WHERE session_id = ?", (session_id,))
                
                # Delete any trigram error records
                cursor.execute("DELETE FROM session_trigram_error WHERE session_id = ?", (session_id,))
            
            # Finally delete the sessions themselves
            cursor.execute("DELETE FROM practice_sessions WHERE snippet_id = ?", (snippet_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting practice sessions for snippet {snippet_id}: {e}")
            return False
    
    @classmethod
    def reset_session_data(cls) -> bool:
        """
        Clear all session data by dropping and recreating the tables.
        """
        db = DatabaseManager()
        
        # Tables to reset in order (to handle foreign key dependencies)
        tables = [
            "session_trigram_error",
            "session_bigram_error",
            "session_trigram_speed",
            "session_bigram_speed",
            "practice_session_errors",
            "practice_session_keystrokes",
            "practice_sessions"
        ]
        
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Drop and recreate each table
            for table in tables:
                # Save CREATE statement for the table
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
                result = cursor.fetchone()
                
                if result:
                    create_stmt = result['sql']
                    
                    # Drop the table
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    
                    # Recreate the table
                    cursor.execute(create_stmt)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error resetting session data: {e}")
            return False
