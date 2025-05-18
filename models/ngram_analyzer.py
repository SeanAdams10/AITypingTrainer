"""
N-Gram Analysis Module

This module provides functionality to analyze typing sessions and extract n-gram statistics,
including speed bottlenecks and error-prone character sequences. It follows object-oriented
principles and implements the functionality described in the ngram.md specification.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.practice_session import PracticeSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 10
# No whitespace allowed in n-grams
VALID_NGRAM_CHARS = re.compile(r'^[^\s]+$')


@dataclass
class NGram:
    """Data class to hold n-gram information."""
    
    text: str
    size: int
    keystrokes: List['Keystroke'] = field(default_factory=list)
    total_time_ms: float = 0.0
    
    # Error flags
    error_on_last: bool = False
    other_errors: bool = False
    accuracy: float = 100.0  # Default to 100% accuracy
    
    @property
    def is_clean(self) -> bool:
        """Determine if this n-gram is clean (no errors)."""
        return not (self.error_on_last or self.other_errors)
    
    @property
    def is_error(self) -> bool:
        """Determine if this n-gram has an error on the last keystroke only."""
        return self.error_on_last and not self.other_errors
    
    @property
    def is_valid(self) -> bool:
        """Determine if this n-gram is valid for tracking."""
        return self.is_clean or self.is_error
    
    @property
    def avg_time_per_char_ms(self) -> float:
        """
        Calculate the average time per character in milliseconds for this n-gram.
        
        Returns:
            float: Average time per character in milliseconds, or 0.0 if total_time_ms is 0
        """
        if self.total_time_ms <= 0 or self.size <= 0:
            return 0.0
        return self.total_time_ms / self.size


class NGramAnalyzer:
    """
    Analyzes n-grams in typing sessions to identify patterns and errors.
    
    This class processes keystroke data to extract n-gram statistics,
    including typing speed and error patterns. It supports analyzing
    n-grams of different sizes and provides methods to retrieve various
    statistics about the analyzed n-grams.
    
    Following OOP principles, it works with PracticeSession objects directly.
    """
    
    def __init__(self, practice_session: PracticeSession, keystrokes: List[Keystroke], db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the NGramAnalyzer with a practice session and keystrokes.
        
        Args:
            practice_session: The PracticeSession object to analyze
            keystrokes: List of Keystroke objects for this session
            db_manager: Optional DatabaseManager for database operations (creates one if None)
        """
        self.session = practice_session
        self.keystrokes = keystrokes
        self.db = db_manager or DatabaseManager()
        
        # Collections for analyzed n-grams
        self.speed_ngrams: Dict[int, Dict[str, NGram]] = {}  # For clean n-grams (no errors)
        self.error_ngrams: Dict[int, Dict[str, NGram]] = {}  # For n-grams with error on last character
        
        # Track if analysis has been performed
        self.analysis_complete = False
    
    def analyze(self, min_size: int = MIN_NGRAM_SIZE, max_size: int = MAX_NGRAM_SIZE) -> None:
        """
        Analyze the keystrokes and extract n-gram statistics.
        
        This method processes all keystrokes to identify valid n-grams,
        calculate timing information, and detect errors. It then separates
        the n-grams into clean and error categories based on error patterns.
        
        Args:
            min_size: Minimum n-gram size to analyze (inclusive)
            max_size: Maximum n-gram size to analyze (inclusive)
            
        Raises:
            ValueError: If min_size or max_size are invalid
        """
        if not self.keystrokes:
            logger.warning("No keystrokes to analyze")
            return
        
        # Validate input
        if min_size < MIN_NGRAM_SIZE or max_size > MAX_NGRAM_SIZE or min_size > max_size:
            raise ValueError(f"Invalid n-gram size range: must be between {MIN_NGRAM_SIZE} and {MAX_NGRAM_SIZE}")
        
        # Reset analysis state
        self.speed_ngrams = {}
        self.error_ngrams = {}
        
        # Process each n-gram size
        for size in range(min_size, max_size + 1):
            self._analyze_ngram_size(size)
        
        # Mark analysis as complete
        self.analysis_complete = True
    
    def _analyze_ngram_size(self, size: int) -> None:
        """
        Extract all n-grams of a specific size from the keystrokes.
        
        This method analyzes all sequences of 'size' consecutive keystrokes,
        creates NGram objects for each unique n-gram, and classifies them
        as clean or error n-grams based on error patterns.
        
        Args:
            size: Size of the n-grams to extract
        """
        if size < MIN_NGRAM_SIZE or size > MAX_NGRAM_SIZE:
            logger.warning("Invalid n-gram size: %s, must be between %s and %s", size, MIN_NGRAM_SIZE, MAX_NGRAM_SIZE)
            return
        
        if len(self.keystrokes) < size:
            logger.info("Not enough keystrokes (%s) to extract n-grams of size %s", len(self.keystrokes), size)
            return
        
        # Initialize dictionaries for this size if they don't exist
        self.speed_ngrams[size] = {}
        self.error_ngrams[size] = {}
        
        # Slide a window of 'size' over the keystrokes
        for i in range(len(self.keystrokes) - size + 1):
            # Get the keystrokes for this potential n-gram
            ngram_keystrokes = self.keystrokes[i:i+size]
            
            # Extract the text of the n-gram
            ngram_text = ''.join(ks.keystroke_char for ks in ngram_keystrokes)
            
            # Skip n-grams with whitespace
            if not VALID_NGRAM_CHARS.match(ngram_text):
                continue
            
            # Calculate timing (skip the first keystroke's time)
            total_time_ms = sum(
                (ks.time_since_previous or 0) 
                for ks in ngram_keystrokes[1:]
            )
            
            # Check for errors
            error_on_last = not ngram_keystrokes[-1].is_correct
            other_errors = any(not ks.is_correct for ks in ngram_keystrokes[:-1])
            
            # Create the n-gram object
            ngram = NGram(
                text=ngram_text,
                size=size,
                keystrokes=ngram_keystrokes.copy(),
                total_time_ms=total_time_ms,
                error_on_last=error_on_last,
                other_errors=other_errors
            )
            
            # Add to the appropriate dictionary based on error classification
            if ngram.is_clean:
                # For clean n-grams (no errors), add to speed analysis
                if ngram_text in self.speed_ngrams[size]:
                    existing_ngram = self.speed_ngrams[size][ngram_text]
                    existing_ngram.total_time_ms += total_time_ms
                    existing_ngram.keystrokes.extend(ngram_keystrokes)
                else:
                    self.speed_ngrams[size][ngram_text] = ngram
            elif ngram.is_error:
                # For n-grams with error only on last character, add to error analysis
                if ngram_text in self.error_ngrams[size]:
                    existing_ngram = self.error_ngrams[size][ngram_text]
                    existing_ngram.total_time_ms += total_time_ms
                    existing_ngram.keystrokes.extend(ngram_keystrokes)
                else:
                    self.error_ngrams[size][ngram_text] = ngram
    
    def save_to_database(self) -> bool:
        """
        Save the analyzed n-grams to the database.
        
        This method writes clean n-grams to the session_ngram_speed table
        and error n-grams to the session_ngram_errors table.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.analysis_complete:
            logger.warning("Cannot save to database before analysis is complete")
            return False
        
        try:
            # Ensure the required tables exist
            self._ensure_tables_exist()
            
            # Begin a transaction
            self.db.begin_transaction()
            
            # Save clean n-grams to session_ngram_speed table
            for size, ngrams in self.speed_ngrams.items():
                for text, ngram in ngrams.items():
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO session_ngram_speed 
                        (session_id, ngram_size, ngram, ngram_time_ms)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            self.session.session_id,
                            ngram.size,
                            ngram.text,
                            ngram.avg_time_per_char_ms
                        )
                    )
            
            # Save error n-grams to session_ngram_errors table
            for size, ngrams in self.error_ngrams.items():
                for text, ngram in ngrams.items():
                    self.db.execute(
                        """
                        INSERT OR REPLACE INTO session_ngram_errors 
                        (session_id, ngram_size, ngram)
                        VALUES (?, ?, ?)
                        """,
                        (
                            self.session.session_id,
                            ngram.size,
                            ngram.text
                        )
                    )
            
            # Commit the transaction
            self.db.commit_transaction()
            logger.info("Successfully saved n-gram analysis for session %s", self.session.session_id)
            return True
            
        except Exception as e:
            # Rollback in case of error
            self.db.rollback_transaction()
            logger.error("Error saving n-gram analysis: %s", e)
            return False
    
    def _ensure_tables_exist(self) -> None:
        """Ensure that the required n-gram tables exist in the database.
        
        Uses the DatabaseManager's init_tables method to initialize all tables,
        including the n-gram tables.
        """
        # Call the DatabaseManager's init_tables method
        self.db.init_tables()
    
    def get_slowest_ngrams(self, size: int, limit: int = 10) -> List[NGram]:
        """
        Get the slowest n-grams of a specific size.
        
        Args:
            size: Size of the n-grams to retrieve
            limit: Maximum number of results to return
            
        Returns:
            List of NGram objects sorted by speed (slowest first)
        """
        if not self.analysis_complete:
            logger.warning("Must call analyze() before getting slowest n-grams")
            return []
            
        if size not in self.speed_ngrams:
            return []
            
        # Get clean n-grams and sort by time per character (highest first)
        ngrams = list(self.speed_ngrams[size].values())
        return sorted(ngrams, key=lambda x: x.avg_time_per_char_ms, reverse=True)[:limit]
    
    def get_most_error_prone_ngrams(self, size: int, limit: int = 10) -> List[NGram]:
        """
        Get the most error-prone n-grams of a specific size.
        
        Args:
            size: Size of the n-grams to retrieve
            limit: Maximum number of results to return
            
        Returns:
            List of NGram objects sorted by occurrence count (highest first)
        """
        if not self.analysis_complete:
            logger.warning("Must call analyze() before getting error-prone n-grams")
            return []
            
        if size not in self.error_ngrams:
            return []
            
        # Get error n-grams and sort by keystrokes count (highest first)
        ngrams = list(self.error_ngrams[size].values())
        return sorted(ngrams, key=lambda x: len(x.keystrokes), reverse=True)[:limit]
    
    def generate_practice_snippet(self, size: int, error_based: bool = False, limit: int = 5) -> str:
        """
        Generate a practice snippet based on the analyzed n-grams.
        
        This method creates a practice snippet containing either the slowest
        or most error-prone n-grams, depending on the error_based flag.
        
        Args:
            size: Size of the n-grams to include in the snippet
            error_based: If True, use error-prone n-grams; otherwise use slow n-grams
            limit: Maximum number of n-grams to include
            
        Returns:
            str: A formatted practice snippet text
        """
        if not self.analysis_complete:
            logger.warning("Must call analyze() before generating practice snippets")
            return ""
        
        # Get the relevant n-grams
        if error_based:
            ngrams = self.get_most_error_prone_ngrams(size, limit)
            snippet_type = "error-prone"
        else:
            ngrams = self.get_slowest_ngrams(size, limit)
            snippet_type = "slow"
        
        if not ngrams:
            return f"No {snippet_type} {size}-grams found for practice."
        
        # Generate a suitable heading
        heading = f"Practice for {snippet_type} {size}-grams"
        snippet_text = [heading, "=" * len(heading), ""]
        
        # Add each n-gram to the snippet
        for i, ngram in enumerate(ngrams, 1):
            if error_based:
                statistics = f"(Error frequency: {len(ngram.keystrokes)} occurrences)"
            else:
                time_ms = ngram.avg_time_per_char_ms
                wpm = (60000 / (time_ms * 5)) if time_ms > 0 else 0  # 5 chars per word
                statistics = f"(Speed: {wpm:.1f} WPM)"
            
            snippet_text.append(f"{i}. N-gram: '{ngram.text}' {statistics}")
            
            # Try to find example words containing this n-gram
            examples = self._find_example_words(ngram.text)
            if examples:
                snippet_text.append(f"   Examples: {', '.join(examples)}")
            
            snippet_text.append("")
        
        # Add a practice section
        snippet_text.extend([
            "Practice these sequences multiple times:",
            "",
            " ".join(ngram.text for ngram in ngrams),
            "",
            "Focus on accuracy and gradually build speed."
        ])
        
        return "\n".join(snippet_text)
    
    def _find_example_words(self, ngram: str, limit: int = 3) -> List[str]:
        """
        Find example words containing the given n-gram.
        
        Args:
            ngram: The n-gram to search for
            limit: Maximum number of example words to return
            
        Returns:
            List of words containing the n-gram
        """
        try:
            rows = self.db.fetch_all(
                """
                SELECT word FROM words
                WHERE word LIKE ?
                ORDER BY frequency DESC
                LIMIT ?
                """,
                (f"%{ngram}%", limit)
            )
            return [row[0] for row in rows]
        except Exception as e:
            logger.warning("Error finding example words: %s", e)
            return []
    
    @classmethod
    def analyze_session(cls, session_id: str, db_manager: Optional[DatabaseManager] = None) -> 'NGramAnalyzer':
        """
        Factory method to create, analyze, and save an NGramAnalyzer for a specific session.
        
        This class method loads the session and keystrokes from the database,
        performs analysis, and saves the results back to the database.
        
        Args:
            session_id: The ID of the practice session to analyze
            db_manager: Optional DatabaseManager instance
            
        Returns:
            NGramAnalyzer: The analyzer instance with completed analysis
            
        Raises:
            ValueError: If the session or keystrokes cannot be loaded
        """
        db = db_manager or DatabaseManager()
        
        # Load the practice session
        from models.practice_session import PracticeSessionManager
        session_manager = PracticeSessionManager(db)
        session = session_manager.get_session_by_id(session_id)
        
        if not session:
            raise ValueError(f"Could not find practice session with ID: {session_id}")
        
        # Load keystrokes for the session
        keystrokes = cls._load_keystrokes_for_session(session_id, db)
        
        if not keystrokes:
            raise ValueError(f"No keystrokes found for session ID: {session_id}")
        
        # Create and analyze
        analyzer = cls(session, keystrokes, db)
        analyzer.analyze()
        analyzer.save_to_database()
        
        return analyzer
    
    @staticmethod
    def _load_keystrokes_for_session(session_id: str, db: DatabaseManager) -> List[Keystroke]:
        """
        Load keystrokes for a specific session from the database.
        
        Args:
            session_id: The ID of the session to load keystrokes for
            db: DatabaseManager instance
            
        Returns:
            List of Keystroke objects sorted by time
        """
        try:
            rows = db.fetch_all(
                """
                SELECT keystroke_id, keystroke_time, keystroke_char, expected_char,
                       is_correct, error_type, time_since_previous
                FROM session_keystrokes
                WHERE session_id = ?
                ORDER BY keystroke_time
                """,
                (session_id,)
            )
            
            # Convert rows to Keystroke objects
            keystrokes = []
            for row in rows:
                keystroke = Keystroke(
                    session_id=session_id,
                    keystroke_id=row[0],
                    keystroke_time=datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1],
                    keystroke_char=row[2],
                    expected_char=row[3],
                    is_correct=bool(row[4]),
                    error_type=row[5],
                    time_since_previous=row[6]
                )
                keystrokes.append(keystroke)
            
            return keystrokes
            
        except Exception as e:
            logger.error("Error loading keystrokes for session %s: %s", session_id, e)
            return []
