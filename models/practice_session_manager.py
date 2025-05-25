#!/usr/bin/env python
"""
PracticeSessionManager class for managing practice sessions in the typing trainer application.
"""
import datetime
import logging
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from db.database_manager import DatabaseManager
from models.practice_session import PracticeSession


class PracticeSessionManager:
    """
    Manager for CRUD operations and session logic for PracticeSession.
    Handles all DB access and business logic for typing sessions.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize PracticeSessionManager with a DatabaseManager instance."""
        self.db_manager: DatabaseManager = db_manager

    def get_last_session_for_snippet(
        self, snippet_id: int
    ) -> Optional[PracticeSession]:
        """
        Fetch the most recent practice session for a given snippet.
        Returns a PracticeSession instance or None if not found.
        """
        row = self.db_manager.execute(
            """
            SELECT session_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, total_time, session_wpm, session_cpm, expected_chars, actual_chars, errors, efficiency, correctness, accuracy
            FROM practice_sessions
            WHERE snippet_id = ?
            ORDER BY end_time DESC LIMIT 1
            """,
            (snippet_id,),
        ).fetchone()
        if not row:
            return None
        return PracticeSession(
            session_id=row[0],
            snippet_id=row[1],
            snippet_index_start=row[2],
            snippet_index_end=row[3],
            content=row[4],
            start_time=datetime.datetime.fromisoformat(row[5]) if row[5] else None,
            end_time=datetime.datetime.fromisoformat(row[6]) if row[6] else None,
            total_time=row[7],
            session_wpm=row[8],
            session_cpm=row[9],
            expected_chars=row[10],
            actual_chars=row[11],
            errors=row[12],
            efficiency=row[13],
            correctness=row[14],
            accuracy=row[15],
        )

    def get_session_content(self, session_id: str) -> Optional[str]:
        """
        Get the content of a session by its ID.
        
        Args:
            session_id: The ID of the session to get content for
            
        Returns:
            The content of the session as a string, or None if not found
        """
        row = self.db_manager.execute(
            "SELECT content FROM practice_sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()
        
        return row[0] if row else None
        
    def get_session_by_id(self, session_id: str) -> Optional[PracticeSession]:
        """
        Retrieve a complete PracticeSession object by its session_id.
        
        Args:
            session_id: The ID of the session to retrieve
            
        Returns:
            A PracticeSession object if found, None otherwise
        """
        row = self.db_manager.execute(
            """
            SELECT session_id, snippet_id, snippet_index_start, snippet_index_end, content, 
                   start_time, end_time, total_time, session_wpm, session_cpm, 
                   expected_chars, actual_chars, errors, efficiency, correctness, accuracy
            FROM practice_sessions WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()
        
        if not row:
            return None
            
        return PracticeSession(
            session_id=row[0],
            snippet_id=row[1],
            snippet_index_start=row[2],
            snippet_index_end=row[3],
            content=row[4],
            start_time=datetime.datetime.fromisoformat(row[5]) if row[5] else None,
            end_time=datetime.datetime.fromisoformat(row[6]) if row[6] else None,
            total_time=row[7],
            session_wpm=row[8],
            session_cpm=row[9],
            expected_chars=row[10],
            actual_chars=row[11],
            errors=row[12],
            efficiency=row[13],
            correctness=row[14],
            accuracy=row[15],
        )

    def get_session_info(self, snippet_id: int) -> Dict[str, Any]:
        """
        Get last session indices and snippet length for a snippet_id.
        Returns dict with last_start_index, last_end_index, snippet_length.
        """
        # Get last session
        last_session = self.get_last_session_for_snippet(snippet_id)
        if last_session is not None:
            last_start_index = last_session.snippet_index_start
            last_end_index = last_session.snippet_index_end
        else:
            last_start_index = 0
            last_end_index = 0
        # Get snippet length from snippet_parts table (sum of all part lengths)
        row = self.db_manager.execute(
            "SELECT SUM(LENGTH(content)) FROM snippet_parts WHERE snippet_id = ?",
            (snippet_id,),
        ).fetchone()
        snippet_length = row[0] if row and row[0] is not None else 0
        return {
            "last_start_index": last_start_index,
            "last_end_index": last_end_index,
            "snippet_length": snippet_length,
        }



    
    def get_next_position(self, snippet_id: int) -> int:
        """
        Get the recommended starting position for the next practice session.
        
        This method determines where the next session should start based on the last session's end position.
        If the last session ended at or beyond the snippet's length, it wraps around to the beginning (position 0).
        If there's no previous session, it starts from the beginning (position 0).
        
        Args:
            snippet_id: ID of the snippet to check
            
        Returns:
            int: The recommended starting position for the next session
        """
        # Get session info which includes the last end index and snippet length
        session_info = self.get_session_info(snippet_id)
        snippet_length = session_info["snippet_length"]
        last_end_index = session_info["last_end_index"]
        
        # If there's no previous session or the last session reached the end, start from the beginning
        if last_end_index == 0 or last_end_index >= snippet_length:
            return 0
        
        # Otherwise, continue from where the last session ended
        return last_end_index

    def create_session(self, session: PracticeSession) -> str:
        """
        Create a new practice session in the database.
        
        Args:
            session: PracticeSession object with session details
            
        Returns:
            str: The session_id of the created session
            
        Raises:
            Exception: If there was an error creating the session
        """
        logging.debug('Entering create_session with session: %s', session)
        try:
            # Generate a unique UUID for the session_id if not provided
            session_id = str(uuid.uuid4()) if session.session_id is None else str(session.session_id)
            
            # Include session_id in the INSERT statement
            query = """
                INSERT INTO practice_sessions (
                    session_id, snippet_id, snippet_index_start, snippet_index_end, content,
                    start_time, end_time, total_time, session_wpm,
                    session_cpm, expected_chars, actual_chars, errors, efficiency, correctness, accuracy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
            params = (
                session_id,
                session.snippet_id,
                session.snippet_index_start,
                session.snippet_index_end,
                session.content,
                session.start_time.isoformat() if session.start_time else None,
                session.end_time.isoformat() if session.end_time else None,
                session.total_time,
                session.session_wpm,
                session.session_cpm,
                session.expected_chars,
                session.actual_chars,
                session.errors,
                session.efficiency,
                session.correctness,
                session.accuracy,
            )
            self.db_manager.execute(query, params)
            logging.debug('Session created with ID: %s', session_id)
        except Exception as e:
            logging.error('Exception in create_session: %s', e)
            raise
        logging.debug('Exiting create_session with session_id: %s', session_id)
        return session_id

    def list_sessions_for_snippet(self, snippet_id: int) -> List[PracticeSession]:
        """
        List all practice sessions for a given snippet.
        
        Args:
            snippet_id: ID of the snippet to list sessions for
            
        Returns:
            List[PracticeSession]: List of PracticeSession objects
        """
        rows = self.db_manager.execute(
            """
            SELECT session_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, total_time, session_wpm, session_cpm, expected_chars, actual_chars, errors, efficiency, correctness, accuracy
            FROM practice_sessions WHERE snippet_id = ? ORDER BY end_time DESC
            """,
            (snippet_id,),
        ).fetchall()
        return [
            PracticeSession(
                session_id=row[0],
                snippet_id=row[1],
                snippet_index_start=row[2],
                snippet_index_end=row[3],
                content=row[4],
                start_time=datetime.datetime.fromisoformat(row[5]) if row[5] else None,
                end_time=datetime.datetime.fromisoformat(row[6]) if row[6] else None,
                total_time=row[7],
                session_wpm=row[8],
                session_cpm=row[9],
                expected_chars=row[10],
                actual_chars=row[11],
                errors=row[12],
                # If efficiency or correctness are not in the database (old data), provide defaults
                efficiency=row[13] if row[13] is not None else 1.0,
                correctness=row[14] if row[14] is not None else 1.0,
                accuracy=row[15],
            )
            for row in rows
        ]

    def from_dict(self, data: Dict[str, Any]) -> PracticeSession:
        """Create a PracticeSession instance from a dictionary.
        
        Args:
            data: Dictionary containing session data
            
        Returns:
            PracticeSession: A new instance created from the dictionary data
        """
        # Handle datetime fields
        start_time = data.get("start_time")
        if start_time and isinstance(start_time, str):
            start_time = datetime.datetime.fromisoformat(start_time)

        end_time = data.get("end_time")
        if end_time and isinstance(end_time, str):
            end_time = datetime.datetime.fromisoformat(end_time)

        # Handle session_id (now a string UUID)
        session_id = data.get("session_id")
        
        # Handle snippet_id
        snippet_id = data.get("snippet_id")
        if snippet_id is not None and not isinstance(snippet_id, int):
            try:
                snippet_id = int(snippet_id)
            except (ValueError, TypeError):
                snippet_id = None

        # Set default values for metrics if they're not in the data
        efficiency = data.get("efficiency", 1.0)
        correctness = data.get("correctness", 1.0)
        
        # Default accuracy calculation: efficiency * correctness
        # Only use the provided accuracy if it exists, otherwise calculate it
        accuracy = data.get("accuracy")
        if accuracy is None and efficiency is not None and correctness is not None:
            accuracy = efficiency * correctness
        elif accuracy is None:
            accuracy = 1.0  # Default if we can't calculate
        
        # Use the PracticeSession class to create a new instance
        return PracticeSession(
            session_id=session_id,
            snippet_id=snippet_id,
            snippet_index_start=data.get("snippet_index_start"),
            snippet_index_end=data.get("snippet_index_end"),
            content=data.get("content", ""),
            start_time=start_time,
            end_time=end_time,
            total_time=data.get("total_time"),
            session_wpm=data.get("session_wpm"),
            session_cpm=data.get("session_cpm"),
            expected_chars=data.get("expected_chars"),
            actual_chars=data.get("actual_chars"),
            errors=data.get("errors"),
            efficiency=efficiency,
            correctness=correctness,
            accuracy=accuracy,
        )

    @classmethod
    def get_progress_data(
        cls, category_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get practice session data for progress tracking, optionally filtered by integer category_id.
        Ensures IDs in the result are integers.
        
        Args:
            category_id: Optional category ID to filter by
            
        Returns:
            List[Dict[str, Any]]: List of practice session data dictionaries
        """
        db = DatabaseManager.get_instance()

        if category_id is None:
            query = """
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time,
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id, tc.category_name, ts.snippet_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                ORDER BY ps.end_time DESC
                """
            params = ()
        else:
            query = """
                SELECT ps.session_id, ps.start_time, ps.end_time, ps.total_time,
                       ps.session_wpm, ps.session_cpm, ps.errors, ps.accuracy,
                       ts.category_id, tc.category_name, ts.snippet_name
                FROM practice_sessions ps
                JOIN text_snippets ts ON ps.snippet_id = ts.snippet_id
                JOIN text_category tc ON ts.category_id = tc.category_id
                WHERE ts.category_id = ?
                ORDER BY ps.end_time DESC
                """
            params = (category_id,)

        rows = db.execute_query(query, params)

        result = []
        for row_dict in rows:
            session_data = dict(row_dict)

            for id_field in ["session_id", "category_id"]:
                if session_data.get(id_field) is not None and not isinstance(
                    session_data[id_field], int
                ):
                    try:
                        session_data[id_field] = int(session_data[id_field])
                    except (ValueError, TypeError):
                        session_data[id_field] = None

            for time_field in ["start_time", "end_time"]:
                if session_data[time_field] and isinstance(
                    session_data[time_field], str
                ):
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
        
        Args:
            snippet_id: ID of the snippet to delete sessions for
            
        Returns:
            bool: True if successful, False otherwise
        """
        db = DatabaseManager.get_instance()
        try:
            return db.execute_update(
                "DELETE FROM practice_sessions WHERE snippet_id = ?", (snippet_id,)
            )
        except sqlite3.DatabaseError as e:
            print(f"Error deleting practice sessions for snippet_id {snippet_id}: {e}")
            return False

    def reset_session_data(self) -> bool:
        """
        Clear all session data by dropping and recreating the tables with INTEGER IDs.
        
        Returns:
            bool: True if successful, False otherwise
        """
        sql = "Delete from practice_sessions"
        try:
            self.db_manager.execute(sql)
            return True
        except sqlite3.DatabaseError as e:
            print(f"Error resetting session data: {e}")
            return False
            
    def clear_all_session_data(self) -> bool:
        """
        Clear all session data from all related tables.
        
        This removes all data from:
        - practice_sessions
        - session_keystrokes
        - session_ngram_speed
        - session_ngram_errors
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("Starting to clear all session data...")
            
            # Begin transaction for atomicity
            self.db_manager.begin_transaction()
            
            # Count records before deletion for verification
            sessions_count = self.db_manager.execute(
                "SELECT COUNT(*) FROM practice_sessions"
            ).fetchone()[0]
            print(f"Found {sessions_count} practice sessions to delete")
            
            # Delete n-grams using NGramManager
            from models.ngram_manager import NGramManager
            ngram_manager = NGramManager(self.db_manager)
            if not ngram_manager.delete_all_ngrams():
                print("Warning: Failed to delete all n-grams")
                self.db_manager.rollback_transaction()
                return False
            
            # Delete keystrokes using Keystroke class
            from models.keystroke import Keystroke
            if not Keystroke.delete_all_keystrokes(self.db_manager):
                print("Warning: Failed to delete all keystrokes")
                self.db_manager.rollback_transaction()
                return False
            
            # Finally delete from the parent table
            print("Deleting from practice_sessions table...")
            self.db_manager.execute("DELETE FROM practice_sessions")
            
            # Commit the transaction
            self.db_manager.commit_transaction()
            print("Successfully cleared all session data")
            return True
            
        except sqlite3.Error as e:
            # Rollback the transaction on error
            self.db_manager.rollback_transaction()
            print(f"Error clearing session data: {e}")
            return False
