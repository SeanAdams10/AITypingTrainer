"""
PracticeSession model class for tracking typing practice sessions.
"""
from typing import Dict, List, Any, Optional
import datetime
import sqlite3
from db.database_manager import DatabaseManager


class PracticeSession:
    """
    Model class for practice sessions in the typing trainer application.
    """

    def save(self) -> bool:
        """
        Save the practice session to the database.
        If session_id is not set, generate a unique one.
        Returns True if successful, False otherwise.
        """
        if self.session_id is None:
            # Generate a unique session_id: timestamp + snippet_id
            timestamp = int(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            if self.snippet_id is not None:
                try:
                    self.session_id = int(f"{timestamp}{self.snippet_id}")
                except ValueError:
                    self.session_id = timestamp
            else:
                self.session_id = timestamp
        if self.start_time is None:
            self.start_time = datetime.datetime.now()
        query = """
            INSERT INTO practice_sessions
            (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time, practice_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            success = self.db.execute_update(query, (
                self.session_id,
                self.snippet_id,
                self.snippet_index_start if self.snippet_index_start is not None else 0,
                self.snippet_index_end if self.snippet_index_end is not None else 0,
                self.start_time,
                self.practice_type
            ))
            if not success:
                print("Failed to insert session into practice_sessions table.")
            return success
        except sqlite3.DatabaseError as e:
            print(f"Error saving session: {e}")
            return False

    @classmethod
    def get_session_info(cls, snippet_id: int) -> dict:
        """
        Get last session indices and snippet length for a snippet_id.
        Returns dict with last_start_index, last_end_index, snippet_length.
        """
        db = DatabaseManager()
        # Get last session indices
        session = db.execute_query(
            "SELECT snippet_index_start, snippet_index_end "
            "FROM practice_sessions "
            "WHERE snippet_id = ? "
            "ORDER BY start_time DESC "
            "LIMIT 1",
            (snippet_id,)
        )
        last_start = session[0]['snippet_index_start'] if session else None
        last_end = session[0]['snippet_index_end'] if session else None
        # Get snippet length (sum of all parts)
        length_row = db.execute_query(
            "SELECT SUM(LENGTH(content)) as total_length "
            "FROM snippet_parts "
            "WHERE snippet_id = ?",
            (snippet_id,)
        )
        snippet_length = (
            length_row[0]['total_length']
            if length_row and length_row[0]['total_length'] is not None
            else 0
        )
        return {
            'last_start_index': last_start,
            'last_end_index': last_end,
            'snippet_length': snippet_length
        }
   
    def __init__(
        self,
        session_id: Optional[int] = None,
        snippet_id: Optional[int] = None,
        snippet_index_start: Optional[int] = None,
        snippet_index_end: Optional[int] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        total_time: Optional[int] = None,
        session_wpm: Optional[float] = None,
        session_cpm: Optional[float] = None,
        expected_chars: Optional[int] = None,
        actual_chars: Optional[int] = None,
        errors: Optional[int] = None,
        accuracy: Optional[float] = None,
        practice_type: str = 'beginning'
    ) -> None:
        """Initialize a PracticeSession instance."""
        self.session_id: Optional[int] = session_id
        self.snippet_id: Optional[int] = snippet_id
        self.snippet_index_start: Optional[int] = snippet_index_start
        self.snippet_index_end: Optional[int] = snippet_index_end
        self.start_time: datetime.datetime = start_time or datetime.datetime.now()
        self.end_time: Optional[datetime.datetime] = end_time
        self.total_time: Optional[int] = total_time
        self.session_wpm: Optional[float] = session_wpm
        self.session_cpm: Optional[float] = session_cpm
        self.expected_chars: Optional[int] = expected_chars
        self.actual_chars: Optional[int] = actual_chars
        self.errors: Optional[int] = errors
        self.accuracy: Optional[float] = accuracy
        self.practice_type: str = practice_type
        self.db: DatabaseManager = DatabaseManager()

   
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PracticeSession':
        """Create a PracticeSession instance from a dictionary, ensuring all fields are set."""
        # Handle datetime conversions
        start_time = data.get('start_time')
        if isinstance(start_time, str):
            try:
                start_time = datetime.datetime.fromisoformat(start_time)
            except ValueError:
                start_time = datetime.datetime.now()
        elif start_time is None:
            start_time = datetime.datetime.now()
        end_time = data.get('end_time')
        if isinstance(end_time, str) and end_time:
            try:
                end_time = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                end_time = None
        elif not isinstance(end_time, datetime.datetime):
            end_time = None
        session_id = data.get('session_id')
        if session_id is not None and not isinstance(session_id, int):
            try:
                session_id = int(session_id)
            except (ValueError, TypeError):
                session_id = None
        # Always set all fields, using defaults if missing
        return cls(
            session_id=session_id,
            snippet_id=data.get('snippet_id'),
            snippet_index_start=data.get('snippet_index_start', 0),
            snippet_index_end=data.get('snippet_index_end', 0),
            start_time=start_time,
            end_time=end_time,
            total_time=data.get('total_time', 0),
            session_wpm=data.get('session_wpm', 0.0),
            session_cpm=data.get('session_cpm', 0),
            expected_chars=data.get('expected_chars', 0),
            actual_chars=data.get('actual_chars', 0),
            errors=data.get('errors', 0),
            accuracy=data.get('accuracy', 0.0),
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
            print("Session already started.")
            return False  # Session already started

        if self.snippet_id is None:
            print("Cannot start session without a snippet ID.")
            return False  # Cannot start without a snippet

        # Generate a unique integer session ID (timestamp + snippet_id)
        timestamp = int(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
        if self.snippet_id is not None:
            # Combine timestamp and snippet_id, but avoid line too long
            try:
                self.session_id = int(f"{timestamp}{self.snippet_id}")
            except ValueError:
                self.session_id = timestamp
        else:
            self.session_id = timestamp
        self.start_time = datetime.datetime.now()

        # Ensure snippet_index_start and snippet_index_end are int
        snippet_index_start = self.snippet_index_start if isinstance(self.snippet_index_start, int) else 0
        snippet_index_end = self.snippet_index_end if isinstance(self.snippet_index_end, int) else 0

        query = """
            INSERT INTO practice_sessions
            (session_id, snippet_id, snippet_index_start, snippet_index_end, start_time, practice_type)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        try:
            success = self.db.execute_update(query, (
                self.session_id,
                self.snippet_id,
                snippet_index_start,
                snippet_index_end,
                self.start_time,
                self.practice_type
            ))

            if not success:
                print("Failed to insert session into practice_sessions table.")
            return success

        except sqlite3.DatabaseError as e:
            print(f"Error starting session: {e}")
            return False
   
    def end(self, stats: Dict[str, Any]) -> bool:
        """End a practice session and record the stats."""
        if self.session_id is None:
            return False  # Session not started
       
        self.end_time = datetime.datetime.now()
       
        # Calculate total time in seconds
        if self.start_time:
            self.total_time = int((self.end_time - self.start_time).total_seconds())
       
        # Update session with stats
        self.session_wpm = stats.get('wpm')
        self.session_cpm = stats.get('session_cpm')
        if self.session_cpm is not None:
            try:
                self.session_cpm = float(self.session_cpm)
            except (ValueError, TypeError):
                self.session_cpm = None
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
           
        except sqlite3.DatabaseError as e:
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
           
        except sqlite3.DatabaseError as e:
            print(f"Error resetting session data: {e}")
            return False
