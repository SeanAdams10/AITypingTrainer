"""
NGramAnalyzer model for analyzing typing performance with n-grams of varying sizes.
"""
from typing import Dict, List, Any, Optional
import datetime
import sqlite3
from db.database_manager import DatabaseManager

class NGramAnalyzer:
    """
    Model class for analyzing n-gram typing performance.
    Handles both speed and error analysis for n-grams of varying sizes (2-8).
    """
    
    # Common table names for all n-gram sizes
    SPEED_TABLE = "session_ngram_speed"
    ERROR_TABLE = "session_ngram_error"
    
    def __init__(self, n: int) -> None:
        """
        Initialize the n-gram analyzer for the specified size.
        
        Args:
            n: The n-gram size (2-8)
        """
        if n < 2 or n > 8:
            raise ValueError(f"n must be between 2 and 8, got {n}")
        
        self.n: int = n
        self.db_manager: DatabaseManager = DatabaseManager.get_instance()
        
        # Setup names for use in SQL and reporting
        self.n_gram_name = {
            2: "Bigram",
            3: "Trigram",
            4: "4-gram",
            5: "5-gram", 
            6: "6-gram",
            7: "7-gram",
            8: "8-gram"
        }.get(n)

    def analyze_ngrams(self) -> bool:
        """
        Process keystroke data to build n-gram speed and error tables.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Ensure tables exist
            self._ensure_tables_exist(cursor)
            
            # Clear existing n-gram data
            cursor.execute(f"DELETE FROM {self.SPEED_TABLE} WHERE ngram_size = ?", (self.n,))
            cursor.execute(f"DELETE FROM {self.ERROR_TABLE} WHERE ngram_size = ?", (self.n,))
            
            # Get all practice sessions with keystrokes
            cursor.execute("""
                SELECT DISTINCT session_id 
                FROM practice_session_keystrokes 
                ORDER BY session_id
            """)
            
            sessions = [row['session_id'] for row in cursor.fetchall()]
            
            for session_id in sessions:
                # Get all keystrokes for the session, ordered by keystroke_id
                cursor.execute("""
                    SELECT 
                        session_id, keystroke_id, keystroke_char, expected_char, 
                        is_correct, time_since_previous
                    FROM practice_session_keystrokes
                    WHERE session_id = ?
                    ORDER BY keystroke_id
                """, (session_id,))
                
                keystrokes = cursor.fetchall()
                
                # Process for n-grams (need at least n keystrokes)
                if len(keystrokes) < self.n:
                    continue
                
                # Analyze n-grams for speed and errors
                for i in range(self.n - 1, len(keystrokes)):
                    # Get the n keystrokes for this n-gram
                    ngram_keystrokes = [keystrokes[i - offset] for offset in range(self.n - 1, -1, -1)]
                    
                    # Extract the expected characters
                    ngram_chars = [ks['expected_char'] for ks in ngram_keystrokes]
                    ngram_text = ''.join(ngram_chars)
                    
                    # Skip if any character is whitespace
                    if any(char.isspace() for char in ngram_text):
                        continue
                    
                    # Current keystroke is the last character in the n-gram
                    curr_keystroke = ngram_keystrokes[-1]
                    time_taken = curr_keystroke['time_since_previous']
                    
                    # Check if all keystrokes are correct for speed analysis
                    all_correct = all(ks['is_correct'] for ks in ngram_keystrokes)
                    
                    # Only include n-grams with valid timing data and all correct keystrokes for speed
                    if all_correct and time_taken is not None and time_taken > 0:
                        # Skip if time is unreasonably long (e.g., user was distracted)
                        if time_taken > 5000:  # 5 seconds
                            continue
                        
                        # Add to n-gram speed table
                        cursor.execute(f"""
                            INSERT INTO {self.SPEED_TABLE} 
                            (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                            VALUES (?, ?, ?, ?, ?)
                        """, (session_id, self.n, i, time_taken, ngram_text))
                    
                    # Only include n-grams with an error on the last character for error analysis
                    if not curr_keystroke['is_correct']:
                        # Add to n-gram error table only if the last character is incorrect
                        cursor.execute(f"""
                            INSERT INTO {self.ERROR_TABLE} 
                            (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                            VALUES (?, ?, ?, ?, ?)
                        """, (session_id, self.n, i, time_taken or 0, ngram_text))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error analyzing {self.n}-grams: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def get_slow_ngrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the slowest n-grams from the database.

        Args:
            limit (int): Maximum number of n-grams to return
            min_occurrences (int): Minimum number of times an n-gram must occur

        Returns:
            List[Dict[str, Any]]: Each dict contains 'ngram_text', 'ngram_size', 'avg_time', and 'count'
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
            limit: Maximum number of n-grams to return
            min_occurrences: Minimum number of times an n-gram must occur
            
        Returns:
            List of dictionaries with n-gram information
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
    
    def get_speed_results_for_session(self, session_id: str) -> list[dict]:
        """
        Get speed n-gram results for a specific session.
        """
        query = f"""
            SELECT ngram_text, ngram_time
            FROM {self.SPEED_TABLE}
            WHERE session_id = ? AND ngram_size = ?
            ORDER BY ngram_id
        """
        return self.db_manager.execute_query(query, (session_id, self.n))

    def get_error_results_for_session(self, session_id: str) -> list[dict]:
        """
        Get error n-gram results for a specific session.
        """
        query = f"""
            SELECT ngram_text, ngram_time
            FROM {self.ERROR_TABLE}
            WHERE session_id = ? AND ngram_size = ?
            ORDER BY ngram_id
        """
        return self.db_manager.execute_query(query, (session_id, self.n))

    def create_ngram_snippet(
        self,
        ngram_type: str = "slow",
        name: Optional[str] = None,
        count: int = 20,
        min_occurrences: int = 2
    ) -> dict:
        """
        Create a new snippet from n-gram data (slow/error/etc).

        Args:
            ngram_type (str): Type of n-gram to use (e.g., 'slow', 'error').
            name (Optional[str]): Custom name for the snippet (default: generated).
            count (int): Maximum number of n-grams to include (default: 20).
            min_occurrences (int): Minimum times an n-gram must appear (default: 2).

        Returns:
            dict: {'id': snippet_id, 'text': snippet_text, 'name': snippet_name}. On error, id is -1 and text contains error message.
        """
        import pydantic
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            # Select n-grams based on type
            if ngram_type == "slow":
                ngrams = self.get_slow_ngrams(count, min_occurrences)
                ngram_label = f"Slow {self.n_gram_name}s"
            elif ngram_type == "error":
                ngrams = self.get_error_ngrams(count, min_occurrences)
                ngram_label = f"Error {self.n_gram_name}s"
            else:
                return {"id": -1, "text": f"Unknown ngram_type '{ngram_type}' specified.", "name": name or "N-gram Practice"}
            if not ngrams:
                return {"id": -1, "text": f"No {ngram_type} {self.n}-grams found with the specified criteria.", "name": name or "N-gram Practice"}
            cursor.execute("SELECT word FROM words")
            all_words = [row['word'] for row in cursor.fetchall()]
            ngram_words = {}
            for ngram_data in ngrams:
                ngram = ngram_data['ngram_text']
                matching_words = [word for word in all_words if ngram in word]
                selected_words = matching_words[:5] if matching_words else []
                ngram_words[ngram] = {
                    'avg_time': ngram_data.get('avg_time', 0.0),
                    'occurrence_count': ngram_data.get('occurrence_count', 0),
                    'words': selected_words
                }
            practice_lines = [
                f"# Practice Session - {ngram_label} ({datetime.datetime.now().strftime('%Y-%m-%d')})",
                "",
                f"This practice text is generated based on your {ngram_type} {self.n_gram_name.lower() if self.n_gram_name else ''}s.",
                "Focus on the words containing these challenging character combinations.",
                "",
                f"## {ngram_label} Practice:"
            ]
            for ngram, data in ngram_words.items():
                words = data['words'] if data['words'] else [f"<no words containing '{ngram}'>"]
                practice_lines.append(
                    f"{self.n_gram_name} '{ngram}' (avg: {data['avg_time']:.1f}ms, count: {data['occurrence_count']}): " +
                    " ".join(words)
                )
            practice_text = "\n".join(practice_lines)
            cursor.execute(
                "SELECT category_id FROM text_category WHERE category_name = 'Practice Snippets'"
            )
            result = cursor.fetchone()
            if result:
                category_id = result['category_id']
            else:
                cursor.execute(
                    "INSERT INTO text_category (category_name) VALUES ('Practice Snippets')"
                )
                category_id = cursor.lastrowid
            snippet_name = name or f"{ngram_label} Practice ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
            cursor.execute(
                "INSERT INTO text_snippets (category_id, snippet_name) VALUES (?, ?)",
                (category_id, snippet_name)
            )
            snippet_id = cursor.lastrowid
            max_part_size = 8000
            for i in range(0, len(practice_text), max_part_size):
                part_content = practice_text[i:i + max_part_size]
                part_number = i // max_part_size
                cursor.execute(
                    "INSERT INTO snippet_parts (snippet_id, part_number, content) VALUES (?, ?, ?)",
                    (snippet_id, part_number, part_content)
                )
            conn.commit()
            conn.close()
            return {"id": snippet_id, "text": practice_text, "name": snippet_name}
        except Exception as e:
            print(f"Error creating {self.n}-gram snippet: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return {"id": -1, "text": f"Error: {str(e)}", "name": name or "N-gram Practice"}
    def _ensure_tables_exist(self, cursor: sqlite3.Cursor) -> None:
        """
        Ensure that the necessary database tables exist for this n-gram size.
        
        Args:
            cursor: An active SQLite cursor
        """
        # Create speed table if it doesn't exist
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.SPEED_TABLE} (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
        """)
        
        # Create error table if it doesn't exist
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.ERROR_TABLE} (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
        """)
    
    @staticmethod
    def create_all_tables() -> bool:
        """
        Create all necessary tables for all supported n-gram sizes (2-8).
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = DatabaseManager.get_instance().get_connection()
            cursor = conn.cursor()
            
            for n in range(2, 9):
                analyzer = NGramAnalyzer(n)
                analyzer._ensure_tables_exist(cursor)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error creating n-gram tables: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
            
    def record_keystrokes(self, session_id: str, keystrokes: List[Dict[str, Any]]) -> bool:
        """
        Record n-grams for a session based on keystroke data.
        This is called when a practice session ends to analyze n-grams.
        
        Args:
            session_id: The practice session ID
            keystrokes: List of keystroke dictionaries with all keystroke data
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Convert keystrokes to format needed for analyze_ngrams
        if len(keystrokes) < self.n:
            return True  # Not enough keystrokes for this n-gram size
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Ensure tables exist
        self._ensure_tables_exist(cursor)
        
        try:
            for i in range(self.n - 1, len(keystrokes)):
                # Get the n keystrokes for this n-gram
                ngram_keystrokes = keystrokes[i - (self.n - 1):i + 1]
                
                # Extract the expected characters
                ngram_chars = [ks.get('expected_char', '') for ks in ngram_keystrokes]
                ngram_text = ''.join(ngram_chars)
                
                # Skip if any character is whitespace
                if any(char.isspace() for char in ngram_text):
                    continue
                
                # Current keystroke is the last character in the n-gram
                curr_keystroke = ngram_keystrokes[-1]
                time_taken = curr_keystroke.get('time_since_previous', 0)
                
                # Check if all keystrokes are correct for speed analysis
                all_correct = all(ks.get('is_correct', False) for ks in ngram_keystrokes)
                
                # Only include n-grams with valid timing data and all correct keystrokes for speed
                if all_correct and time_taken and time_taken > 0:
                    # Skip if time is unreasonably long (e.g., user was distracted)
                    if time_taken > 5000:  # 5 seconds
                        continue
                    
                    # Add to n-gram speed table
                    cursor.execute(f"""
                        INSERT INTO {self.SPEED_TABLE} 
                        (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, self.n, i, time_taken, ngram_text))
                
                # Only include n-grams with an error on the last character for error analysis
                if not curr_keystroke.get('is_correct', True):
                    # Add to n-gram error table only if the last character is incorrect
                    cursor.execute(f"""
                        INSERT INTO {self.ERROR_TABLE} 
                        (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, self.n, i, time_taken or 0, ngram_text))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error recording {self.n}-grams for session {session_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
