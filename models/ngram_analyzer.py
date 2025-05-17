"""
N-Gram Analysis Module

This module provides functionality to analyze typing sessions and extract n-gram statistics,
including speed and error patterns, to help identify areas for improvement in typing skills.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from db.database_manager import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 10
VALID_NGRAM_CHARS = re.compile(r'^[^\s]+$')  # No whitespace allowed in n-grams


@dataclass
class NGramStats:
    """Data class to hold n-gram statistics."""
    ngram: str
    ngram_size: int
    total_time_ms: float = 0.0
    error_count: int = 0

    @property
    def is_error(self) -> bool:
        """Determine if this n-gram has any errors."""
        return self.error_count > 0


class NGramAnalyzer:
    """
    Analyzes typing sessions to extract n-gram statistics.
    
    This class processes keystroke data to identify patterns in typing speed and errors,
    focusing on n-grams (sequences of n characters) to help users improve their typing skills.
    
    For each n-gram size n:
    - Records n-grams in session_ngram_speed if there are no errors
    - Records n-grams in session_ngram_error if there is an error on the last keystroke ONLY
    - Skips n-grams with errors in any position except the last character
    """
    """
    Analyzes typing sessions to extract n-gram statistics.
    
    This class processes keystroke data to identify patterns in typing speed and errors,
    focusing on n-grams (sequences of n characters) to help users improve their typing skills.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the NGramAnalyzer with a database manager.
        
        Args:
            db_manager: An instance of DatabaseManager for database operations.
        """
        self.db = db_manager
        
    def analyze_session(self, session_id: str) -> Dict[str, Dict[str, NGramStats]]:
        """
        Analyze a typing session and update n-gram statistics.
        
        Args:
            session_id: The ID of the session to analyze.
            
        Returns:
            A dictionary mapping n-gram sizes to dictionaries of NGramStats objects.
        """
        try:
            # Get keystrokes for the session
            keystrokes = self._get_session_keystrokes(session_id)
            if not keystrokes:
                logger.warning("No keystrokes found for session %s", session_id)
                return {}
                
            # Process keystrokes to extract n-grams
            ngram_stats = self._process_keystrokes(keystrokes)
            
            # Save results to database
            self._save_ngram_stats(session_id, ngram_stats)
            
            return ngram_stats
            
        except Exception as e:
            logger.error("Error analyzing session %s: %s", session_id, str(e), exc_info=True)
            raise
    
    def _get_session_keystrokes(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve keystrokes for a session from the database.
        
        Args:
            session_id: The ID of the session to retrieve keystrokes for.
            
        Returns:
            List of keystroke records as dictionaries.
        """
        query = """
            SELECT 
                keystroke_char, 
                expected_char, 
                is_correct, 
                time_since_previous
            FROM session_keystrokes 
            WHERE session_id = ? 
            ORDER BY keystroke_id
        """
        rows = self.db.fetchall(query, (session_id,))
        # Convert SQLite Row objects to dictionaries
        return [dict(row) for row in rows] if rows else []
    
    def get_keystroke_value(self, keystroke: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Safely get a value from a keystroke dictionary or object.
        
        Args:
            keystroke: Keystroke data as dict or object
            key: The key/attribute to get
            default: Default value if key not found
            
        Returns:
            The value for the key or the default value
        """
        # Try dictionary access first
        if hasattr(keystroke, 'get') and callable(getattr(keystroke, 'get')):
            return keystroke.get(key, default)
        # Then try attribute access
        if hasattr(keystroke, key):
            return getattr(keystroke, key, default)
        # Fall back to dictionary access with __getitem__ if available
        if hasattr(keystroke, '__getitem__') and key in keystroke:
            return keystroke[key]
        return default

    def _process_keystrokes(
        self, 
        keystrokes: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, NGramStats]]:
        """
        Process keystrokes to extract n-gram statistics.
        
        For each n-gram size n:
        - If there are no errors in the n-gram, record it in session_ngram_speed
        - If there is an error on the last character ONLY, record it in session_ngram_error
        - Skip n-grams with errors in any position except the last character
        
        Args:
            keystrokes: List of keystroke records.
            
        Returns:
            Dictionary mapping n-gram sizes to dictionaries of NGramStats.
        """
        logger.info("Processing %d keystrokes for n-gram analysis", len(keystrokes))
        
        # Process keystrokes into a more usable format
        processed_keystrokes = []
        for ks in keystrokes:
            try:
                processed_keystrokes.append({
                    'char': self.get_keystroke_value(ks, 'keystroke_char', ''),
                    'expected': self.get_keystroke_value(ks, 'expected_char', ''),
                    'is_correct': bool(self.get_keystroke_value(ks, 'is_correct', False)),
                    'time': float(self.get_keystroke_value(ks, 'time_since_previous', 0.0))
                })
            except (KeyError, ValueError) as e:
                logger.warning("Skipping invalid keystroke: %s", str(e))
                continue
                
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Processed keystrokes: %s", processed_keystrokes)
        
        # Dictionary to store n-gram statistics by size
        ngram_stats: Dict[str, Dict[str, NGramStats]] = {}
        
        # Process n-grams of different sizes
        for n in range(MIN_NGRAM_SIZE, MAX_NGRAM_SIZE + 1):
            if len(processed_keystrokes) < n:
                logger.debug("Skipping n-gram size %d: not enough keystrokes", n)
                continue
                
            ngram_stats[str(n)] = {}
            
            # Slide window of size n across the keystrokes
            for i in range(len(processed_keystrokes) - n + 1):
                window = processed_keystrokes[i:i+n]
                
                # Extract n-gram characters and check for errors
                ngram = ''.join(ks['char'] for ks in window)
                has_error = any(not ks['is_correct'] for ks in window)
                
                # Calculate total time for the n-gram
                total_time = sum(ks['time'] for ks in window[1:])
                
                # Initialize n-gram stats if not exists
                if ngram not in ngram_stats[str(n)]:
                    ngram_stats[str(n)][ngram] = NGramStats(
                        ngram=ngram,
                        ngram_size=n,
                        total_time_ms=0.0,
                        error_count=0
                    )
                
                # Update the appropriate counter based on error status
                stats = ngram_stats[str(n)][ngram]
                if has_error:
                    stats.error_count += 1
                    logger.debug(
                        "Incremented error count for '%s' to %d", 
                        ngram, 
                        stats.error_count
                    )
                else:
                    stats.total_time_ms = total_time  # Store the actual time, not a sum
                    logger.debug(
                        "Set time for '%s' to %.2f ms",
                        ngram,
                        total_time
                    )
        
        # Filter out n-gram sizes with no data
        return {k: v for k, v in ngram_stats.items() if v}
    
    def _update_ngram_stats(
        self, 
        ngram_stats_dict: Dict[str, NGramStats],
        ngram: str,
        ngram_time: float,
        is_error: bool
    ) -> None:
        """
        Update n-gram statistics in the dictionary.
        
        Args:
            ngram_stats_dict: Dictionary of NGramStats objects for a specific n-gram size
            ngram: The n-gram text
            ngram_time: Time taken to type this n-gram in milliseconds
            is_error: Whether this is an error entry
        """
        if ngram not in ngram_stats_dict:
            ngram_stats_dict[ngram] = NGramStats(
                ngram=ngram,
                ngram_size=len(ngram),
                total_time_ms=ngram_time if not is_error else 0.0,
                error_count=1 if is_error else 0
            )
        else:
            stats = ngram_stats_dict[ngram]
            if not is_error:
                stats.total_time_ms = ngram_time  # Store the latest time, not a sum
            else:
                stats.error_count += 1
    
    def _save_ngram_stats(self, session_id: str, ngram_stats: Dict[str, Dict[str, NGramStats]]) -> None:
        """
        Save n-gram statistics to the database.
        
        Args:
            session_id: The session ID
            ngram_stats: Dictionary of n-gram statistics
            
        Raises:
            Exception: If there's an error saving the statistics
        """
        try:
            # Save speed and error statistics separately
            for ngram_size, stats_dict in ngram_stats.items():
                if int(ngram_size) > 1:  # Only process n-grams of size 2 or greater
                    # Separate speed and error stats
                    speed_stats = {
                        ngram: stats 
                        for ngram, stats in stats_dict.items() 
                        if not stats.is_error
                    }
                    error_stats = {
                        ngram: stats 
                        for ngram, stats in stats_dict.items() 
                        if stats.is_error
                    }
                    
                    # Save speed stats if any
                    if speed_stats:
                        self._save_ngram_speed(session_id, speed_stats)
                    
                    # Save error stats if any
                    if error_stats:
                        self._save_ngram_errors(session_id, error_stats)
            
            self.db.commit_transaction()
            
        except Exception as e:
            self.db.rollback_transaction()
            logger.error("Error saving n-gram stats: %s", str(e), exc_info=True)
            raise

    def _save_ngram_speed(self, session_id: str, stats_dict: Dict[str, NGramStats]) -> None:
        """
        Save n-gram speed statistics to the database.
        
        Args:
            session_id: The session ID
            stats_dict: Dictionary mapping n-grams to their statistics
        """
        for ngram, stats in stats_dict.items():
            query = """
                INSERT OR REPLACE INTO session_ngram_speed 
                (session_id, ngram_size, ngram, ngram_time_ms)
                VALUES (?, ?, ?, ?)
            """
            self.db.execute(
                query,
                (session_id, stats.ngram_size, ngram, stats.total_time_ms),
                commit=False
            )

    def _save_ngram_errors(self, session_id: str, stats_dict: Dict[str, NGramStats]) -> None:
        """
        Save n-gram error statistics to the database.
        
        Args:
            session_id: The session ID
            stats_dict: Dictionary mapping n-grams to their error statistics
        """
        for ngram, stats in stats_dict.items():
            if stats.error_count == 0:
                continue  # Skip n-grams with zero error count
                
            query = """
                INSERT OR REPLACE INTO session_ngram_errors 
                (session_id, ngram_size, ngram, error_count)
                VALUES (?, ?, ?, ?)
            """
            self.db.execute(
                query,
                (session_id, stats.ngram_size, ngram, stats.error_count),
                commit=False
            )

    def get_slowest_ngrams(
        self, 
        ngram_size: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the slowest n-grams across all sessions.
        
        Args:
            ngram_size: The size of n-grams to retrieve.
            limit: Maximum number of results to return.
            
        Returns:
            List of dictionaries containing n-gram and average time in milliseconds
            
        Raises:
            ValueError: If ngram_size is less than 2 or limit is less than 1
        """
        if ngram_size < 2:
            raise ValueError("ngram_size must be at least 2")
        if limit < 1:
            raise ValueError("limit must be at least 1")
            
        try:
            query = """
                SELECT ngram, AVG(ngram_time_ms) as avg_time
                FROM session_ngram_speed
                WHERE ngram_size = ?
                GROUP BY ngram
                ORDER BY avg_time DESC
                LIMIT ?
            """
            results = self.db.fetchall(query, (ngram_size, limit))
            return [{"ngram": row["ngram"], "avg_time_ms": row["avg_time"]} for row in results]
        except Exception as e:
            logger.error("Error retrieving slowest n-grams: %s", str(e))
            return []
    
    def get_most_error_prone_ngrams(
        self,
        ngram_size: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most error-prone n-grams across all sessions.
        
        Args:
            ngram_size: The size of n-grams to retrieve.
            limit: Maximum number of results to return.
            
        Returns:
            List of dictionaries containing n-gram and error count
            
        Raises:
            ValueError: If ngram_size is less than 2 or limit is less than 1
        """
        if ngram_size < 2:
            raise ValueError("ngram_size must be at least 2")
        if limit < 1:
            raise ValueError("limit must be at least 1")
            
        try:
            query = """
                SELECT ngram, error_count
                FROM session_ngram_errors
                WHERE ngram_size = ?
                ORDER BY error_count DESC
                LIMIT ?
            """
            results = self.db.fetchall(query, (ngram_size, limit))
            return [{"ngram": row["ngram"], "error_count": row["error_count"]} for row in results]
        except Exception as e:
            logger.error("Error retrieving most error-prone n-grams: %s", str(e))
            return []


def main() -> None:
    """Example usage of the NGramAnalyzer class."""
    try:
        # Initialize database and analyzer
        db = DatabaseManager("typing_data.db")
        analyzer = NGramAnalyzer(db)
        
        # Example session ID - in a real application, this would come from user input or config
        session_id = "example_session_id"
        
        # Analyze a session
        analyzer.analyze_session(session_id)
        
        # Get and display slowest bigrams
        slow_bigrams = analyzer.get_slowest_ngrams(ngram_size=2)
        print("Slowest bigrams:", slow_bigrams)
        
        # Get and display most error-prone trigrams
        error_trigrams = analyzer.get_most_error_prone_ngrams(ngram_size=3)
        print("Most error-prone trigrams:", error_trigrams)
        
    except Exception as e:
        logger.error("Error in example usage: %s", str(e), exc_info=True)
        raise

if __name__ == "__main__":
    main()
