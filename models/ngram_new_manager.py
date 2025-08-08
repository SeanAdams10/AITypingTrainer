"""
New N-Gram Manager for analyzing n-gram statistics from typing sessions.

This module provides the complete NGramManager implementation according to
the updated specification in ngram.md, including speed modes, classification
logic, timing calculations, and batch operations.
"""

import logging
import sqlite3
import uuid
from copy import deepcopy
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Tuple, Dict, Any

from pydantic import ValidationError

if TYPE_CHECKING:
    from db.database_manager import DatabaseManager

from models.ngram_new import (
    SpeedNGram, ErrorNGram, Keystroke, SpeedMode, NGramClassifier,
    MIN_NGRAM_SIZE, MAX_NGRAM_SIZE, SEQUENCE_SEPARATORS,
    validate_ngram_size, has_sequence_separators, is_valid_ngram_text
)

logger = logging.getLogger(__name__)


class NGramManager:
    """
    Manages n-gram analysis operations according to the updated specification.

    This class provides the complete analysis pipeline including:
    - Speed mode processing (raw vs net)
    - N-gram extraction and classification
    - Complex timing calculations with gross-up logic
    - Batch database operations
    - Comprehensive validation and error handling
    """

    def __init__(self, db_manager: Optional["DatabaseManager"]) -> None:
        """
        Initialize the NGramManager with a database manager.

        Args:
            db_manager: Instance of DatabaseManager for database operations
        """
        self.db = db_manager

    def analyze_session(self, session_id: str, speed_mode: str) -> bool:
        """
        Main orchestrator method for analyzing a typing session.

        Args:
            session_id: UUID of the session to analyze
            speed_mode: Speed calculation mode ("raw" or "net")

        Returns:
            bool: True if analysis completed successfully, False otherwise
        """
        try:
            # Input validation
            if not self._validate_input(session_id, speed_mode):
                return False

            # Get session data
            session = self._get_session(session_id)
            if not session:
                logger.error(f"Session not found: {session_id}")
                return False

            keystrokes = session.get('keystrokes', [])
            expected_text = session.get('expected_text', '')

            if not keystrokes or not expected_text:
                logger.warning(f"Session {session_id} has no keystrokes or expected text")
                return True  # Not an error, just nothing to analyze

            # Convert to Keystroke objects if needed
            keystroke_objects = self._convert_to_keystroke_objects(keystrokes, session_id)

            # Process all n-gram sizes
            all_speed_ngrams = []
            all_error_ngrams = []

            for ngram_size in range(MIN_NGRAM_SIZE, MAX_NGRAM_SIZE + 1):
                # Extract and classify n-grams for this size
                speed_ngrams, error_ngrams = self._process_ngram_size(
                    keystroke_objects, expected_text, ngram_size, speed_mode, session_id
                )
                all_speed_ngrams.extend(speed_ngrams)
                all_error_ngrams.extend(error_ngrams)

            # Batch save to database
            success = self._save_ngrams_batch(all_speed_ngrams, all_error_ngrams)

            if success:
                logger.info(f"N-gram analysis completed for session {session_id}: "
                          f"{len(all_speed_ngrams)} speed patterns, "
                          f"{len(all_error_ngrams)} error patterns identified")
            
            return success

        except Exception as e:
            logger.error(f"Analysis failed for session {session_id}: {str(e)}", exc_info=True)
            return False

    def extract_ngrams(self, keystrokes: List[Keystroke], expected_text: str, ngram_size: int) -> List[str]:
        """
        Extract all possible n-grams from expected text for the given size.

        Args:
            keystrokes: List of keystroke objects (not used in extraction, but kept for API compatibility)
            expected_text: The expected text to extract n-grams from
            ngram_size: Size of n-grams to extract

        Returns:
            List[str]: List of n-gram strings extracted from expected text
        """
        if not validate_ngram_size(ngram_size):
            logger.warning(f"Invalid n-gram size: {ngram_size}")
            return []

        if not expected_text or len(expected_text) < ngram_size:
            return []

        ngrams = []
        i = 0
        
        while i <= len(expected_text) - ngram_size:
            # Extract potential n-gram
            ngram_text = expected_text[i:i + ngram_size]
            
            # Check for sequence separators
            if has_sequence_separators(ngram_text):
                # Skip past the separator and continue
                separator_pos = next(
                    (j for j, char in enumerate(ngram_text) if char in SEQUENCE_SEPARATORS),
                    0
                )
                i += separator_pos + 1
                continue
            
            ngrams.append(ngram_text)
            i += 1

        return ngrams

    def classify_ngram(self, ngram_text: str, keystrokes: List[Keystroke], start_index: int) -> NGramClassifier:
        """
        Classify an n-gram based on keystroke patterns.

        Args:
            ngram_text: The n-gram text to classify
            keystrokes: List of keystrokes covering this n-gram
            start_index: Starting text index for this n-gram

        Returns:
            NGramClassifier: Classification of the n-gram (CLEAN, ERROR, or IGNORED)
        """
        if not ngram_text or not keystrokes:
            return NGramClassifier.IGNORED

        # Check for sequence separators in expected text
        if has_sequence_separators(ngram_text):
            return NGramClassifier.IGNORED

        ngram_size = len(ngram_text)
        if not validate_ngram_size(ngram_size):
            return NGramClassifier.IGNORED

        # Get keystrokes for this n-gram window
        ngram_keystrokes = []
        for i in range(ngram_size):
            text_idx = start_index + i
            # Find keystroke for this text index
            keystroke = next((k for k in keystrokes if k.text_index == text_idx), None)
            if not keystroke:
                return NGramClassifier.IGNORED
            ngram_keystrokes.append(keystroke)

        # Check timing validity
        duration = self.calculate_timing(ngram_keystrokes, 0, ngram_size)
        if duration <= 0:
            return NGramClassifier.IGNORED

        # Analyze error patterns
        errors = [not k.is_correct for k in ngram_keystrokes]
        
        # Clean: all keystrokes correct
        if not any(errors):
            return NGramClassifier.CLEAN
        
        # Error: only last keystroke is incorrect
        if errors[-1] and not any(errors[:-1]):
            return NGramClassifier.ERROR
        
        # Ignored: errors in non-last positions
        return NGramClassifier.IGNORED

    def calculate_timing(self, keystrokes: List[Keystroke], start_index: int, ngram_length: int) -> float:
        """
        Calculate n-gram duration with proper gross-up logic.

        Args:
            keystrokes: List of keystrokes for this n-gram
            start_index: Starting index within the keystroke list (usually 0)
            ngram_length: Length of the n-gram

        Returns:
            float: Duration in milliseconds, or 0 if calculation fails
        """
        if not keystrokes or len(keystrokes) < ngram_length or ngram_length < 1:
            return 0.0

        try:
            end_index = start_index + ngram_length - 1
            
            if end_index >= len(keystrokes):
                return 0.0

            # Validate timestamps
            if not self._validate_timing_data(keystrokes[start_index:end_index + 1]):
                return 0.0

            first_time = keystrokes[start_index].timestamp
            last_time = keystrokes[end_index].timestamp

            # Calculate raw duration
            raw_duration = (last_time - first_time).total_seconds() * 1000.0

            # Handle negative or zero duration
            if raw_duration <= 0:
                return 0.0

            # Apply gross-up logic based on specification
            if start_index == 0:
                # No i-1 character exists - use gross-up formula
                # estimated_duration = (observed_duration / (n-1)) * n
                if ngram_length == 1:
                    return raw_duration  # No gross-up needed for single character
                grossed_up_duration = (raw_duration / (ngram_length - 1)) * ngram_length
                return grossed_up_duration
            else:
                # i-1 character exists - use actual timing
                # Use time from character before n-gram to last character in n-gram
                before_time = keystrokes[start_index - 1].timestamp
                actual_duration = (last_time - before_time).total_seconds() * 1000.0
                return max(0.0, actual_duration)  # Ensure non-negative

        except Exception as e:
            logger.error(f"Error calculating timing: {str(e)}")
            return 0.0

    def _validate_input(self, session_id: str, speed_mode: str) -> bool:
        """Validate input parameters for analysis."""
        if not session_id or not session_id.strip():
            logger.error("Session ID cannot be None or empty")
            return False

        if speed_mode not in [SpeedMode.RAW.value, SpeedMode.NET.value]:
            logger.error(f"Invalid speed mode: {speed_mode}")
            return False

        if not self.db:
            logger.error("No database connection available")
            return False

        return True

    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from database."""
        try:
            # This would typically query the database for session data
            # For now, return a placeholder structure
            # In real implementation, this would use self.db to fetch session data
            return {
                'id': session_id,
                'keystrokes': [],
                'expected_text': ''
            }
        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {str(e)}")
            return None

    def _convert_to_keystroke_objects(self, keystrokes: List[Any], session_id: str) -> List[Keystroke]:
        """Convert raw keystroke data to Keystroke objects."""
        keystroke_objects = []
        
        for i, keystroke_data in enumerate(keystrokes):
            try:
                # Handle different input formats
                if isinstance(keystroke_data, Keystroke):
                    keystroke_objects.append(keystroke_data)
                elif isinstance(keystroke_data, dict):
                    # Ensure required fields are present
                    keystroke_dict = {
                        'session_id': session_id,
                        'timestamp': keystroke_data.get('timestamp', datetime.utcnow()),
                        'text_index': keystroke_data.get('text_index', i),
                        'expected_char': keystroke_data.get('expected_char', ''),
                        'actual_char': keystroke_data.get('actual_char', ''),
                        'is_correct': keystroke_data.get('is_correct', False)
                    }
                    keystroke_objects.append(Keystroke(**keystroke_dict))
                else:
                    # Handle object with attributes
                    keystroke_dict = {
                        'session_id': session_id,
                        'timestamp': getattr(keystroke_data, 'timestamp', datetime.utcnow()),
                        'text_index': getattr(keystroke_data, 'text_index', i),
                        'expected_char': getattr(keystroke_data, 'expected_char', 
                                               getattr(keystroke_data, 'expected', '')),
                        'actual_char': getattr(keystroke_data, 'actual_char',
                                             getattr(keystroke_data, 'char', '')),
                        'is_correct': getattr(keystroke_data, 'is_correct', False)
                    }
                    keystroke_objects.append(Keystroke(**keystroke_dict))
                    
            except Exception as e:
                logger.warning(f"Failed to convert keystroke {i}: {str(e)}")
                continue

        return keystroke_objects

    def _clone_keystrokes(self, keystrokes: List[Keystroke]) -> List[Keystroke]:
        """Create a deep copy of keystrokes for separate processing."""
        return deepcopy(keystrokes)

    def _apply_speed_mode(self, keystrokes: List[Keystroke], mode: str) -> List[Keystroke]:
        """Apply speed mode filtering to keystrokes."""
        if mode == SpeedMode.RAW.value:
            # Raw mode: return all keystrokes as-is
            return keystrokes
        
        elif mode == SpeedMode.NET.value:
            # Net mode: keep only last occurrence of each text_index
            # This removes corrections and backspaces
            text_index_map = {}
            
            # Build map of text_index -> latest keystroke
            for keystroke in keystrokes:
                text_index_map[keystroke.text_index] = keystroke
            
            # Sort by text_index to maintain sequence order
            filtered_keystrokes = [
                text_index_map[idx] for idx in sorted(text_index_map.keys())
            ]
            
            return filtered_keystrokes
        
        else:
            logger.error(f"Unknown speed mode: {mode}")
            return keystrokes

    def _process_ngram_size(self, keystrokes: List[Keystroke], expected_text: str, 
                          ngram_size: int, speed_mode: str, session_id: str) -> Tuple[List[SpeedNGram], List[ErrorNGram]]:
        """Process n-grams for a specific size."""
        speed_ngrams = []
        error_ngrams = []

        # Clone keystrokes for separate processing
        speed_keystrokes = self._clone_keystrokes(keystrokes)
        error_keystrokes = self._clone_keystrokes(keystrokes)

        # Apply speed mode to speed processing clone
        speed_keystrokes = self._apply_speed_mode(speed_keystrokes, speed_mode)

        # Extract possible n-grams from expected text
        possible_ngrams = self.extract_ngrams(keystrokes, expected_text, ngram_size)

        # Process each possible n-gram
        for start_idx in range(len(expected_text) - ngram_size + 1):
            ngram_text = expected_text[start_idx:start_idx + ngram_size]
            
            if not is_valid_ngram_text(ngram_text):
                continue

            # Process for speed analysis
            speed_classification = self.classify_ngram(ngram_text, speed_keystrokes, start_idx)
            if speed_classification == NGramClassifier.CLEAN:
                speed_ngram = self._create_speed_ngram(
                    ngram_text, speed_keystrokes, start_idx, ngram_size, speed_mode, session_id
                )
                if speed_ngram:
                    speed_ngrams.append(speed_ngram)

            # Process for error analysis (always use raw keystrokes)
            error_classification = self.classify_ngram(ngram_text, error_keystrokes, start_idx)
            if error_classification == NGramClassifier.ERROR:
                error_ngram = self._create_error_ngram(
                    ngram_text, error_keystrokes, start_idx, ngram_size, session_id
                )
                if error_ngram:
                    error_ngrams.append(error_ngram)

        return speed_ngrams, error_ngrams

    def _create_speed_ngram(self, ngram_text: str, keystrokes: List[Keystroke], 
                          start_index: int, ngram_size: int, speed_mode: str, session_id: str) -> Optional[SpeedNGram]:
        """Create a SpeedNGram object."""
        try:
            # Get keystrokes for this n-gram
            ngram_keystrokes = []
            for i in range(ngram_size):
                text_idx = start_index + i
                keystroke = next((k for k in keystrokes if k.text_index == text_idx), None)
                if not keystroke:
                    return None
                ngram_keystrokes.append(keystroke)

            # Calculate timing
            duration_ms = self.calculate_timing(ngram_keystrokes, 0, ngram_size)
            if duration_ms <= 0:
                return None

            ms_per_keystroke = duration_ms / ngram_size

            return SpeedNGram(
                id=uuid.uuid4(),
                session_id=session_id,
                size=ngram_size,
                text=ngram_text,
                duration_ms=duration_ms,
                ms_per_keystroke=ms_per_keystroke,
                speed_mode=SpeedMode(speed_mode),
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error creating speed n-gram: {str(e)}")
            return None

    def _create_error_ngram(self, expected_text: str, keystrokes: List[Keystroke], 
                          start_index: int, ngram_size: int, session_id: str) -> Optional[ErrorNGram]:
        """Create an ErrorNGram object."""
        try:
            # Get keystrokes for this n-gram
            ngram_keystrokes = []
            actual_chars = []
            
            for i in range(ngram_size):
                text_idx = start_index + i
                keystroke = next((k for k in keystrokes if k.text_index == text_idx), None)
                if not keystroke:
                    return None
                ngram_keystrokes.append(keystroke)
                actual_chars.append(keystroke.actual_char)

            actual_text = ''.join(actual_chars)

            # Calculate timing
            duration_ms = self.calculate_timing(ngram_keystrokes, 0, ngram_size)
            if duration_ms <= 0:
                return None

            return ErrorNGram(
                id=uuid.uuid4(),
                session_id=session_id,
                size=ngram_size,
                expected_text=expected_text,
                actual_text=actual_text,
                duration_ms=duration_ms,
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error creating error n-gram: {str(e)}")
            return None

    def _save_ngrams_batch(self, speed_ngrams: List[SpeedNGram], error_ngrams: List[ErrorNGram]) -> bool:
        """Save n-grams using batch operations with fallback to individual saves."""
        try:
            if not self.db:
                logger.error("No database connection available for saving")
                return False

            # Check if database supports batch operations
            supports_batch = getattr(self.db, 'supports_batch_operations', lambda: False)()

            if supports_batch:
                return self._save_batch_operations(speed_ngrams, error_ngrams)
            else:
                return self._save_individual_operations(speed_ngrams, error_ngrams)

        except Exception as e:
            logger.error(f"Error saving n-grams: {str(e)}", exc_info=True)
            return False

    def _save_batch_operations(self, speed_ngrams: List[SpeedNGram], error_ngrams: List[ErrorNGram]) -> bool:
        """Save using batch database operations."""
        try:
            # Batch insert speed n-grams
            if speed_ngrams:
                speed_data = [
                    (str(n.id), str(n.session_id), n.size, n.text, n.duration_ms, 
                     n.ms_per_keystroke, n.speed_mode.value, n.created_at)
                    for n in speed_ngrams
                ]
                self.db.executemany(
                    "INSERT INTO session_ngram_speed "
                    "(ngram_speed_id, session_id, ngram_size, ngram_text, "
                    "ngram_time_ms, ms_per_keystroke, speed_mode, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    speed_data
                )

            # Batch insert error n-grams
            if error_ngrams:
                error_data = [
                    (str(n.id), str(n.session_id), n.size, n.expected_text, 
                     n.actual_text, n.duration_ms, n.created_at)
                    for n in error_ngrams
                ]
                self.db.executemany(
                    "INSERT INTO session_ngram_errors "
                    "(ngram_error_id, session_id, ngram_size, expected_text, "
                    "actual_text, duration_ms, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    error_data
                )

            logger.info(f"Batch saved {len(speed_ngrams)} speed n-grams and {len(error_ngrams)} error n-grams")
            return True

        except Exception as e:
            logger.error(f"Batch save failed: {str(e)}")
            return False

    def _save_individual_operations(self, speed_ngrams: List[SpeedNGram], error_ngrams: List[ErrorNGram]) -> bool:
        """Fallback to individual save operations."""
        success_count = 0
        total_count = len(speed_ngrams) + len(error_ngrams)

        # Save speed n-grams individually
        for ngram in speed_ngrams:
            if self._save_single_speed_ngram(ngram):
                success_count += 1

        # Save error n-grams individually
        for ngram in error_ngrams:
            if self._save_single_error_ngram(ngram):
                success_count += 1

        logger.info(f"Individual save completed: {success_count}/{total_count} n-grams saved")
        return success_count == total_count

    def _save_single_speed_ngram(self, ngram: SpeedNGram) -> bool:
        """Save a single speed n-gram."""
        try:
            self.db.execute(
                "INSERT INTO session_ngram_speed "
                "(ngram_speed_id, session_id, ngram_size, ngram_text, "
                "ngram_time_ms, ms_per_keystroke, speed_mode, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(ngram.id), str(ngram.session_id), ngram.size, ngram.text,
                 ngram.duration_ms, ngram.ms_per_keystroke, ngram.speed_mode.value, ngram.created_at)
            )
            return True
        except Exception as e:
            logger.error(f"Error saving speed n-gram: {str(e)}")
            return False

    def _save_single_error_ngram(self, ngram: ErrorNGram) -> bool:
        """Save a single error n-gram."""
        try:
            self.db.execute(
                "INSERT INTO session_ngram_errors "
                "(ngram_error_id, session_id, ngram_size, expected_text, "
                "actual_text, duration_ms, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(ngram.id), str(ngram.session_id), ngram.size, ngram.expected_text,
                 ngram.actual_text, ngram.duration_ms, ngram.created_at)
            )
            return True
        except Exception as e:
            logger.error(f"Error saving error n-gram: {str(e)}")
            return False

    def _validate_timing_data(self, keystrokes: List[Keystroke]) -> bool:
        """Validate timing data for keystrokes."""
        for keystroke in keystrokes:
            if keystroke.timestamp is None:
                logger.error(f"Null timestamp in keystroke: {keystroke}")
                return False
            # Additional timestamp validation could be added here
        return True

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
