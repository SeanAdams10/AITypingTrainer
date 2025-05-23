"""
NGram Manager for analyzing n-gram statistics from typing sessions.

This module provides functionality to analyze n-gram statistics such as:
- Slowest n-grams by average speed
- Most error-prone n-grams
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class NGramStats:
    """Data class to hold n-gram statistics."""
    
    ngram: str
    ngram_size: int
    avg_speed: float  # in ms per character
    total_occurrences: int
    last_used: Optional[datetime]

class NGramManager:
    """
    Manages n-gram analysis operations.
    
    This class provides methods to analyze n-gram statistics from typing sessions,
    including finding the slowest n-grams and those with the most errors.
    """
    
    def __init__(self, db_manager: Any) -> None:
        """
        Initialize the NGramManager with a database manager.
        
        Args:
            db_manager: Instance of DatabaseManager for database operations
        """
        self.db = db_manager
    
    def slowest_n(self, 
                  n: int, 
                  ngram_sizes: Optional[List[int]] = None,
                  lookback_distance: int = 1000) -> List[NGramStats]:
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
            ngram_sizes = list(range(1, 11))  # Default to 1-10
            
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
                ngram,
                ngram_size,
                AVG(ngram_time_ms) as avg_time_ms,
                COUNT(*) as occurrences,
                MAX(s.start_time) as last_used
            FROM session_ngram_speed s
            JOIN recent_sessions rs ON s.session_id = rs.session_id
            JOIN practice_sessions ps ON s.session_id = ps.session_id
            WHERE ngram_size IN ({placeholders})
            GROUP BY ngram, ngram_size
            HAVING COUNT(*) >= 3  -- Require at least 3 occurrences
            ORDER BY avg_time_ms DESC
            LIMIT ?
        """
        
        params = [lookback_distance] + list(ngram_sizes) + [n]
        
        results = self.db.fetchall(query, tuple(params))
        
        return [
            NGramStats(
                ngram=row['ngram'],
                ngram_size=row['ngram_size'],
                avg_speed=1000 / row['avg_time_ms'] * len(row['ngram']) if row['avg_time_ms'] > 0 else 0,
                total_occurrences=row['occurrences'],
                last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None
            )
            for row in results
        ]
    
    def error_n(self, 
               n: int, 
               ngram_sizes: Optional[List[int]] = None,
               lookback_distance: int = 1000) -> List[NGramStats]:
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
            ngram_sizes = list(range(1, 11))  # Default to 1-10
            
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
                e.ngram,
                e.ngram_size,
                COUNT(*) as error_count,
                MAX(ps.start_time) as last_used
            FROM session_ngram_errors e
            JOIN recent_sessions rs ON e.session_id = rs.session_id
            JOIN practice_sessions ps ON e.session_id = ps.session_id
            WHERE e.ngram_size IN ({placeholders})
            GROUP BY e.ngram, e.ngram_size
            ORDER BY error_count DESC, e.ngram_size
            LIMIT ?
        """
        
        params = [lookback_distance] + list(ngram_sizes) + [n]
        
        results = self.db.fetchall(query, tuple(params))
        
        return [
            NGramStats(
                ngram=row['ngram'],
                ngram_size=row['ngram_size'],
                avg_speed=0,  # Not applicable for error count
                total_occurrences=row['error_count'],
                last_used=datetime.fromisoformat(row['last_used']) if row['last_used'] else None
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
            logger.info("Deleting all n-gram data from database")
            self.db.execute("DELETE FROM session_ngram_speed")
            self.db.execute("DELETE FROM session_ngram_errors")
            return True
        except sqlite3.Error as e:
            logger.error("Error deleting n-gram data: %s", str(e), exc_info=True)
            return False
