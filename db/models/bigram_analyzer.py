"""
BigramAnalyzer model for analyzing typing performance with bigrams.
"""
from typing import Dict, List, Any, Optional, Tuple
import datetime
from ..database_manager import DatabaseManager


class BigramAnalyzer:
    """
    Model class for analyzing bigram typing performance.
    Handles both speed and error analysis.
    """
    
    def __init__(self):
        """Initialize a BigramAnalyzer instance."""
        self.db = DatabaseManager()
    
    def analyze_bigrams(self) -> bool:
        """
        Process keystroke data to build bigram speed and error tables.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Clear existing bigram data
            cursor.execute("DELETE FROM session_bigram_speed")
            cursor.execute("DELETE FROM session_bigram_error")
            
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
                
                # Process for bigrams (need at least 2 keystrokes)
                if len(keystrokes) < 2:
                    continue
                
                # Analyze for bigram speed
                for i in range(1, len(keystrokes)):
                    prev_keystroke = keystrokes[i-1]
                    curr_keystroke = keystrokes[i]
                    
                    # Only include correct keystrokes for timing information
                    if (prev_keystroke['is_correct'] and 
                        curr_keystroke['is_correct'] and 
                        curr_keystroke['time_since_previous'] is not None):
                        
                        bigram_text = prev_keystroke['expected_char'] + curr_keystroke['expected_char']
                        time_taken = curr_keystroke['time_since_previous']
                        
                        # Skip if time is unreasonably long (e.g., user was distracted)
                        if time_taken > 5000:  # 5 seconds
                            continue
                        
                        # Add to bigram speed table
                        cursor.execute("""
                            INSERT INTO session_bigram_speed 
                            (session_id, bigram_id, bigram_time, bigram_text)
                            VALUES (?, ?, ?, ?)
                        """, (session_id, i, time_taken, bigram_text))
                
                # Analyze for bigram errors
                for i in range(1, len(keystrokes)):
                    prev_keystroke = keystrokes[i-1]
                    curr_keystroke = keystrokes[i]
                    
                    # For errors, look for error in the second character of the bigram
                    if not curr_keystroke['is_correct']:
                        bigram_text = prev_keystroke['expected_char'] + curr_keystroke['expected_char']
                        time_taken = curr_keystroke['time_since_previous'] or 0
                        
                        # Add to bigram error table
                        cursor.execute("""
                            INSERT INTO session_bigram_error 
                            (session_id, bigram_id, bigram_time, bigram_text)
                            VALUES (?, ?, ?, ?)
                        """, (session_id, i, time_taken, bigram_text))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error analyzing bigrams: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def get_slow_bigrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the slowest bigrams from the database.
        
        Args:
            limit: Maximum number of bigrams to return
            min_occurrences: Minimum number of times a bigram must occur
            
        Returns:
            List of dictionaries with bigram information
        """
        query = """
            SELECT 
                bigram_text, 
                COUNT(*) as occurrence_count,
                AVG(bigram_time) as avg_time
            FROM session_bigram_speed
            GROUP BY bigram_text
            HAVING COUNT(*) >= ?
            ORDER BY avg_time DESC
            LIMIT ?
        """
        
        return self.db.execute_query(query, (min_occurrences, limit))
    
    def get_error_bigrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the most common error bigrams.
        
        Args:
            limit: Maximum number of bigrams to return
            min_occurrences: Minimum number of times a bigram must occur
            
        Returns:
            List of dictionaries with bigram information
        """
        query = """
            SELECT 
                bigram_text, 
                COUNT(*) as occurrence_count
            FROM session_bigram_error
            GROUP BY bigram_text
            HAVING COUNT(*) >= ?
            ORDER BY occurrence_count DESC
            LIMIT ?
        """
        
        return self.db.execute_query(query, (min_occurrences, limit))
    
    def create_bigram_snippet(self, limit: int = 20, min_occurrences: int = 2) -> Tuple[int, str]:
        """
        Create a new snippet from the slowest bigrams.
        
        Args:
            limit: Maximum number of slowest bigrams to include
            min_occurrences: Minimum number of times a bigram must appear across sessions
        
        Returns:
            Tuple of (snippet_id, report) where report is a summary of what was included
        """
        try:
            # Get the slow bigrams
            slow_bigrams = self.get_slow_bigrams(limit, min_occurrences)
            
            if not slow_bigrams:
                return (-1, "No slow bigrams found with the specified criteria.")
            
            # Get all words from the database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM words")
            all_words = [row['word'] for row in cursor.fetchall()]
            
            # Find words containing the slow bigrams
            bigram_words = {}
            for bigram_data in slow_bigrams:
                bigram = bigram_data['bigram_text']
                matching_words = [word for word in all_words if bigram in word]
                
                # Select up to 5 words for each bigram
                selected_words = matching_words[:5] if matching_words else []
                bigram_words[bigram] = {
                    'avg_time': bigram_data['avg_time'],
                    'occurrence_count': bigram_data['occurrence_count'],
                    'words': selected_words
                }
            
            # Create the practice text
            practice_lines = [
                f"# Practice Session - Slow Bigrams ({datetime.datetime.now().strftime('%Y-%m-%d')})",
                "",
                "This practice text is generated based on your slow bigrams.",
                "Focus on the words containing these challenging character combinations.",
                "",
                "## Slow Bigrams Practice:"
            ]
            
            for bigram, data in bigram_words.items():
                words = data['words'] if data['words'] else [f"<no words containing '{bigram}'>"]
                practice_lines.append(
                    f"Bigram '{bigram}' (avg: {data['avg_time']:.1f}ms, count: {data['occurrence_count']}): " +
                    " ".join(words)
                )
            
            practice_text = "\n".join(practice_lines)
            
            # Create a category for practice snippets if it doesn't exist
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
            
            # Create the snippet
            snippet_name = f"Slow Bigrams Practice ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
            cursor.execute(
                "INSERT INTO text_snippets (category_id, snippet_name) VALUES (?, ?)",
                (category_id, snippet_name)
            )
            snippet_id = cursor.lastrowid
            
            # Add the content
            # Split content if necessary (SQLite text size limitations)
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
            
            # Create a report
            report = f"Created practice snippet '{snippet_name}' with {len(bigram_words)} slow bigrams."
            
            return (snippet_id, report)
            
        except Exception as e:
            print(f"Error creating bigram snippet: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return (-1, f"Error: {str(e)}")
