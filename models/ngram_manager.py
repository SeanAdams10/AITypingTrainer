"""
NGram Manager for analyzing n-gram statistics from typing sessions.

This module provides functionality to analyze n-gram statistics such as:
- Slowest n-grams by average speed
- Most error-prone n-grams
"""

import logging
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from db.database_manager import DatabaseManager

from .ngram import NGram

logger = logging.getLogger(__name__)

MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 10


@dataclass
class NGramStats:
    """Data class to hold n-gram statistics."""

    ngram_id: str
    ngram: str
    ngram_size: int
    avg_speed: float  # in ms per character
    total_occurrences: int
    last_used: Optional[datetime]


# Define Keystroke model here for now, can be moved to a shared models file
class Keystroke(BaseModel):
    char: str
    expected: str
    timestamp: datetime

    @property
    def is_error(self) -> bool:
        return self.char != self.expected


class NGramManager:
    """
    Manages n-gram analysis operations.

    This class provides methods to analyze n-gram statistics from typing sessions,
    including finding the slowest n-grams and those with the most errors.
    """

    def __init__(self, db_manager: Optional["DatabaseManager"]) -> None:
        """
        Initialize the NGramManager with a database manager.

        Args:
            db_manager: Instance of DatabaseManager for database operations
        """
        self.db = db_manager

    def slowest_n(
        self, n: int, ngram_sizes: Optional[List[int]] = None, lookback_distance: int = 1000
    ) -> List[NGramStats]:
        """
        Find the n slowest n-grams by average speed.

        Args:
            n: Number of n-grams to return
            ngram_sizes: List of n-gram sizes to include (default is 1-10)
            lookback_distance: Number of most recent sessions to consider

        Returns:
            List of NGramStats objects sorted by speed (slowest first)
        """
        if n <= 0:
            return []

        if ngram_sizes is None:
            ngram_sizes = list(range(MIN_NGRAM_SIZE, MAX_NGRAM_SIZE + 1))  # Default to 2-10

        if not ngram_sizes:
            return []

        # Build the query to get the slowest n-grams
        placeholders = ",".join(["?"] * len(ngram_sizes))
        query = f"""
            WITH recent_sessions AS (
                SELECT session_id 
                FROM practice_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            )
            SELECT 
                s.ngram_speed_id as ngram_id,
                ngram_text as ngram,
                ngram_size,
                AVG(ngram_time_ms) as avg_time_ms,
                COUNT(*) as occurrences,
                MAX(ps.start_time) as last_used
            FROM session_ngram_speed s
            JOIN recent_sessions rs ON s.session_id = rs.session_id
            JOIN practice_sessions ps ON s.session_id = ps.session_id
            WHERE ngram_size IN ({placeholders})
            GROUP BY ngram_text, ngram_size
            HAVING COUNT(*) >= 3  -- Require at least 3 occurrences
            ORDER BY avg_time_ms DESC
            LIMIT ?
        """

        params = [lookback_distance] + list(ngram_sizes) + [n]

        results = self.db.fetchall(query, tuple(params)) if self.db else []

        return [
            NGramStats(
                ngram_id=row["ngram_id"],
                ngram=row["ngram"],
                ngram_size=row["ngram_size"],
                avg_speed=1000 / row["avg_time_ms"] * len(row["ngram"])
                if row["avg_time_ms"] > 0
                else 0,
                total_occurrences=row["occurrences"],
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            )
            for row in results
        ]

    def error_n(
        self, n: int, ngram_sizes: Optional[List[int]] = None, lookback_distance: int = 1000
    ) -> List[NGramStats]:
        """
        Find the n most error-prone n-grams by error count.

        Args:
            n: Number of n-grams to return
            ngram_sizes: List of n-gram sizes to include (default is 1-10)
            lookback_distance: Number of most recent sessions to consider

        Returns:
            List of NGramStats objects sorted by error count (highest first)
        """
        if n <= 0:
            return []

        if ngram_sizes is None:
            ngram_sizes = list(range(MIN_NGRAM_SIZE, MAX_NGRAM_SIZE + 1))  # Default to 2-10

        if not ngram_sizes:
            return []

        # Build the query to get the most error-prone n-grams
        placeholders = ",".join(["?"] * len(ngram_sizes))
        query = f"""
            WITH recent_sessions AS (
                SELECT session_id 
                FROM practice_sessions 
                ORDER BY start_time DESC 
                LIMIT ?
            )
            SELECT 
                e.ngram_error_id as ngram_id,
                ngram_text as ngram,
                ngram_size,
                COUNT(*) as error_count,
                MAX(ps.start_time) as last_used
            FROM session_ngram_errors e
            JOIN recent_sessions rs ON e.session_id = rs.session_id
            JOIN practice_sessions ps ON e.session_id = ps.session_id
            WHERE e.ngram_size IN ({placeholders})
            GROUP BY ngram_text, ngram_size
            ORDER BY error_count DESC, e.ngram_size
            LIMIT ?
        """

        params = [lookback_distance] + list(ngram_sizes) + [n]

        results = self.db.fetchall(query, tuple(params)) if self.db else []

        return [
            NGramStats(
                ngram_id=row["ngram_id"],
                ngram=row["ngram"],
                ngram_size=row["ngram_size"],
                avg_speed=0,  # Not applicable for error count
                total_occurrences=row["error_count"],
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            )
            for row in results
        ]

    def delete_all_ngrams(self) -> bool:
        """
        Delete all n-gram data from the database.

        This will clear both the session_ngram_speed and session_ngram_errors tables.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.db is None:
                logger.warning("Cannot delete n-gram data - no database connection")
                return False

            logger.info("Deleting all n-gram data from database")
            self.db.execute("DELETE FROM session_ngram_speed")
            self.db.execute("DELETE FROM session_ngram_errors")
            return True
        except sqlite3.Error as e:
            logger.error("Error deleting n-gram data: %s", str(e), exc_info=True)
            return False

    def generate_ngrams_from_keystrokes(
        self, keystrokes: List[Keystroke], ngram_size: int
    ) -> List[NGram]:
        """
        Generates NGram objects from a list of keystrokes without saving to DB.
        Sets is_valid, is_error, and is_clean flags based on defined rules.
        N-gram text is now the expected chars, not the actual typed chars.
        """
        generated_ngrams: List[NGram] = []
        # Only allow n-grams of length 2-10 for in-memory analysis (for is_clean flag)
        if not keystrokes or len(keystrokes) < ngram_size or ngram_size < MIN_NGRAM_SIZE or ngram_size > MAX_NGRAM_SIZE:
            return generated_ngrams

        # Helper functions to handle different Keystroke field naming conventions
        def get_expected_char(k: object) -> str:
            """Get expected character, supporting both 'expected' and 'expected_char' fields."""
            return getattr(k, "expected", getattr(k, "expected_char", ""))

        def get_actual_char(k: object) -> str:
            """Get actual character, supporting both 'char' and 'keystroke_char' fields."""
            return getattr(k, "char", getattr(k, "keystroke_char", ""))

        def get_time(k: object) -> Optional[datetime]:
            """Get timestamp, supporting both 'timestamp' and 'keystroke_time' fields."""
            return getattr(k, "timestamp", getattr(k, "keystroke_time", None))

        for i in range(len(keystrokes) - ngram_size + 1):
            current_keystroke_sequence = keystrokes[i : i + ngram_size]
            # Filtering: skip n-grams containing any space or backspace in expected chars
            if any(
                get_expected_char(k) == " " or get_expected_char(k) == "\b"
                for k in current_keystroke_sequence
            ):
                continue

            start_time = get_time(current_keystroke_sequence[0])
            end_time = get_time(current_keystroke_sequence[-1])
            if start_time is None or end_time is None:
                continue
            total_time_ms = (end_time - start_time).total_seconds() * 1000.0
            # Filtering: skip n-grams with total_time_ms == 0 (for ngram_size > 1)
            if ngram_size > 1 and total_time_ms == 0.0:
                continue
            # Additional filtering: skip if any consecutive keystrokes have the same timestamp (zero duration for any part)
            has_zero_part = any(
                get_time(current_keystroke_sequence[j])
                == get_time(current_keystroke_sequence[j + 1])
                for j in range(len(current_keystroke_sequence) - 1)
            )
            if has_zero_part:
                continue

            errors_in_sequence = [
                get_actual_char(k) != get_expected_char(k) for k in current_keystroke_sequence
            ]
            err_not_at_end = any(errors_in_sequence[:-1])
            # Clean: all chars correct, no space/backspace, time>0
            is_clean_ngram = all(
                get_actual_char(k) == get_expected_char(k) for k in current_keystroke_sequence
            )
            # Error: only last char is error, all others correct, no space/backspace, time>0
            ngram_is_error_flag = (not any(errors_in_sequence[:-1])) and errors_in_sequence[-1]
            # Valid: not error in non-last, no space/backspace, time>0
            is_valid_ngram = not err_not_at_end

            # Set ngram text: always expected chars (per clarified spec)
            text = "".join(get_expected_char(k) for k in current_keystroke_sequence)

            ngram_instance = NGram(
                ngram_id=str(uuid.uuid4()),
                text=text,
                size=ngram_size,
                start_time=start_time,
                end_time=end_time,
                is_clean=is_clean_ngram,
                is_error=ngram_is_error_flag,
                is_valid=is_valid_ngram,
            )
            generated_ngrams.append(ngram_instance)
        return generated_ngrams

    def save_ngram(self, ngram: NGram, session_id: str) -> bool:
        """
        Save an NGram object to the appropriate database table based on its flags.

        Per specification in ngram.md:
        - Clean ngrams go to the session_ngram_speed table
        - Ngrams with error flag (error only in last position) go to the session_ngram_errors table
        - Only ngrams of size 2-10 are saved

        Args:
            ngram: The NGram object to save
            session_id: The session ID to associate with this NGram

        Returns:
            bool: True if the save operation was successful, False otherwise
        """
        if self.db is None:
            logger.warning("Cannot save NGram - no database connection")
            return False

        # Only save n-grams of size 2-10 as per specification
        if ngram.size < MIN_NGRAM_SIZE or ngram.size > MAX_NGRAM_SIZE:
            logger.debug(
                f"Skipping ngram '{ngram.text}' as size {ngram.size} is outside range {MIN_NGRAM_SIZE}-{MAX_NGRAM_SIZE}"
            )
            return True  # Not an error, just skipping

        try:
            # Calculate the ngram time in milliseconds
            ngram_time_ms = ngram.total_time_ms

            if ngram.is_clean:
                # Save to session_ngram_speed table (clean ngrams only)
                self.db.execute(
                    "INSERT INTO session_ngram_speed "
                    "(ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ngram.ngram_id, session_id, ngram.size, ngram.text, ngram_time_ms),
                )
            elif ngram.is_error:
                # Save to session_ngram_errors table (errors only in last position)
                self.db.execute(
                    "INSERT INTO session_ngram_errors "
                    "(ngram_error_id, session_id, ngram_size, ngram_text) "
                    "VALUES (?, ?, ?, ?)",
                    (ngram.ngram_id, session_id, ngram.size, ngram.text),
                )
            # Do not save n-grams that are neither clean nor error

            return True
        except sqlite3.Error as e:
            logger.error("Error saving NGram: %s", str(e), exc_info=True)
            return False
