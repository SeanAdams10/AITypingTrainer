"""
Keystroke model for tracking keystrokes during practice sessions.
"""

from typing import Dict, List, Any, Optional, Union
import datetime
from db.database_manager import DatabaseManager


class Keystroke:
    """
    Model class for tracking individual keystrokes in practice sessions.
    """

    def __init__(
        self,
        session_id: Optional[int] = None,
        keystroke_id: Optional[int] = None,
        keystroke_time: Optional[datetime.datetime] = None,
        keystroke_char: str = "",
        expected_char: str = "",
        is_correct: bool = False,
        time_since_previous: Optional[int] = None,
    ) -> None:
        """Initialize a Keystroke instance."""
        self.session_id: Optional[int] = session_id
        self.keystroke_id: Optional[int] = keystroke_id
        self.keystroke_time: datetime.datetime = (
            keystroke_time or datetime.datetime.now()
        )
        self.keystroke_char: str = keystroke_char
        self.expected_char: str = expected_char
        self.is_correct: bool = is_correct
        self.time_since_previous: Optional[int] = time_since_previous
        self.db: DatabaseManager = DatabaseManager.get_instance()

    def save(self) -> bool:
        """Save this keystroke to the practice_session_keystrokes table using integer IDs."""
        db = self.db if hasattr(self, "db") else DatabaseManager.get_instance()
        try:
            # Ensure session_id is an integer
            if self.session_id is None or not isinstance(self.session_id, int):
                print(
                    f"Error: Invalid or missing session_id ({self.session_id}) for keystroke save.",
                    file=sys.stderr,
                )
                return False

            # Determine keystroke_id if not set (ensure it's an integer)
            if self.keystroke_id is None:
                rows = db.execute_query(
                    "SELECT MAX(keystroke_id) as max_id FROM practice_session_keystrokes WHERE session_id = ?",
                    (self.session_id,),
                )
                max_id = (
                    rows[0]["max_id"] if rows and rows[0]["max_id"] is not None else -1
                )
                self.keystroke_id = max_id + 1
            elif not isinstance(self.keystroke_id, int):
                try:
                    self.keystroke_id = int(self.keystroke_id)
                except (ValueError, TypeError):
                    print(
                        f"Error: Invalid keystroke_id type ({type(self.keystroke_id)}) for keystroke save.",
                        file=sys.stderr,
                    )
                    return False

            success = db.execute_update(
                """
                INSERT INTO practice_session_keystrokes (
                    session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.session_id,
                    self.keystroke_id,
                    (
                        self.keystroke_time.isoformat()
                        if hasattr(self.keystroke_time, "isoformat")
                        else self.keystroke_time
                    ),
                    self.keystroke_char,
                    self.expected_char,
                    int(self.is_correct),
                    self.time_since_previous,
                ),
            )
            return success
        except Exception as e:
            import sys

            print(f"Error saving keystroke: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Keystroke":
        """Create a Keystroke instance from a dictionary, ensuring integer IDs."""
        # Handle datetime conversion
        keystroke_time = data.get("keystroke_time")
        if isinstance(keystroke_time, str):
            try:
                keystroke_time = datetime.datetime.fromisoformat(
                    keystroke_time.replace("Z", "+00:00")
                )
            except ValueError:
                keystroke_time = datetime.datetime.now()

        # Handle boolean conversion
        is_correct = data.get("is_correct")
        if isinstance(is_correct, str):
            is_correct = is_correct.lower() in ("true", "1", "t", "y", "yes")
        elif isinstance(is_correct, int):
            is_correct = bool(is_correct)
        if not isinstance(is_correct, bool):
            is_correct = bool(is_correct)

        # Ensure IDs are integers
        session_id = data.get("session_id")
        if session_id is not None and not isinstance(session_id, int):
            try:
                session_id = int(session_id)
            except (ValueError, TypeError):
                session_id = None

        keystroke_id = data.get("keystroke_id")
        if keystroke_id is not None and not isinstance(keystroke_id, int):
            try:
                keystroke_id = int(keystroke_id)
            except (ValueError, TypeError):
                keystroke_id = None

        return cls(
            session_id=session_id,
            keystroke_id=keystroke_id,
            keystroke_time=keystroke_time,
            keystroke_char=data.get("keystroke_char", ""),
            expected_char=data.get("expected_char", ""),
            is_correct=is_correct,
            time_since_previous=data.get("time_since_previous"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the keystroke to a dictionary with integer IDs."""
        return {
            "session_id": self.session_id,
            "keystroke_id": self.keystroke_id,
            "keystroke_time": (
                self.keystroke_time.isoformat() if self.keystroke_time else None
            ),
            "keystroke_char": self.keystroke_char,
            "expected_char": self.expected_char,
            "is_correct": self.is_correct,
            "time_since_previous": self.time_since_previous,
        }

    @classmethod
    def save_many(cls, session_id: int, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Save multiple keystrokes at once for an integer practice session ID.

        Args:
            session_id: The integer ID of the practice session
            keystrokes: A list of keystroke data dictionaries

        Returns:
            bool: True if successful, False otherwise
        """
        if not isinstance(session_id, int) or not keystrokes:
            print(
                f"Error: Invalid session_id ({session_id}) or empty keystrokes list in save_many.",
                file=sys.stderr,
            )
            return False

        db = DatabaseManager.get_instance()
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

            # Get max error_id for this session to ensure uniqueness
            cursor.execute(
                "SELECT MAX(error_id) FROM practice_session_errors WHERE session_id = ?",
                (session_id,),
            )
            max_error_id = cursor.fetchone()[0]
            error_count = (max_error_id + 1) if max_error_id is not None else 0

            # Get max keystroke_id for this session to ensure uniqueness if not provided
            cursor.execute(
                "SELECT MAX(keystroke_id) FROM practice_session_keystrokes WHERE session_id = ?",
                (session_id,),
            )
            max_keystroke_id = cursor.fetchone()[0]
            next_keystroke_id = (
                (max_keystroke_id + 1) if max_keystroke_id is not None else 0
            )

            keystroke_data_to_insert = []
            error_data_to_insert = []

            for k_data in keystrokes:
                # Ensure keystroke_id is an integer
                k_id = k_data.get("keystroke_id")
                if k_id is None:
                    k_id = next_keystroke_id
                    next_keystroke_id += 1
                elif not isinstance(k_id, int):
                    try:
                        k_id = int(k_id)
                    except (ValueError, TypeError):
                        print(
                            f"Warning: Skipping keystroke with invalid keystroke_id: {k_data.get('keystroke_id')}",
                            file=sys.stderr,
                        )
                        continue

                # Convert keystroke_time from ISO format to datetime if necessary
                k_time = k_data.get("keystroke_time")
                if isinstance(k_time, str):
                    try:
                        k_time = datetime.datetime.fromisoformat(
                            k_time.replace("Z", "+00:00")
                        )
                    except ValueError:
                        k_time = datetime.datetime.now()
                elif k_time is None:
                    k_time = datetime.datetime.now()

                # Determine if the keystroke is correct
                is_correct = k_data.get("is_correct", False)
                if isinstance(is_correct, str):
                    is_correct = is_correct.lower() in ("true", "1", "t", "y", "yes")
                elif isinstance(is_correct, int):
                    is_correct = bool(is_correct)
                if not isinstance(is_correct, bool):
                    is_correct = bool(is_correct)

                keystroke_data_to_insert.append(
                    (
                        session_id,
                        k_id,
                        k_time.isoformat(),
                        k_data.get("keystroke_char", ""),
                        k_data.get("expected_char", ""),
                        int(is_correct),
                        k_data.get("time_since_previous"),
                    )
                )

                if not is_correct:
                    error_data_to_insert.append(
                        (
                            session_id,
                            error_count,
                            k_id,
                            k_data.get("keystroke_char", ""),
                            k_data.get("expected_char", ""),
                        )
                    )
                    error_count += 1

            # Use executemany for potentially better performance
            if keystroke_data_to_insert:
                cursor.executemany(keystroke_query, keystroke_data_to_insert)
            if error_data_to_insert:
                cursor.executemany(error_query, error_data_to_insert)

            conn.commit()
            return True

        except Exception as e:
            print(f"Error saving keystrokes: {e}")
            conn.rollback()
            return False

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_for_session(cls, session_id: int) -> List["Keystroke"]:
        """Get all keystrokes for an integer practice session ID."""
        db = DatabaseManager.get_instance()
        query = """
            SELECT *
            FROM practice_session_keystrokes
            WHERE session_id = ?
            ORDER BY keystroke_id
        """
        results = db.execute_query(query, (session_id,))

        return [cls.from_dict(row) for row in results]

    @classmethod
    def get_errors_for_session(cls, session_id: int) -> List["Keystroke"]:
        """Get all error keystrokes for an integer practice session ID."""
        db = DatabaseManager.get_instance()
        query = """
            SELECT k.*
            FROM practice_session_keystrokes k
            JOIN practice_session_errors e ON k.session_id = e.session_id AND k.keystroke_id = e.keystroke_id
            WHERE k.session_id = ?
            ORDER BY k.keystroke_id
        """
        results = db.execute_query(query, (session_id,))

        return [cls.from_dict(row) for row in results]
