# Consolidated SessionManager for all DB and aggregate logic
import datetime
import logging
from typing import List, Optional

from db.database_manager import DatabaseManager
from db.exceptions import (
    ConstraintError,
    DatabaseError,
    DatabaseTypeError,
    DBConnectionError,
    ForeignKeyError,
    IntegrityError,
    SchemaError,
)
from models.session import Session


class SessionManager:
    """
    Manages all database and aggregation operations for Session objects.
    Delegates all DB operations to DatabaseManager and handles only exceptions
    from exceptions.py.
    All session_id values are UUID strings.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        try:
            row = self.db_manager.execute(
                """
                SELECT session_id, snippet_id, user_id, keyboard_id, snippet_index_start, snippet_index_end,
                       content, start_time, end_time, actual_chars, errors
                FROM practice_sessions WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            return Session(
                session_id=str(row[0]),
                snippet_id=str(row[1]),
                user_id=str(row[2]),
                keyboard_id=str(row[3]),
                snippet_index_start=int(row[4]),
                snippet_index_end=int(row[5]),
                content=str(row[6]),
                start_time=row[7]
                if isinstance(row[7], datetime.datetime)
                else datetime.datetime.fromisoformat(row[7]),
                end_time=row[8]
                if isinstance(row[8], datetime.datetime)
                else datetime.datetime.fromisoformat(row[8]),
                actual_chars=int(row[9]),
                errors=int(row[10]),
            )
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

    def list_sessions_for_snippet(self, snippet_id: str) -> List[Session]:
        try:
            rows = self.db_manager.execute(
                (
                    "SELECT session_id, snippet_id, user_id, keyboard_id, snippet_index_start, "
                    "snippet_index_end, content, start_time, end_time, actual_chars, errors "
                    "FROM practice_sessions WHERE snippet_id = ? "
                    "ORDER BY end_time DESC"
                ),
                (snippet_id,),
            ).fetchall()
            return [
                Session(
                    session_id=str(row[0]),
                    snippet_id=str(row[1]),
                    user_id=str(row[2]),
                    keyboard_id=str(row[3]),
                    snippet_index_start=int(row[4]),
                    snippet_index_end=int(row[5]),
                    content=str(row[6]),
                    start_time=row[7]
                    if isinstance(row[7], datetime.datetime)
                    else datetime.datetime.fromisoformat(row[7]),
                    end_time=row[8]
                    if isinstance(row[8], datetime.datetime)
                    else datetime.datetime.fromisoformat(row[8]),
                    actual_chars=int(row[9]),
                    errors=int(row[10]),
                )
                for row in rows
            ]
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

    def save_session(self, session: Session) -> str:
        """
        Save a Session object to the database. If a session with the same
        session_id exists, update it; otherwise, insert a new record.
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
                session_id, snippet_id, user_id, keyboard_id, snippet_index_start, snippet_index_end,
                content, start_time, end_time, actual_chars, errors, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.snippet_id,
                session.user_id,
                session.keyboard_id,
                session.snippet_index_start,
                session.snippet_index_end,
                session.content,
                session.start_time.isoformat(),
                session.end_time.isoformat(),
                session.actual_chars,
                session.errors,
                # ms_per_keystroke now uses expected_chars
                session.ms_per_keystroke if session.ms_per_keystroke is not None else 0,
            ),
        )

    def _update_session(self, session: Session) -> None:
        """Update an existing session in the database."""
        self.db_manager.execute(
            """
            UPDATE practice_sessions SET
                snippet_id = ?,
                user_id = ?,
                keyboard_id = ?,
                snippet_index_start = ?,
                snippet_index_end = ?,
                content = ?,
                start_time = ?,
                end_time = ?,
                actual_chars = ?,
                errors = ?
            WHERE session_id = ?
            """,
            (
                session.snippet_id,
                session.user_id,
                session.keyboard_id,
                session.snippet_index_start,
                session.snippet_index_end,
                session.content,
                session.start_time.isoformat(),
                session.end_time.isoformat(),
                session.actual_chars,
                session.errors,
                session.session_id,
            ),
        )

    def delete_session_by_id(self, session_id: str) -> bool:
        """
        Delete a session by its session_id. Returns True if deleted, False if not found.
        """
        try:
            result = self.db_manager.execute(
                "DELETE FROM practice_sessions WHERE session_id = ?",
                (session_id,),
            )
            return result.rowcount > 0
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            print(f"Error deleting session by id: {e}")
            logging.error(f"Error deleting session by id: {e}")
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
            if hasattr(keystroke_manager, "delete_all_keystrokes"):
                keystrokes_deleted = keystroke_manager.delete_all_keystrokes()
            # Try to delete all ngrams
            try:
                ngram_manager.delete_all_ngrams()
                ngrams_deleted = True
            except Exception as e:
                logging.error(f"Error deleting all ngrams: {e}")
                ngrams_deleted = False
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

    def get_latest_session_for_keyboard(self, keyboard_id: str) -> Optional[Session]:
        """
        Returns the most recent session for the given keyboard_id across all snippets.
        Returns None if no sessions found for this keyboard.
        """
        try:
            row = self.db_manager.fetchone(
                """
                SELECT session_id, snippet_id, user_id, keyboard_id, snippet_index_start, 
                       snippet_index_end, content, start_time, end_time, actual_chars, errors
                FROM practice_sessions 
                WHERE keyboard_id = ? 
                ORDER BY start_time DESC 
                LIMIT 1
                """,
                (keyboard_id,),
            )
            
            if not row:
                return None
                
            return Session(
                session_id=str(row["session_id"]),
                snippet_id=str(row["snippet_id"]),
                user_id=str(row["user_id"]),
                keyboard_id=str(row["keyboard_id"]),
                snippet_index_start=int(row["snippet_index_start"]),
                snippet_index_end=int(row["snippet_index_end"]),
                content=str(row["content"]),
                start_time=row["start_time"]
                if isinstance(row["start_time"], datetime.datetime)
                else datetime.datetime.fromisoformat(row["start_time"]),
                end_time=row["end_time"]
                if isinstance(row["end_time"], datetime.datetime)
                else datetime.datetime.fromisoformat(row["end_time"]),
                actual_chars=int(row["actual_chars"]),
                errors=int(row["errors"]),
            )
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            print(f"Error retrieving latest session for keyboard: {e}")
            logging.error(f"Error retrieving latest session for keyboard: {e}")
            raise

    def get_next_position(self, snippet_id: str) -> int:
        """
        Returns the next start index for a session on the given snippet.
        - If no previous sessions: returns 0
        - If last session ended at or beyond snippet length: returns 0
        - Otherwise: returns last session's snippet_index_end
        """
        # Get all sessions for this snippet, most recent first
        sessions = self.list_sessions_for_snippet(snippet_id)
        if not sessions:
            return 0
        last_session = sessions[0]
        # Get the snippet content length
        from models.snippet_manager import SnippetManager

        snippet_manager = SnippetManager(self.db_manager)
        snippet = snippet_manager.get_snippet_by_id(str(snippet_id))
        snippet_length = len(snippet.content) if snippet and snippet.content else 0
        if last_session.snippet_index_end >= snippet_length:
            return 0
        return last_session.snippet_index_end
