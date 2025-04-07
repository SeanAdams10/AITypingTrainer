"""
TrigramAnalyzer model for analyzing typing performance with trigrams.
"""
from typing import Dict, List, Any, Optional, Tuple
import datetime
from ..database_manager import DatabaseManager


class TrigramAnalyzer:
    """
    Model class for analyzing trigram typing performance.
    Handles both speed and error analysis.
    """
    
    def __init__(self):
        """Initialize a TrigramAnalyzer instance."""
        self.db = DatabaseManager()
    
    def analyze_trigrams(self) -> bool:
        """
        Process keystroke data to build trigram speed and error tables.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Clear existing trigram data
            cursor.execute("DELETE FROM session_trigram_speed")
            cursor.execute("DELETE FROM session_trigram_error")
            
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
                
                # Process for trigrams (need at least 3 keystrokes)
                if len(keystrokes) < 3:
                    continue
                
                # Analyze for trigram speed
                for i in range(2, len(keystrokes)):
                    prev2_keystroke = keystrokes[i-2]
                    prev1_keystroke = keystrokes[i-1]
                    curr_keystroke = keystrokes[i]
                    
                    # Only include correct keystrokes for timing information
                    if (prev2_keystroke['is_correct'] and 
                        prev1_keystroke['is_correct'] and 
                        curr_keystroke['is_correct'] and 
                        curr_keystroke['time_since_previous'] is not None):
                        
                        trigram_text = (
                            prev2_keystroke['expected_char'] + 
                            prev1_keystroke['expected_char'] + 
                            curr_keystroke['expected_char']
                        )
                        time_taken = curr_keystroke['time_since_previous']
                        
                        # Skip if time is unreasonably long (e.g., user was distracted)
                        if time_taken > 5000:  # 5 seconds
                            continue
                        
                        # Add to trigram speed table
                        cursor.execute("""
                            INSERT INTO session_trigram_speed 
                            (session_id, trigram_id, trigram_time, trigram_text)
                            VALUES (?, ?, ?, ?)
                        """, (session_id, i, time_taken, trigram_text))
                
                # Analyze for trigram errors
                for i in range(2, len(keystrokes)):
                    prev2_keystroke = keystrokes[i-2]
                    prev1_keystroke = keystrokes[i-1]
                    curr_keystroke = keystrokes[i]
                    
                    # For errors, look for error in the third character of the trigram
                    if not curr_keystroke['is_correct']:
                        trigram_text = (
                            prev2_keystroke['expected_char'] + 
                            prev1_keystroke['expected_char'] + 
                            curr_keystroke['expected_char']
                        )
                        time_taken = curr_keystroke['time_since_previous'] or 0
                        
                        # Add to trigram error table
                        cursor.execute("""
                            INSERT INTO session_trigram_error 
                            (session_id, trigram_id, trigram_time, trigram_text)
                            VALUES (?, ?, ?, ?)
                        """, (session_id, i, time_taken, trigram_text))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error analyzing trigrams: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def get_slow_trigrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the slowest trigrams from the database.
        
        Args:
            limit: Maximum number of trigrams to return
            min_occurrences: Minimum number of times a trigram must occur
            
        Returns:
            List of dictionaries with trigram information
        """
        query = """
            SELECT 
                trigram_text, 
                COUNT(*) as occurrence_count,
                AVG(trigram_time) as avg_time
            FROM session_trigram_speed
            GROUP BY trigram_text
            HAVING COUNT(*) >= ?
            ORDER BY avg_time DESC
            LIMIT ?
        """
        
        return self.db.execute_query(query, (min_occurrences, limit))
    
    def get_error_trigrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        """
        Get the most common error trigrams.
        
        Args:
            limit: Maximum number of trigrams to return
            min_occurrences: Minimum number of times a trigram must occur
            
        Returns:
            List of dictionaries with trigram information
        """
        query = """
            SELECT 
                trigram_text, 
                COUNT(*) as occurrence_count
            FROM session_trigram_error
            GROUP BY trigram_text
            HAVING COUNT(*) >= ?
            ORDER BY occurrence_count DESC
            LIMIT ?
        """
        
        return self.db.execute_query(query, (min_occurrences, limit))
    
    def create_trigram_snippet(self, limit: int = 20, min_occurrences: int = 2) -> Tuple[int, str]:
        """
        Create a new snippet from the slowest trigrams.
        
        Args:
            limit: Maximum number of slowest trigrams to include
            min_occurrences: Minimum number of times a trigram must appear across sessions
        
        Returns:
            Tuple of (snippet_id, report) where report is a summary of what was included
        """
        try:
            # Get the slow trigrams
            slow_trigrams = self.get_slow_trigrams(limit, min_occurrences)
            
            if not slow_trigrams:
                return (-1, "No slow trigrams found with the specified criteria.")
            
            # Get all words from the database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM words")
            all_words = [row['word'] for row in cursor.fetchall()]
            
            # Find words containing the slow trigrams
            trigram_words = {}
            for trigram_data in slow_trigrams:
                trigram = trigram_data['trigram_text']
                matching_words = [word for word in all_words if trigram in word]
                
                # Select up to 5 words for each trigram
                selected_words = matching_words[:5] if matching_words else []
                trigram_words[trigram] = {
                    'avg_time': trigram_data['avg_time'],
                    'occurrence_count': trigram_data['occurrence_count'],
                    'words': selected_words
                }
            
            # Create the practice text
            practice_lines = [
                f"# Practice Session - Slow Trigrams ({datetime.datetime.now().strftime('%Y-%m-%d')})",
                "",
                "This practice text is generated based on your slow trigrams.",
                "Focus on the words containing these challenging character combinations.",
                "",
                "## Slow Trigrams Practice:"
            ]
            
            for trigram, data in trigram_words.items():
                words = data['words'] if data['words'] else [f"<no words containing '{trigram}'>"]
                practice_lines.append(
                    f"Trigram '{trigram}' (avg: {data['avg_time']:.1f}ms, count: {data['occurrence_count']}): " +
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
            snippet_name = f"Slow Trigrams Practice ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
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
            report = f"Created practice snippet '{snippet_name}' with {len(trigram_words)} slow trigrams."
            
            return (snippet_id, report)
            
        except Exception as e:
            print(f"Error creating trigram snippet: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return (-1, f"Error: {str(e)}")
