"""
Extensions for the PracticeSession model to track keystrokes, errors, and n-gram analysis.
This implements the functionality specified in TypingDrill.md for recording typing session data.
"""
import datetime
import sqlite3
from typing import Any, Dict, List

from db.database_manager import DatabaseManager
from models.ngram_analyzer import NGramAnalyzer
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
    
    def record_keystroke(
        self,
        session_id: str,
        char_position: int,
        char_typed: str,
        expected_char: str,
        timestamp: datetime.datetime,
        time_since_previous: int
    ) -> int:
        """
        Record a keystroke for a typing session.

        Args:
            session_id (str): ID of the practice session
            char_position (int): Position in the text where the keystroke was made
            char_typed (str): The character that was typed
            expected_char (str): The character that was expected at this position
            timestamp (datetime.datetime): When the keystroke occurred
            time_since_previous (int): Milliseconds since previous keystroke (0 for first keystroke)

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

            # Check if character is a backspace (handled as error)
            is_backspace = char_typed == '\b'
            # If it's a backspace or doesn't match expected, it's an error
            is_correct = (not is_backspace) and (char_typed == expected_char)

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
                time_since_previous
            )
            try:
                # Removed commit=True to avoid transaction handling in each keystroke
                cursor = self.db_manager.execute(query, params)
                if cursor is None:
                    raise RuntimeError(f"Failed to insert keystroke for session_id={session_id}, keystroke_id={keystroke_id}")
                return keystroke_id
            except sqlite3.Error as sql_e:
                print(f"SQLite error recording keystroke: {sql_e}, session_id={session_id}, char_position={char_position}")
                raise RuntimeError(f"SQLite error recording keystroke: {sql_e}") from sql_e
        except Exception as e:
            print(f"Error recording keystroke: {e}, session_id={session_id}, char_position={char_position}")
            raise RuntimeError(f"Error recording keystroke: {e}") from e

    def get_keystrokes_for_session(self, session_id: str) -> List[Dict[str, Any]]:
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
                'time_since_previous': row[6] if row[6] is not None else 0,  # time between keystrokes
                'is_correct': row[5]  # is_correct field from database
            })
        
        return result


# PracticeSessionErrorManager class removed as errors are now tracked directly in the keystroke data


# The NgramAnalyzer class has been replaced with the NGramAnalyzer from models.ngram_analyzer


# Extend PracticeSessionManager with methods to use these classes
def save_session_data(
    session_manager: PracticeSessionManager,
    session_id: str,
    keystrokes: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    skip_ngram_analysis: bool = False
) -> bool:
    """
    Save comprehensive session data including keystrokes and n-gram analysis.

    Args:
        session_manager (PracticeSessionManager): PracticeSessionManager instance
        session_id (str): ID of the practice session to save data for
        keystrokes (List[Dict[str, Any]]): List of keystroke data (position, char, timestamp, etc.)
        errors (List[Dict[str, Any]]): Legacy parameter, no longer used (errors tracked in keystrokes)

    Returns:
        bool: True if all data was saved successfully, False otherwise
    """
    if not session_manager or not session_id or not keystrokes:
        print("Missing required parameters for save_session_data")
        return False
    
    db_manager = session_manager.db_manager
    
    try:
        # Initialize managers
        keystroke_manager = PracticeSessionKeystrokeManager(db_manager)
        
        
        # Process keystrokes
        last_timestamp = None
        for i, ks in enumerate(keystrokes):
            # Ensure all required fields are present
            if 'char_position' not in ks or 'timestamp' not in ks:
                print(f"Skipping invalid keystroke (missing required fields) at index {i}: {ks}")
                continue
                
            # Handle both 'char_typed' and 'keystroke_char' field names
            char_typed = ks.get('char_typed', ks.get('keystroke_char'))
            if char_typed is None:
                print(f"Skipping invalid keystroke (missing char_typed/keystroke_char) at index {i}: {ks}")
                continue
                
            # Get expected character from the session content or the keystroke data
            expected_char = ks.get('expected_char')
            if expected_char is None:
                content = session_manager.get_session_content(session_id)
                if content and ks['char_position'] < len(content):
                    expected_char = content[ks['char_position']]
                else:
                    expected_char = '?'
            
            # Calculate time since previous keystroke (in milliseconds)
            current_time = ks['timestamp']
            time_since_previous = ks.get('time_since_previous', 0)
            
            # Only calculate time_since_previous if not provided
            if time_since_previous == 0 and last_timestamp is not None:
                # If timestamps are datetime objects
                if isinstance(current_time, datetime.datetime) and isinstance(last_timestamp, datetime.datetime):
                    time_since_previous = int((current_time - last_timestamp).total_seconds() * 1000)
                # If timestamps are strings, parse them
                elif isinstance(current_time, str) and isinstance(last_timestamp, str):
                    try:
                        current_dt = datetime.datetime.fromisoformat(current_time)
                        last_dt = datetime.datetime.fromisoformat(last_timestamp)
                        time_since_previous = int((current_dt - last_dt).total_seconds() * 1000)
                    except (ValueError, TypeError):
                        # If parsing fails, use a default value
                        time_since_previous = 100
                # If one is a datetime and the other is a string
                elif isinstance(current_time, datetime.datetime) and isinstance(last_timestamp, str):
                    try:
                        last_dt = datetime.datetime.fromisoformat(last_timestamp)
                        time_since_previous = int((current_time - last_dt).total_seconds() * 1000)
                    except (ValueError, TypeError):
                        time_since_previous = 100
                elif isinstance(current_time, str) and isinstance(last_timestamp, datetime.datetime):
                    try:
                        current_dt = datetime.datetime.fromisoformat(current_time)
                        time_since_previous = int((current_dt - last_timestamp).total_seconds() * 1000)
                    except (ValueError, TypeError):
                        time_since_previous = 100
                else:
                    # If they're numbers
                    try:
                        time_since_previous = int((float(current_time) - float(last_timestamp)) * 1000)
                    except (ValueError, TypeError):
                        time_since_previous = 100
            
            # Record the keystroke
            try:
                keystroke_manager.record_keystroke(
                    session_id=session_id,
                    char_position=ks['char_position'],
                    char_typed=char_typed,
                    expected_char=expected_char,
                    timestamp=current_time,
                    time_since_previous=time_since_previous
                )
            except Exception as e:
                print(f"Error recording keystroke: {e}")
                raise
            
            last_timestamp = current_time
        
        # Perform n-gram analysis using the new NGramAnalyzer.analyze_session class method
        # This method handles all the complexities of creating the correct objects
        if not skip_ngram_analysis:
            try:
                # Use the class method to analyze the session
                NGramAnalyzer.analyze_session(session_id, db_manager)
                #todo: save the ngrams
                
            except Exception as e:
                print(f"Error during n-gram analysis: {e}")
                import traceback
                traceback.print_exc()
        

        # Calculate metrics based on keystrokes
        total_keystrokes = len(keystrokes)
        
        # Count backspaces and errors
        backspace_count = sum(1 for ks in keystrokes if ks.get('char_typed') == '\b')
        error_count = sum(1 for ks in keystrokes if ks.get('is_error', 0) == 1 and ks.get('char_typed') != '\b')
        
        # Get the expected characters from the session
        content = session_manager.get_session_content(session_id)
        expected_chars = len(content) if content else 0
        
        # Calculate keystrokes excluding backspaces
        keystrokes_excluding_backspaces = total_keystrokes - backspace_count
        
        # Avoid division by zero
        if keystrokes_excluding_backspaces == 0:
            keystrokes_excluding_backspaces = 1
            
        # Calculate efficiency as a percentage (0.0 to 100.0)
        efficiency = min(100.0, (expected_chars / keystrokes_excluding_backspaces) * 100.0)
        
        # Calculate correctness (correct chars in final state / expected chars)
        # For this, we need to reconstruct the final typed text
        typed_text = []
        for ks in keystrokes:
            char_typed = ks.get('char_typed')
            if char_typed == '\b':
                if typed_text:  # Backspace removes the last character
                    typed_text.pop()
            else:
                typed_text.append(char_typed)
        
        # Count correct characters in final state
        final_text = ''.join(typed_text)
        correct_chars = sum(1 for a, b in zip(final_text, content, strict=False) if a == b) if content else 0
        
        # Calculate correctness as a percentage (0.0 to 100.0)
        correctness = min(100.0, (correct_chars / expected_chars) * 100.0) if expected_chars > 0 else 100.0
        
        # Calculate accuracy (efficiency * correctness / 100)
        accuracy = (efficiency * correctness) / 100.0
        
        # Update the session with the calculated metrics
        update_query = """
            UPDATE practice_sessions 
            SET efficiency = ?, 
                correctness = ?, 
                accuracy = ?
            WHERE session_id = ?
        """
        db_manager.execute(update_query, (efficiency / 100.0, correctness / 100.0, accuracy / 100.0, session_id))
        
        return True
        
    except Exception as e:
        print(f"Error saving session data: {e}")
        import traceback
        traceback.print_exc()
        return False
