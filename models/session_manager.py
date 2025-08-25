"""SessionManager for database access and aggregation logic.

Provides typed CRUD and query helpers for `Session` objects, delegates DB
calls to `DatabaseManager`, and follows project-wide debug/trace standards.
"""
# Consolidated SessionManager for all DB and aggregate logic
import datetime
import logging
import traceback
from typing import List, Mapping, Optional, Sequence, Union, cast

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
from helpers.debug_util import DebugUtil
from models.session import Session


class SessionManager:
    """Manages database and aggregation operations for `Session` objects.

    Delegates all DB operations to `DatabaseManager` and handles only
    exceptions from `db.exceptions`. All `session_id` values are UUID strings.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize manager with a `DatabaseManager` dependency."""
        self.db_manager = db_manager
        self.debug_util = DebugUtil()

    # --- Internal helpers -------------------------------------------------

    def _get(
        self,
        row: Union[Mapping[str, object], Sequence[object]],
        key: str,
        idx: int,
    ) -> object:
        """Return a field from a row that may be mapping-like or sequence-like."""
        if isinstance(row, Mapping):
            return row[key]
        # In the non-mapping case, treat as a sequence for positional access
        return row[idx]

    def _row_to_session(self, row: Union[Mapping[str, object], Sequence[object]]) -> Session:
        """Convert a DB row (mapping or sequence) into a `Session` instance."""
        start_val = self._get(row, "start_time", 7)
        end_val = self._get(row, "end_time", 8)
        start_dt = (
            start_val
            if isinstance(start_val, datetime.datetime)
            else datetime.datetime.fromisoformat(str(start_val))
        )
        end_dt = (
            end_val
            if isinstance(end_val, datetime.datetime)
            else datetime.datetime.fromisoformat(str(end_val))
        )
        # Local safe int converter to satisfy typing and handle common DB types
        def _to_int(v: object) -> int:
            # Handle ints and bools explicitly without calling int() on 'object'
            if isinstance(v, bool):
                return 1 if v else 0
            if isinstance(v, int):
                return v
            # Convert common textual/byte representations
            try:
                return int(str(v))
            except Exception as exc:  # pragma: no cover - defensive
                raise TypeError(f"Cannot convert value to int: {v!r}") from exc
        return Session(
            session_id=str(self._get(row, "session_id", 0)),
            snippet_id=str(self._get(row, "snippet_id", 1)),
            user_id=str(self._get(row, "user_id", 2)),
            keyboard_id=str(self._get(row, "keyboard_id", 3)),
            snippet_index_start=_to_int(self._get(row, "snippet_index_start", 4)),
            snippet_index_end=_to_int(self._get(row, "snippet_index_end", 5)),
            content=str(self._get(row, "content", 6)),
            start_time=start_dt,
            end_time=end_dt,
            actual_chars=_to_int(self._get(row, "actual_chars", 9)),
            errors=_to_int(self._get(row, "errors", 10)),
        )

    def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by its `session_id`. Returns None if not found."""
        try:
            row = self.db_manager.execute(
                """
                SELECT
                    session_id,
                    snippet_id,
                    user_id,
                    keyboard_id,
                    snippet_index_start,
                    snippet_index_end,
                    content,
                    start_time,
                    end_time,
                    actual_chars,
                    errors
                FROM practice_sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if not row:
                return None
            typed_row = cast(Union[Mapping[str, object], Sequence[object]], row)
            return self._row_to_session(typed_row)
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            traceback.print_exc()
            print(f"Error retrieving session by id: {e}")
            logging.error(f"Error retrieving session by id: {e}")
            self.debug_util.debugMessage(f"Error retrieving session by id: {e}")
            raise

    def list_sessions_for_snippet(self, snippet_id: str) -> List[Session]:
        """List sessions for a snippet, ordered by most recent end_time."""
        try:
            rows = self.db_manager.execute(
                (
                    """
                    SELECT
                        session_id,
                        snippet_id,
                        user_id,
                        keyboard_id,
                        snippet_index_start,
                        snippet_index_end,
                        content,
                        start_time,
                        end_time,
                        actual_chars,
                        errors
                    FROM practice_sessions
                    WHERE snippet_id = ?
                    ORDER BY end_time DESC
                    """
                ),
                (snippet_id,),
            ).fetchall()
            typed_rows = cast(
                Sequence[Union[Mapping[str, object], Sequence[object]]],
                rows,
            )
            return [self._row_to_session(r) for r in typed_rows]
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            traceback.print_exc()
            msg = f"Error listing sessions for snippet: {e}"
            logging.error(msg)
            self.debug_util.debugMessage(msg)
            raise

    def save_session(self, session: Session) -> str:
        """Save a Session to the database.

        If a session with the same `session_id` exists, update it; otherwise,
        insert a new record. Returns the `session_id`.
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
            traceback.print_exc()
            msg = f"Error saving session: {e}"
            logging.error(msg)
            self.debug_util.debugMessage(msg)
            raise

    def _insert_session(self, session: Session) -> None:
        """Insert a new session into the database."""
        self.db_manager.execute(
            """
            INSERT INTO practice_sessions (
                session_id,
                snippet_id,
                user_id,
                keyboard_id,
                snippet_index_start,
                snippet_index_end,
                content,
                start_time,
                end_time,
                actual_chars,
                errors,
                ms_per_keystroke
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
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
        """Delete a session by its session_id. Returns True if deleted, else False."""
        try:
            result = self.db_manager.execute(
                "DELETE FROM practice_sessions WHERE session_id = ?",
                (session_id,),
            )
            # Some cursor protocols may not expose rowcount in type hints.
            deleted = cast(int, getattr(result, "rowcount", 0))
            return deleted > 0
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
        """Delete all keystrokes and ngrams before deleting all sessions.

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
                traceback.print_exc()
                logging.error(f"Error deleting all ngrams: {e}")
                self.debug_util.debugMessage(f"Error deleting all ngrams: {e}")
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
            traceback.print_exc()
            print(f"Error deleting all sessions and related data: {e}")
            logging.error(f"Error deleting all sessions and related data: {e}")
            self.debug_util.debugMessage(f"Error deleting all sessions and related data: {e}")
            return False

    def get_latest_session_for_keyboard(self, keyboard_id: str) -> Optional[Session]:
        """Return the most recent session for the given keyboard across all snippets.

        Returns None if no sessions are found for this keyboard.
        """
        try:
            row = self.db_manager.fetchone(
                """
                SELECT
                    session_id,
                    snippet_id,
                    user_id,
                    keyboard_id,
                    snippet_index_start,
                    snippet_index_end,
                    content,
                    start_time,
                    end_time,
                    actual_chars,
                    errors
                FROM practice_sessions
                WHERE keyboard_id = ?
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (keyboard_id,),
            )
            
            if not row:
                return None
            typed_row = cast(Union[Mapping[str, object], Sequence[object]], row)
            return self._row_to_session(typed_row)
        except (
            DBConnectionError,
            ConstraintError,
            DatabaseError,
            DatabaseTypeError,
            ForeignKeyError,
            IntegrityError,
            SchemaError,
        ) as e:
            traceback.print_exc()
            print(f"Error retrieving latest session for keyboard: {e}")
            logging.error(f"Error retrieving latest session for keyboard: {e}")
            self.debug_util.debugMessage(f"Error retrieving latest session for keyboard: {e}")
            raise

    def get_next_position(self, snippet_id: str) -> int:
        """Return the next start index for a session on the given snippet.

        - If no previous sessions: returns 0
        - If last session ended at or beyond snippet length: returns 0
        - Otherwise: returns last session's snippet_index_end.
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
