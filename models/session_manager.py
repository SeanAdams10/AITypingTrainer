import logging
from typing import List, Optional

from db.database_manager import DatabaseManager
from db.exceptions import (
    DBConnectionError,
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
)
from models.session import Session


class SessionManager:
    """
    Manages all database and aggregation operations for Session objects.
    Delegates all DB operations to DatabaseManager and handles only exceptions from exceptions.py.
    All session_id values are UUID strings.
    """
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_session(self, **kwargs) -> Session:
        """
        Factory method to create a new Session object with a new UUID if not provided.
        Usage: session = session_manager.create_session(snippet_id=..., ...)
        """
        return Session(**kwargs)

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        try:
            row = self.db_manager.execute(
                """
                SELECT session_id, snippet_id, snippet_index_start, snippet_index_end, content, 
                       start_time, end_time, actual_chars, errors
                FROM practice_sessions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            
            # Convert row to dict for Session.from_dict
            row_dict = dict(row)
            # Let Session.from_dict handle all parsing, including datetimes
            return Session.from_dict(row_dict)
        
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            print(f"Error retrieving session by id: {e}")
            logging.error(f"Error retrieving session by id: {e}")
            raise

    def list_sessions_for_snippet(self, snippet_id: int) -> List[Session]:
        try:
            rows = self.db_manager.execute(
                (
                    "SELECT session_id, snippet_id, snippet_index_start, "
                    "snippet_index_end, content, start_time, end_time, actual_chars, errors "
                    "FROM practice_sessions WHERE snippet_id = ?"
                ),
                (snippet_id,),
            ).fetchall()
            return [Session.from_dict(dict(row)) for row in rows]
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            print(f"Error listing sessions for snippet: {e}")
            logging.error(f"Error listing sessions for snippet: {e}")
            raise

    def delete_all(self) -> bool:
        """
        Delete all keystrokes and ngrams before deleting all sessions.
        Only deletes sessions if both keystroke and ngram deletions succeed.
        Returns True if all deletions succeed, False otherwise.
        """
        from models.keystroke_manager import KeystrokeManager
        from models.ngram_manager import NGramManager
        try:
            keystroke_manager = KeystrokeManager(self.db_manager)
            ngram_manager = NGramManager(self.db_manager)
            keystrokes_deleted = False
            ngrams_deleted = False
            # Try to delete all keystrokes
            if hasattr(keystroke_manager, "delete_all"):
                keystrokes_deleted = keystroke_manager.delete_all()
            elif hasattr(keystroke_manager, "delete_all_keystrokes"):
                keystrokes_deleted = keystroke_manager.delete_all_keystrokes()
            else:
                raise NotImplementedError(
                    "KeystrokeManager must have delete_all or delete_all_keystrokes method."
                )
            # Try to delete all ngrams
            ngrams_deleted = ngram_manager.delete_all_ngrams()
            if keystrokes_deleted and ngrams_deleted:
                self.db_manager.execute("DELETE FROM practice_sessions")
                return True
            else:
                logging.error(
                    f"Failed to delete all: keystrokes_deleted={keystrokes_deleted}, "
                    f"ngrams_deleted={ngrams_deleted}"
                )
                return False
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
            Exception,
        ) as e:
            print(f"Error deleting all sessions and related data: {e}")
            logging.error(f"Error deleting all sessions and related data: {e}")
            return False

    def save_session(self, session: Session) -> str:
        """
        Save a Session object to the database. If a session with the same session_id exists,
        update it; otherwise, insert a new record.
        Returns the session_id.
        """
        try:
            row = self.db_manager.execute(
                "SELECT 1 FROM practice_sessions WHERE session_id = ?",
                (session.session_id,),
            ).fetchone()
            if row:
                self._update_session(session)
            else:
                self._insert_session(session)
            return session.session_id
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            print(f"Error saving session: {e}")
            logging.error(f"Error saving session: {e}")
            raise

    def _insert_session(self, session: Session) -> None:
        """Insert a new session into the database."""
        self.db_manager.execute(
            """
            INSERT INTO practice_sessions (
                session_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, total_time, session_wpm, session_cpm, expected_chars, actual_chars, errors, efficiency, correctness, accuracy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.snippet_id,
                session.snippet_index_start,
                session.snippet_index_end,
                session.content,
                session.start_time.isoformat(),
                session.end_time.isoformat(),
                session.total_time,
                session.session_wpm,
                session.session_cpm,
                session.expected_chars,
                session.actual_chars,
                session.errors,
                session.efficiency,
                session.correctness,
                session.accuracy,
            ),
        )

    def _update_session(self, session: Session) -> None:
        """Update an existing session in the database."""
        self.db_manager.execute(
            """
            UPDATE practice_sessions SET
                snippet_id = ?,
                snippet_index_start = ?,
                snippet_index_end = ?,
                content = ?,
                start_time = ?,
                end_time = ?,
                total_time = ?,
                session_wpm = ?,
                session_cpm = ?,
                expected_chars = ?,
                actual_chars = ?,
                errors = ?,
                efficiency = ?,
                correctness = ?,
                accuracy = ?
            WHERE session_id = ?
            """,
            (
                session.snippet_id,
                session.snippet_index_start,
                session.snippet_index_end,
                session.content,
                session.start_time.isoformat(),
                session.end_time.isoformat(),
                session.total_time,
                session.session_wpm,
                session.session_cpm,
                session.expected_chars,
                session.actual_chars,
                session.errors,
                session.efficiency,
                session.correctness,
                session.accuracy,
                session.session_id,
            ),
        )
