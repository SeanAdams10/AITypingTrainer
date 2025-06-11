"""
NGramManager model for analyzing typing performance with n-grams of varying sizes.
"""

import sqlite3
from typing import Any, Dict, List, Optional

from db.database_manager import DatabaseManager
from models.keystroke_manager import KeystrokeManager
from models.ngram import NGram

MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 10


class NGramManager:
    """
    Model class for analyzing n-gram typing performance.
    Handles both speed and error analysis for n-grams of varying sizes (2-10).
    """

    SPEED_TABLE: str = "session_ngram_speed"
    ERROR_TABLE: str = "session_ngram_error"

    def __init__(self, n: int) -> None:
        """
        Initialize the n-gram analyzer for the specified size.
        Args:
            n (int): The n-gram size (2-10)
        Raises:
            ValueError: If n is not in the range 2-10.
        """
        if n < 2 or n > 10:
            raise ValueError(f"n must be between 2 and 10, got {n}")
        self.n: int = n
        self.db_manager: DatabaseManager = DatabaseManager.get_instance()
        self.n_gram_name: Optional[str] = {
            2: "Bigram",
            3: "Trigram",
            4: "4-gram",
            5: "5-gram",
            6: "6-gram",
            7: "7-gram",
            8: "8-gram",
            9: "9-gram",
            10: "10-gram",
        }.get(n)

    def analyze_ngrams(self, keystroke_manager: KeystrokeManager, session_id: str) -> List[NGram]:
        """
        Analyze keystrokes from the given KeystrokeManager for a session and return NGram objects.
        """
        keystrokes = keystroke_manager.get_keystrokes_for_session(session_id)
        ngrams: List[NGram] = []
        if len(keystrokes) < self.n:
            return ngrams
        for i in range(self.n - 1, len(keystrokes)):
            ngram_keystrokes = keystrokes[i - (self.n - 1) : i + 1]
            ngram_chars = [ks.expected_char for ks in ngram_keystrokes]
            ngram_text = "".join(ngram_chars)
            if any(char.isspace() for char in ngram_text):
                continue
            start_time = ngram_keystrokes[0].keystroke_time
            end_time = ngram_keystrokes[-1].keystroke_time
            all_correct = all(getattr(ks, "is_correct", True) for ks in ngram_keystrokes)
            is_clean = all_correct
            is_error = (
                not ngram_keystrokes[-1].is_correct
                if hasattr(ngram_keystrokes[-1], "is_correct")
                else False
            )
            is_valid = is_clean or is_error
            ngram = NGram(
                text=ngram_text,
                size=self.n,
                start_time=start_time,
                end_time=end_time,
                is_clean=is_clean,
                is_error=is_error,
                is_valid=is_valid,
            )
            ngrams.append(ngram)
        return ngrams

    def save_ngrams(self, session_id: str, ngrams: List[NGram]) -> None:
        """
        Persist analyzed n-grams to the database.
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        self._ensure_tables_exist(cursor)
        for ngram in ngrams:
            if ngram.is_clean:
                cursor.execute(
                    f"""
                    INSERT INTO {self.SPEED_TABLE} (session_id, ngram_size, ngram_text, ngram_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, ngram.size, ngram.text, ngram.total_time_ms),
                )
            elif ngram.is_error:
                cursor.execute(
                    f"""
                    INSERT INTO {self.ERROR_TABLE} (session_id, ngram_size, ngram_text, ngram_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, ngram.size, ngram.text, ngram.total_time_ms),
                )
        conn.commit()
        conn.close()

    def get_slow_ngrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the slowest n-grams from the database.
        Args:
            limit (int): Maximum number of n-grams to return
            min_occurrences (int): Minimum number of times an n-gram must occur
        Returns:
            List[Dict[str, Any]]: Each dict contains 'ngram_text', 'ngram_size',
                'avg_time', and 'count'
        """
        query = f"""
            SELECT 
                ngram_text, 
                COUNT(*) as occurrence_count,
                AVG(ngram_time) as avg_time
            FROM {self.SPEED_TABLE}
            WHERE ngram_size = ?
            GROUP BY ngram_text
            HAVING COUNT(*) >= ?
            ORDER BY avg_time DESC
            LIMIT ?
        """
        raw_results = self.db_manager.execute_query(query, (self.n, min_occurrences, limit))
        return [
            {
                "ngram_text": row["ngram_text"],
                "ngram_size": self.n,
                "avg_time": row["avg_time"],
                "count": row["occurrence_count"],
            }
            for row in raw_results
        ]

    def get_error_ngrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the most common error n-grams.
        Args:
            limit (int): Maximum number of n-grams to return
            min_occurrences (int): Minimum number of times an n-gram must occur
        Returns:
            List[Dict[str, Any]]: Each dict contains 'ngram_text', 'ngram_size', and 'count'
        """
        query = f"""
            SELECT 
                ngram_text, 
                COUNT(*) as occurrence_count
            FROM {self.ERROR_TABLE}
            WHERE ngram_size = ?
            GROUP BY ngram_text
            HAVING COUNT(*) >= ?
            ORDER BY occurrence_count DESC
            LIMIT ?
        """
        raw_results = self.db_manager.execute_query(query, (self.n, min_occurrences, limit))
        return [
            {
                "ngram_text": row["ngram_text"],
                "ngram_size": self.n,
                "count": row["occurrence_count"],
            }
            for row in raw_results
        ]

    def get_speed_results_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get speed n-gram results for a specific session.
        Args:
            session_id (str): The session ID
        Returns:
            List[Dict[str, Any]]: List of speed n-gram results
        """
        query = f"""
            SELECT ngram_text, ngram_time
            FROM {self.SPEED_TABLE}
            WHERE session_id = ? AND ngram_size = ?
            ORDER BY ngram_id
        """
        return self.db_manager.execute_query(query, (session_id, self.n))

    def get_error_results_for_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get error n-gram results for a specific session.
        Args:
            session_id (str): The session ID
        Returns:
            List[Dict[str, Any]]: List of error n-gram results
        """
        query = f"""
            SELECT ngram_text, ngram_time
            FROM {self.ERROR_TABLE}
            WHERE session_id = ? AND ngram_size = ?
            ORDER BY ngram_id
        """
        return self.db_manager.execute_query(query, (session_id, self.n))

    def _ensure_tables_exist(self, cursor: sqlite3.Cursor) -> None:
        """
        Ensure that the necessary database tables exist for this n-gram size.
        Args:
            cursor (sqlite3.Cursor): An active SQLite cursor
        """
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.SPEED_TABLE} (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.ERROR_TABLE} (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
            """
        )

    @staticmethod
    def create_all_tables() -> bool:
        """
        Create all necessary tables for all supported n-gram sizes (2-10).
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = DatabaseManager.get_instance().get_connection()
            cursor = conn.cursor()
            for n in range(2, 11):
                analyzer = NGramManager(n)
                analyzer._ensure_tables_exist(cursor)
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating n-gram tables: {e}")
            if "conn" in locals():
                conn.rollback()
                conn.close()
            return False
