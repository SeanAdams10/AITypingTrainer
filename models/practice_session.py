#!/usr/bin/env python
"""
PracticeSession model class for tracking typing practice sessions.
"""
from typing import Dict, List, Any, Optional
import datetime
import sqlite3
from db import DatabaseManager


class PracticeSession:
    """Model class for practice sessions in the typing trainer application."""

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
        accuracy: Optional[float] = None
    ) -> None:  # pylint: disable=too-many-arguments, too-many-locals
        """Initialize a PracticeSession instance."""
        self.session_id: Optional[int] = session_id
        self.snippet_id: Optional[int] = snippet_id
        self.snippet_index_start: Optional[int] = snippet_index_start
        self.snippet_index_end: Optional[int] = snippet_index_end
        self.start_time: datetime.datetime = (
            start_time if start_time is not None else datetime.datetime.now()
        )
        self.end_time: Optional[datetime.datetime] = end_time
        self.total_time: Optional[int] = total_time
        self.session_wpm: Optional[float] = session_wpm
        self.session_cpm: Optional[float] = session_cpm
        self.expected_chars: Optional[int] = expected_chars
        self.actual_chars: Optional[int] = actual_chars
        self.errors: Optional[int] = errors
        self.accuracy: Optional[float] = accuracy

    def save(self) -> bool:
        """
        Save the practice session to the database.
        If session_id is None, a new session is created and the integer ID is assigned.
        If session_id is set, the existing session is updated.
        Returns True if successful, False otherwise.
        """
        try:
            db = DatabaseManager.get_instance()

            if self.session_id is None:
                query = (
                    """
                    INSERT INTO practice_sessions (
                        snippet_id, snippet_index_start, snippet_index_end,
                        start_time, end_time, total_time, session_wpm,
                        session_cpm, expected_chars, actual_chars,
                        errors, accuracy
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                )
                params = (
                    self.snippet_id, self.snippet_index_start, self.snippet_index_end,
                    self.start_time.isoformat() if self.start_time else None,
                    self.end_time.isoformat() if self.end_time else None,
                    self.total_time, self.session_wpm, self.session_cpm,
                    self.expected_chars, self.actual_chars, self.errors,
                    self.accuracy
                )
                new_id = db.execute_insert(query, params)
                if new_id > 0:
                    self.session_id = new_id
                    return True
                else:
                    print("Error: Failed to insert new practice session.")
                    return False
            else:
                query = (
                    """
                    UPDATE practice_sessions SET
                        snippet_id = ?, snippet_index_start = ?, snippet_index_end = ?,
                        start_time = ?, end_time = ?, total_time = ?, session_wpm = ?,
                        session_cpm = ?, expected_chars = ?, actual_chars = ?,
                        errors = ?, accuracy = ?
                    WHERE session_id = ?
                    """
                )
                params = (
                    self.snippet_id, self.snippet_index_start, self.snippet_index_end,
                    self.start_time.isoformat() if self.start_time else None,
                    self.end_time.isoformat() if self.end_time else None,
                    self.total_time, self.session_wpm, self.session_cpm,
                    self.expected_chars, self.actual_chars, self.errors,
                    self.accuracy, self.session_id
                )
                return db.execute_update(query, params)

        except sqlite3.DatabaseError as e:
            print(f"Error saving practice session: {e}")
            return False

    @classmethod
    def get_session_info(cls, snippet_id: int) -> Dict[str, int]:
        """
        Get last session indices and snippet length for an integer snippet_id.
        Returns dict with last_start_index, last_end_index, snippet_length.
        """
        db = DatabaseManager.get_instance()

        last_end_index_row = db.execute_query(
            "SELECT snippet_index_end FROM practice_sessions WHERE snippet_id = ? ORDER BY end_time DESC LIMIT 1",
            (snippet_id,)
        )
        last_end_index = last_end_index_row[0]['snippet_index_end'] if last_end_index_row else 0
        last_start_index = last_end_index

        snippet_length_row = db.execute_query(
            """
            SELECT SUM(LENGTH(part_text)) AS total_length
            FROM snippet_parts
            WHERE snippet_id = ?
            """,
            (snippet_id,)
        )
        snippet_length = snippet_length_row[0]['total_length'] if snippet_length_row and snippet_length_row[0]['total_length'] is not None else 0

        return {
            "last_start_index": last_start_index,
            "last_end_index": last_end_index,
            "snippet_length": snippet_length
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PracticeSession':
        """Create a PracticeSession instance from a dictionary, ensuring integer IDs."""
        start_time = data.get('start_time')
        if start_time and isinstance(start_time, str):
            start_time = datetime.datetime.fromisoformat(start_time)

        end_time = data.get('end_time')
        if end_time and isinstance(end_time, str):
            end_time = datetime.datetime.fromisoformat(end_time)

        session_id = data.get('session_id')
        if session_id is not None and not isinstance(session_id, int):
            try:
                session_id = int(session_id)
            except (ValueError, TypeError):
                session_id = None

        snippet_id = data.get('snippet_id')
        if snippet_id is not None and not isinstance(snippet_id, int):
            try:
                snippet_id = int(snippet_id)
            except (ValueError, TypeError):
                snippet_id = None

        return cls(
            session_id=session_id,
            snippet_id=snippet_id,
            snippet_index_start=data.get('snippet_index_start'),
            snippet_index_end=data.get('snippet_index_end'),
            start_time=start_time,
            end_time=end_time,
            total_time=data.get('total_time'),
            session_wpm=data.get('session_wpm'),
            session_cpm=data.get('session_cpm'),
            expected_chars=data.get('expected_chars'),
            actual_chars=data.get('actual_chars'),
            errors=data.get('errors'),
            accuracy=data.get('accuracy')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the practice session to a dictionary with integer IDs."""
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
            'accuracy': self.accuracy
        }

    def start(self) -> bool:
        """Start a new practice session and save it to get an ID."""
        self.start_time = datetime.datetime.now()
        self.end_time = None
        self.total_time = None
        self.session_wpm = None
        self.session_cpm = None
        self.expected_chars = None
        self.actual_chars = None
        self.errors = None
        self.accuracy = None
        self.session_id = None
        return self.save()

    def end(self, stats: Dict[str, Any]) -> bool:
        """End a practice session, record the stats, and save."""
        self.end_time = datetime.datetime.now()
        if self.start_time and 'total_time' not in stats:
            duration = (self.end_time - self.start_time).total_seconds() * 1000
            self.total_time = int(duration)
        else:
            self.total_time = stats.get('total_time')

        self.session_wpm = stats.get('wpm')
        self.session_cpm = stats.get('cpm')
        self.expected_chars = stats.get('expected_chars')
        self.actual_chars = stats.get('actual_chars')
        self.errors = stats.get('errors')
        self.accuracy = stats.get('accuracy')

        if self.session_id is None:
            print("Error: Cannot end a session that hasn't been started or saved.")
            return False

        try:
            success = self.save()
            if not success:
                print(f"Failed to update session {self.session_id} in practice_sessions table.")
            return success
        except sqlite3.DatabaseError as e:
            print(f"Error ending session {self.session_id}: {e}")
            return False

    @classmethod
    def get_progress_data(cls, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get practice session data for progress tracking, optionally filtered by integer category_id.
        Ensures IDs in the result are integers.
        """
        db = DatabaseManager.get_instance()

        if category_id is None:
            query = (
                """
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time,
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id, tc.category_name, ts.snippet_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                ORDER BY ps.end_time DESC
                """
            )
            params = ()
        else:
            query = (
                """
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time,
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id, tc.category_name, ts.snippet_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                WHERE ts.category_id = ?
                ORDER BY ps.end_time DESC
                """
            )
            params = (category_id,)

        rows = db.execute_query(query, params)

        columns = [
            'session_id', 'start_time', 'end_time', 'total_time',
            'session_wpm', 'session_cpm', 'errors', 'accuracy',
            'category_id', 'category_name', 'snippet_name'
        ]

        result = []
        for row_dict in rows:
            session_data = dict(row_dict)

            for id_field in ['session_id', 'category_id']:
                if session_data.get(id_field) is not None and not isinstance(session_data[id_field], int):
                    try:
                        session_data[id_field] = int(session_data[id_field])
                    except (ValueError, TypeError):
                        session_data[id_field] = None

            for time_field in ['start_time', 'end_time']:
                if session_data[time_field] and isinstance(session_data[time_field], str):
                    try:
                        session_data[time_field] = datetime.datetime.fromisoformat(
                            session_data[time_field]
                        )
                    except ValueError:
                        pass

            result.append(session_data)

        return result

    @classmethod
    def delete_by_snippet_id(cls, snippet_id: int) -> bool:
        """
        Delete all practice sessions associated with a specific integer snippet_id.
        """
        db = DatabaseManager.get_instance()
        try:
            return db.execute_update(
                "DELETE FROM practice_sessions WHERE snippet_id = ?",
                (snippet_id,)
            )
        except sqlite3.DatabaseError as e:
            print(f"Error deleting practice sessions for snippet_id {snippet_id}: {e}")
            return False

    @classmethod
    def reset_session_data(cls) -> bool:
        """
        Clear all session data by dropping and recreating the tables with INTEGER IDs.
        """
        db = DatabaseManager.get_instance()
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute("DROP TABLE IF EXISTS practice_sessions")
            cursor.execute(
                """
                CREATE TABLE practice_sessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snippet_id INTEGER NOT NULL,
                    snippet_index_start INTEGER,
                    snippet_index_end INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    total_time INTEGER,
                    session_wpm REAL,
                    session_cpm REAL,
                    expected_chars INTEGER,
                    actual_chars INTEGER,
                    errors INTEGER,
                    accuracy REAL,
                    FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id) ON DELETE CASCADE
                )
                """
            )

            conn.commit()
            return True
        except sqlite3.DatabaseError as e:
            print(f"Error resetting session data: {e}")
            return False
