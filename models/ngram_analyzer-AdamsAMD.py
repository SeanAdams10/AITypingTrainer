"""
NGramAnalyzer model for analyzing typing performance with n-grams of varying sizes.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, ValidationError, StrictStr, StrictInt
from db.database_manager import DatabaseManager
import datetime


class KeystrokeModel(BaseModel):
    expected_char: StrictStr
    is_correct: bool
    time_since_previous: StrictInt


class NGramAnalyzer:
    """
    Model class for analyzing n-gram typing performance.
    Handles both speed and error analysis for n-grams of varying sizes (2-10).
    """
    SPEED_TABLE = "session_ngram_speed"
    ERROR_TABLE = "session_ngram_error"

    def __init__(self, n: int, db_manager: DatabaseManager) -> None:
        if not isinstance(n, int):
            raise TypeError(f"n must be int, got {type(n).__name__}")
        if n < 2 or n > 10:
            raise ValueError(f"n must be between 2 and 10, got {n}")
        if db_manager is None:
            raise ValueError("db_manager must be provided")
        self.n: int = n
        self.db_manager: DatabaseManager = db_manager
        self.n_gram_name = {
            2: "Bigram",
            3: "Trigram",
            4: "4-gram",
            5: "5-gram",
            6: "6-gram",
            7: "7-gram",
            8: "8-gram",
            9: "9-gram",
            10: "10-gram"
        }[n]

    def analyze_ngrams(self) -> bool:
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.SPEED_TABLE} WHERE ngram_size = ?", (self.n,))
            cursor.execute(f"DELETE FROM {self.ERROR_TABLE} WHERE ngram_size = ?", (self.n,))
            cursor.execute("""
                SELECT DISTINCT session_id 
                FROM practice_session_keystrokes 
                ORDER BY session_id
            """)
            sessions = [row['session_id'] for row in cursor.fetchall()]
            for session_id in sessions:
                cursor.execute("""
                    SELECT session_id, keystroke_id, keystroke_char, expected_char, 
                        is_correct, time_since_previous
                    FROM practice_session_keystrokes
                    WHERE session_id = ?
                    ORDER BY keystroke_id
                """, (session_id,))
                keystrokes = cursor.fetchall()
                if len(keystrokes) < self.n:
                    continue
                for i in range(self.n - 1, len(keystrokes)):
                    ngram_keystrokes = [keystrokes[i - offset] for offset in range(self.n - 1, -1, -1)]
                    ngram_chars = [ks['expected_char'] for ks in ngram_keystrokes]
                    ngram_text = ''.join(ngram_chars)
                    if any(char.isspace() for char in ngram_text):
                        continue
                    curr_keystroke = ngram_keystrokes[-1]
                    time_taken = curr_keystroke['time_since_previous']
                    all_correct = all(ks['is_correct'] for ks in ngram_keystrokes)
                    if all_correct and time_taken is not None and time_taken > 0:
                        if time_taken > 5000:
                            continue
                        cursor.execute(f"""
                            INSERT INTO {self.SPEED_TABLE} 
                            (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                            VALUES (?, ?, ?, ?, ?)
                        """, (session_id, self.n, i, time_taken, ngram_text))
                    if not curr_keystroke['is_correct']:
                        cursor.execute(f"""
                            INSERT INTO {self.ERROR_TABLE} 
                            (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                            VALUES (?, ?, ?, ?, ?)
                        """, (session_id, self.n, i, time_taken or 0, ngram_text))
            conn.commit()
            conn.close()
            return True
        except Exception as e:  # noqa: E722
            print(f"Error analyzing {self.n}-grams: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False

    def get_slow_ngrams(self, limit: int = 20, min_occurrences: int = 2) -> List[Dict[str, Any]]:
        if not isinstance(limit, int):
            raise TypeError("limit must be int")
        if not isinstance(min_occurrences, int):
            raise TypeError("min_occurrences must be int")
        query = f"""
            SELECT ngram_text, COUNT(*) as occurrence_count, AVG(ngram_time) as avg_time
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
        if not isinstance(limit, int):
            raise TypeError("limit must be int")
        if not isinstance(min_occurrences, int):
            raise TypeError("min_occurrences must be int")
        query = f"""
            SELECT ngram_text, COUNT(*) as occurrence_count
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

    def get_speed_results_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        if not isinstance(session_id, int):
            raise TypeError("session_id must be int")
        query = f"""
            SELECT ngram_text, ngram_time
            FROM {self.SPEED_TABLE}
            WHERE session_id = ? AND ngram_size = ?
            ORDER BY ngram_id
        """
        return self.db_manager.execute_query(query, (session_id, self.n))

    def get_error_results_for_session(self, session_id: int) -> List[Dict[str, Any]]:
        if not isinstance(session_id, int):
            raise TypeError("session_id must be int")
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
    ) -> Dict[str, str | int]:
        if not isinstance(ngram_type, str):
            raise TypeError("ngram_type must be str")
        if name is not None and not isinstance(name, str):
            raise TypeError("name must be str or None")
        if not isinstance(count, int):
            raise TypeError("count must be int")
        if not isinstance(min_occurrences, int):
            raise TypeError("min_occurrences must be int")
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
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
                    'occurrence_count': int(ngram_data.get('occurrence_count', ngram_data.get('count', 0))),
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
        except Exception as e:  # noqa: E722
            print(f"Error creating {self.n}-gram snippet: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return {"id": -1, "text": f"Error: {str(e)}", "name": name or "N-gram Practice"}

    def record_keystrokes(self, session_id: int, keystrokes: List[Dict[str, Any]]) -> bool:
        if not isinstance(session_id, int):
            raise TypeError(f"session_id must be int, got {type(session_id).__name__}")
        if not isinstance(keystrokes, list):
            raise TypeError("keystrokes must be a list of dicts")
        try:
            validated_keystrokes = [KeystrokeModel(**ks).dict() for ks in keystrokes]
        except ValidationError as e:
            raise TypeError(f"Invalid keystroke data: {e}")
        if len(validated_keystrokes) < self.n:
            return True
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        try:
            for i in range(self.n - 1, len(validated_keystrokes)):
                ngram_keystrokes = validated_keystrokes[i - (self.n - 1):i + 1]
                ngram_chars = [ks.get('expected_char', '') for ks in ngram_keystrokes]
                ngram_text = ''.join(ngram_chars)
                if any(char.isspace() for char in ngram_text):
                    continue
                curr_keystroke = ngram_keystrokes[-1]
                time_taken = curr_keystroke.get('time_since_previous', 0)
                all_correct = all(ks.get('is_correct', False) for ks in ngram_keystrokes)
                if all_correct and time_taken and time_taken > 0:
                    if time_taken > 5000:
                        continue
                    cursor.execute(f"""
                        INSERT INTO {self.SPEED_TABLE} 
                        (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, self.n, i, time_taken, ngram_text))
                if not curr_keystroke.get('is_correct', True):
                    cursor.execute(f"""
                        INSERT INTO {self.ERROR_TABLE} 
                        (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session_id, self.n, i, time_taken or 0, ngram_text))
            conn.commit()
            conn.close()
            return True
        except Exception as e:  # noqa: E722
            print(f"Error recording {self.n}-grams for session {session_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False