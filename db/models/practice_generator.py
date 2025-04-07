"""
PracticeGenerator for creating custom practice snippets based on user data.
"""
from typing import Dict, List, Any, Optional, Tuple
import datetime
import random
from ..database_manager import DatabaseManager
from .bigram_analyzer import BigramAnalyzer
from .trigram_analyzer import TrigramAnalyzer


class PracticeGenerator:
    """
    Model class for generating custom practice snippets based on user performance data.
    """
    
    def __init__(self):
        """Initialize a PracticeGenerator instance."""
        self.db = DatabaseManager()
        self.bigram_analyzer = BigramAnalyzer()
        self.trigram_analyzer = TrigramAnalyzer()
    
    def build_word_table(self) -> bool:
        """
        Build a table of unique words from all text snippets.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Clear the words table
            cursor.execute("DELETE FROM words")
            
            # Get text content from all snippets
            cursor.execute("""
                SELECT snippet_id, content
                FROM snippet_parts
                ORDER BY snippet_id, part_number
            """)
            
            snippet_parts = cursor.fetchall()
            
            words_seen = set()  # Keep track of words we've already processed
            
            # Process each part to extract words
            for part in snippet_parts:
                # Extract words (filtering out non-alphanumeric characters)
                content = part['content']
                word_list = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in content).split()
                
                # Filter for words of reasonable length
                for word in word_list:
                    clean_word = word.strip().lower()
                    if clean_word and len(clean_word) >= 2 and clean_word not in words_seen:
                        words_seen.add(clean_word)
                        cursor.execute(
                            "INSERT INTO words (word) VALUES (?)",
                            (clean_word,)
                        )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error building word table: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def create_practice_snippet(self) -> Tuple[int, str]:
        """
        Create a comprehensive practice snippet based on slow and error-prone n-grams.
        
        This function:
        1. Gets the slowest bigrams and trigrams from speed tables
        2. Gets the most common bigrams and trigrams from error tables
        3. Finds words containing these n-grams
        4. Creates a practice text by randomly selecting items until reaching 1000+ chars
        
        Returns:
            Tuple of (snippet_id, report) where report is a summary of what was included
        """
        try:
            # Get bigram data
            slow_bigrams = self.bigram_analyzer.get_slow_bigrams(10, 2)
            error_bigrams = self.bigram_analyzer.get_error_bigrams(10, 2)
            
            # Get trigram data
            slow_trigrams = self.trigram_analyzer.get_slow_trigrams(10, 2)
            error_trigrams = self.trigram_analyzer.get_error_trigrams(10, 2)
            
            # If no data exists, return error
            if not (slow_bigrams or error_bigrams or slow_trigrams or error_trigrams):
                return (-1, "No analysis data found. Please analyze bigrams and trigrams first.")
            
            # Get all words from the database
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM words")
            all_words = [row['word'] for row in cursor.fetchall()]
            
            # Group words by the n-grams they contain
            word_groups = {}
            
            # Add words for slow bigrams
            for item in slow_bigrams:
                bigram = item['bigram_text']
                matching_words = [word for word in all_words if bigram in word][:5]  # Limit to 5 words
                if matching_words:
                    word_groups[f"slow_bigram:{bigram}"] = {
                        'type': 'slow_bigram',
                        'text': bigram,
                        'words': matching_words,
                        'description': f"Slow bigram '{bigram}' (avg: {item['avg_time']:.1f}ms)"
                    }
            
            # Add words for error bigrams
            for item in error_bigrams:
                bigram = item['bigram_text']
                matching_words = [word for word in all_words if bigram in word][:5]  # Limit to 5 words
                if matching_words:
                    word_groups[f"error_bigram:{bigram}"] = {
                        'type': 'error_bigram',
                        'text': bigram,
                        'words': matching_words,
                        'description': f"Error-prone bigram '{bigram}' (errors: {item['occurrence_count']})"
                    }
            
            # Add words for slow trigrams
            for item in slow_trigrams:
                trigram = item['trigram_text']
                matching_words = [word for word in all_words if trigram in word][:5]  # Limit to 5 words
                if matching_words:
                    word_groups[f"slow_trigram:{trigram}"] = {
                        'type': 'slow_trigram',
                        'text': trigram,
                        'words': matching_words,
                        'description': f"Slow trigram '{trigram}' (avg: {item['avg_time']:.1f}ms)"
                    }
            
            # Add words for error trigrams
            for item in error_trigrams:
                trigram = item['trigram_text']
                matching_words = [word for word in all_words if trigram in word][:5]  # Limit to 5 words
                if matching_words:
                    word_groups[f"error_trigram:{trigram}"] = {
                        'type': 'error_trigram',
                        'text': trigram,
                        'words': matching_words,
                        'description': f"Error-prone trigram '{trigram}' (errors: {item['occurrence_count']})"
                    }
            
            # Create the practice text
            practice_lines = [
                f"# Comprehensive Practice ({datetime.datetime.now().strftime('%Y-%m-%d')})",
                "",
                "This practice session combines words containing your:",
                "- Slowest bigrams and trigrams",
                "- Most error-prone bigrams and trigrams",
                "",
                "## Practice Exercise:"
            ]
            
            # Organize by type for better practice
            sections = {
                'slow_bigram': [],
                'error_bigram': [],
                'slow_trigram': [],
                'error_trigram': []
            }
            
            for key, group in word_groups.items():
                sections[group['type']].append(group)
            
            # Add each section to practice text
            for section_type, section_items in sections.items():
                if section_items:
                    if section_type == 'slow_bigram':
                        practice_lines.append("\n### Slow Bigrams:")
                    elif section_type == 'error_bigram':
                        practice_lines.append("\n### Error-Prone Bigrams:")
                    elif section_type == 'slow_trigram':
                        practice_lines.append("\n### Slow Trigrams:")
                    elif section_type == 'error_trigram':
                        practice_lines.append("\n### Error-Prone Trigrams:")
                    
                    for item in section_items:
                        practice_lines.append(f"{item['description']}: {' '.join(item['words'])}")
            
            # Create a paragraph mixing everything
            practice_lines.append("\n### Mixed Practice Paragraph:")
            
            all_words_for_paragraph = []
            for group in word_groups.values():
                all_words_for_paragraph.extend(group['words'])
            
            if all_words_for_paragraph:
                # Shuffle and pick a subset to create a paragraph
                random.shuffle(all_words_for_paragraph)
                selected_words = all_words_for_paragraph[:min(100, len(all_words_for_paragraph))]
                
                # Split into sentences of about 8-12 words
                sentences = []
                for i in range(0, len(selected_words), random.randint(8, 12)):
                    sentence_words = selected_words[i:i+random.randint(8, 12)]
                    sentence = " ".join(sentence_words)
                    sentences.append(sentence.capitalize() + ".")
                
                paragraph = " ".join(sentences)
                practice_lines.append(paragraph)
            
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
            snippet_name = f"Comprehensive Practice ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})"
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
            
            # Create a summary report
            item_counts = {
                'slow_bigram': len(sections['slow_bigram']),
                'error_bigram': len(sections['error_bigram']),
                'slow_trigram': len(sections['slow_trigram']),
                'error_trigram': len(sections['error_trigram'])
            }
            
            report = (
                f"Created practice snippet '{snippet_name}' including:\n"
                f"- {item_counts['slow_bigram']} slow bigrams\n"
                f"- {item_counts['error_bigram']} error-prone bigrams\n"
                f"- {item_counts['slow_trigram']} slow trigrams\n"
                f"- {item_counts['error_trigram']} error-prone trigrams"
            )
            
            return (snippet_id, report)
            
        except Exception as e:
            print(f"Error creating practice snippet: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return (-1, f"Error: {str(e)}")
