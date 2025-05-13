"""
Extensions for the PracticeSession model to track keystrokes, errors, and n-gram analysis.
This implements the functionality specified in TypingDrill.md for recording typing session data.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import datetime
import sqlite3
from db.database_manager import DatabaseManager
from models.practice_session import PracticeSessionManager

class PracticeSessionKeystrokeManager:
    """
    Manager for recording and analyzing keystrokes during typing practice sessions.
    """
    
    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize with a DatabaseManager instance.
        
        Args:
            db_manager: Database manager for executing queries
        """
        self.db_manager = db_manager
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self) -> None:
        """Ensure all required keystroke tracking tables exist."""
        # Create session_keystrokes table if it doesn't exist
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS session_keystrokes (
                session_id TEXT,
                keystroke_id INTEGER,
                keystroke_time DATETIME NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                time_since_previous INTEGER,
                PRIMARY KEY (session_id, keystroke_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            )
        """, commit=True)
    
    def record_keystroke(
        self,
        session_id: int,
        char_position: int,
        char_typed: str,
        expected_char: str,
        timestamp: datetime.datetime,
        time_since_start: int
    ) -> int:
        """
        Record a keystroke for a typing session.

        Args:
            session_id (int): ID of the practice session
            char_position (int): Position in the text where the keystroke was made
            char_typed (str): The character that was typed
            expected_char (str): The character that was expected at this position
            timestamp (datetime.datetime): When the keystroke occurred
            time_since_start (int): Milliseconds since session start (used as time_since_previous)

        Returns:
            int: ID of the recorded keystroke
        Raises:
            RuntimeError: If the keystroke could not be recorded
        """
        try:
            # Get the next keystroke_id for this session
            max_id_result = self.db_manager.execute(
                "SELECT MAX(keystroke_id) FROM session_keystrokes WHERE session_id = ?",
                (str(session_id),)
            ).fetchone()
            max_id = max_id_result[0] if max_id_result and max_id_result[0] is not None else 0
            keystroke_id = max_id + 1

            is_correct = (char_typed == expected_char)

            query = """
                INSERT INTO session_keystrokes (
                    session_id, keystroke_id, keystroke_time, keystroke_char,
                    expected_char, is_correct, time_since_previous
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                str(session_id),
                keystroke_id,
                timestamp.isoformat(),
                char_typed,
                expected_char,
                1 if is_correct else 0,
                time_since_start
            )
            cursor = self.db_manager.execute(query, params, commit=True)
            if cursor is None or cursor.lastrowid is None:
                raise RuntimeError(f"Failed to insert keystroke for session_id={session_id}, keystroke_id={keystroke_id}")
            return keystroke_id
        except Exception as e:
            print(f"Error recording keystroke: {e}")
            raise RuntimeError(f"Error recording keystroke: {e}") from e

    def get_keystrokes_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        """
        Get all keystrokes recorded for a specific session.
        
        Args:
            session_id: ID of the practice session
            
        Returns:
            List of keystroke dictionaries
        """
        query = """
            SELECT keystroke_id, session_id, keystroke_time, keystroke_char, expected_char,
                   is_correct, time_since_previous
            FROM session_keystrokes
            WHERE session_id = ?
            ORDER BY keystroke_id ASC
        """
        
        rows = self.db_manager.execute(query, (session_id,)).fetchall()
        
        result = []
        # We need to add a char_position for the n-gram analyzer since it's not in our table anymore
        # We'll use the keystroke_id as the char_position since they should be in sequence
        for i, row in enumerate(rows):
            result.append({
                'keystroke_id': row[0],
                'session_id': row[1],
                'char_position': i,  # Using the index as a proxy for char_position
                'char_typed': row[3],  # keystroke_char is in position 3
                'expected_char': row[4],
                'timestamp': row[2],  # keystroke_time is in position 2
                'time_since_start': row[6] if row[6] is not None else 0  # time_since_previous
            })
        
        return result


# PracticeSessionErrorManager class removed as errors are now tracked directly in the keystroke data


class NgramAnalyzer:
    """
    Analyze n-grams within typing sessions for both speed and error patterns.
    """
    
    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize with a DatabaseManager instance.
        
        Args:
            db_manager: Database manager for executing queries
        """
        self.db_manager = db_manager
        self._ensure_tables_exist()
        
    def _ensure_tables_exist(self) -> None:
        """Ensure all required n-gram tables exist."""
        # Create session_ngram_speed table matching the discovered schema
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                ngram_speed_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                speed INTEGER NOT NULL
            )
        """, commit=True)
        
        # Add debug for session_ngram_errors schema
        print("Checking session_ngram_errors table schema:")
        try:
            schema = self.db_manager.execute("PRAGMA table_info(session_ngram_errors)").fetchall()
            print(f"session_ngram_errors columns: {[col[1] for col in schema]}")
        except Exception as e:
            print(f"Error checking session_ngram_errors schema: {e}")
        
        # Create session_ngram_errors table with all required columns from the existing schema
        self.db_manager.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_errors (
                ngram_error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                ngram TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                occurrences INTEGER NOT NULL
            )
        """, commit=True)
    
    def analyze_session_ngrams(self, 
                              session_id: int, 
                              min_size: int = 2,
                              max_size: int = 5) -> bool:
        """
        Analyze n-grams for both speed and errors in a completed typing session.
        
        Args:
            session_id: ID of the practice session to analyze
            min_size: Minimum n-gram size (default: 2)
            max_size: Maximum n-gram size (default: 5)
            
        Returns:
            True if analysis was successful, False otherwise
        """
        # Ensure the tables exist
        self._ensure_tables_exist()
        
        # Debug: Print the table schemas
        print("Checking session_ngram_speed table schema:")
        try:
            schema = self.db_manager.execute("PRAGMA table_info(session_ngram_speed)").fetchall()
            print(f"session_ngram_speed columns: {[col[1] for col in schema]}")
        except Exception as e:
            print(f"Error checking session_ngram_speed schema: {e}")
        
        try:
            # Get session keystrokes
            keystrokes = PracticeSessionKeystrokeManager(self.db_manager).get_keystrokes_for_session(session_id)
            
            if not keystrokes:
                return False
                
            # Get session content (the text that was typed)
            session_query = """
                SELECT content FROM practice_sessions WHERE session_id = ?
            """
            session_row = self.db_manager.execute(session_query, (session_id,)).fetchone()
            
            if not session_row:
                return False
                
            content = session_row[0]
            
            # Analyze speed and errors for different n-gram sizes
            for size in range(min_size, min(max_size + 1, len(content))):
                self._analyze_ngram_speed(session_id, content, keystrokes, size)
                self._analyze_ngram_errors(session_id, content, keystrokes, size)
                
            return True
            
        except Exception as e:
            print(f"Error analyzing n-grams: {e}")
            return False
    
    def _analyze_ngram_speed(self, 
                            session_id: int, 
                            content: str, 
                            keystrokes: List[Dict[str, Any]], 
                            ngram_size: int) -> None:
        """
        Analyze typing speed for n-grams of specified size.
        
        Args:
            session_id: ID of the practice session
            content: The content that was typed
            keystrokes: List of keystroke data from the session
            ngram_size: Size of n-grams to analyze
        """
        # Create a dictionary to store n-gram speed data
        ngram_speeds = {}
        
        # Process keystrokes to calculate time taken for each n-gram
        for i in range(len(keystrokes) - ngram_size + 1):
            # Skip if there are errors within this n-gram
            has_error = False
            for j in range(ngram_size):
                if i + j >= len(keystrokes) or keystrokes[i + j]['char_typed'] != keystrokes[i + j]['expected_char']:
                    has_error = True
                    break
            
            if has_error:
                continue
                
            # Extract the n-gram
            pos = keystrokes[i]['char_position']
            if pos + ngram_size > len(content):
                continue
                
            ngram = content[pos:pos + ngram_size]
            
            # Calculate time taken to type this n-gram
            start_time = keystrokes[i]['time_since_start']
            end_time = keystrokes[i + ngram_size - 1]['time_since_start']
            time_taken = end_time - start_time
            
            # Update n-gram statistics
            if ngram in ngram_speeds:
                ngram_speeds[ngram]['total_time'] += time_taken
                ngram_speeds[ngram]['occurrences'] += 1
            else:
                ngram_speeds[ngram] = {
                    'total_time': time_taken,
                    'occurrences': 1
                }
        
        # Save n-gram speed data
        for ngram, data in ngram_speeds.items():
            avg_time = data['total_time'] // data['occurrences']
            
            query = """
                INSERT INTO session_ngram_speed (
                    session_id, ngram, speed
                ) VALUES (?, ?, ?)
            """
            
            params = (
                session_id,
                ngram,
                avg_time  # Use avg_time as the speed
            )
            
            self.db_manager.execute(query, params, commit=True)
    
    def _analyze_ngram_errors(self, 
                             session_id: int, 
                             content: str, 
                             keystrokes: List[Dict[str, Any]], 
                             ngram_size: int) -> None:
        """
        Analyze typing errors for n-grams of specified size.
        
        Args:
            session_id: ID of the practice session
            content: The content that was typed
            keystrokes: List of keystroke data from the session
            ngram_size: Size of n-grams to analyze
        """
        # Create a dictionary to store n-gram error data
        ngram_errors = {}
        
        # Process keystrokes to find n-grams with errors
        for i in range(len(content) - ngram_size + 1):
            ngram = content[i:i + ngram_size]
            
            # Find keystrokes corresponding to this n-gram
            error_count = 0
            found_all = True
            
            for j in range(ngram_size):
                char_pos = i + j
                
                # Find the keystroke for this position
                keystroke = next((k for k in keystrokes if k['char_position'] == char_pos), None)
                
                if not keystroke:
                    found_all = False
                    break
                    
                if keystroke['char_typed'] != keystroke['expected_char']:
                    error_count += 1
            
            if found_all:
                # Update n-gram statistics
                if ngram in ngram_errors:
                    ngram_errors[ngram]['error_count'] += error_count
                    ngram_errors[ngram]['occurrences'] += 1
                else:
                    ngram_errors[ngram] = {
                        'error_count': error_count,
                        'occurrences': 1
                    }
        
        # Save n-gram error data
        for ngram, data in ngram_errors.items():
            if data['error_count'] > 0:  # Only save n-grams with errors
                query = """
                    INSERT INTO session_ngram_errors (
                        session_id, ngram, ngram_size, error_count, occurrences
                    ) VALUES (?, ?, ?, ?, ?)
                """
                
                params = (
                    session_id,
                    ngram,
                    ngram_size,  # Add the ngram_size parameter
                    data['error_count'],
                    data['occurrences']  # Add the occurrences parameter
                )
                
                self.db_manager.execute(query, params, commit=True)


# Extend PracticeSessionManager with methods to use these classes
def save_session_data(
    session_manager: PracticeSessionManager,
    session_id: int,
    keystrokes: List[Dict[str, Any]],
    errors: List[Dict[str, Any]]
) -> bool:
    """
    Save comprehensive session data including keystrokes, errors, and n-gram analysis.

    Args:
        session_manager (PracticeSessionManager): PracticeSessionManager instance
        session_id (int): ID of the practice session to save data for
        keystrokes (List[Dict[str, Any]]): List of keystroke data (position, char, timestamp, etc.)
        errors (List[Dict[str, Any]]): List of error data (position, expected, typed)

    Returns:
        bool: True if all data was saved successfully, False otherwise
    """
    try:
        db_manager = session_manager.db_manager
        keystroke_manager = PracticeSessionKeystrokeManager(db_manager)
        for ks in keystrokes:
            try:
                keystroke_manager.record_keystroke(
                    session_id=session_id,
                    char_position=ks['char_position'],
                    char_typed=ks['char_typed'],
                    expected_char=ks['expected_char'],
                    timestamp=ks['timestamp'],
                    time_since_start=ks['time_since_start']
                )
            except Exception as ke:
                print(f"Failed to save keystroke at position {ks.get('char_position')}: {ke}")
                return False
        print(f"Found {len(errors)} errors in session data - these are already tracked in the keystroke table.")
        for err in errors:
            pass
        ngram_analyzer = NgramAnalyzer(db_manager)
        ngram_analyzer.analyze_session_ngrams(session_id)
        return True
    except Exception as e:
        print(f"Error saving session data: {e}")
        return False

