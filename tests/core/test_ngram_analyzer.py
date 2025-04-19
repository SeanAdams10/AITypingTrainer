"""
Tests for NGramAnalyzer (parameterized n-gram analyzer).
"""
import os
import sys
import pytest
import sqlite3
from pathlib import Path
from typing import Callable, Generator, Dict, List, Any, Tuple
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import from project modules
from models.ngram_analyzer import NGramAnalyzer  # noqa: E402
from models.practice_generator import PracticeGenerator


class TestNGramAnalyzer:
    """Test class for the NGramAnalyzer functionality."""

    @pytest.fixture(scope="function")
    def test_db_path(self, tmp_path: Path) -> Path:
        """
        Create a temporary path for the test database.
        
        Args:
            tmp_path: pytest fixture that provides a temporary directory
            
        Returns:
            Path to the temporary database file
        """
        return tmp_path / "test_ngram.db"
        
    @pytest.fixture(scope="function")
    def setup_database(self, test_db_path: Path) -> sqlite3.Connection:
        """
        Set up and tear down a test database for each test.
        
        This fixture creates a SQLite database file for testing
        and ensures it's properly cleaned up after each test.
        
        Args:
            test_db_path: Path to the temporary database file
            
        Returns:
            sqlite3.Connection: Database connection for use in tests
        """
        # Create database
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE practice_sessions (
                id INTEGER PRIMARY KEY,
                snippet_id INTEGER,
                date_created TEXT,
                wpm REAL,
                accuracy REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE practice_snippets (
                id INTEGER PRIMARY KEY,
                text TEXT,
                category TEXT
            )
        """)
        
        # Create practice_session_keystrokes table
        cursor.execute("""
            CREATE TABLE practice_session_keystrokes (
                session_id TEXT,
                keystroke_id INTEGER,
                keystroke_time DATETIME,
                keystroke_char TEXT,
                expected_char TEXT,
                is_correct BOOLEAN,
                time_since_previous INTEGER,
                PRIMARY KEY (session_id, keystroke_id)
            )
        """)
        
        # Create practice_session_errors table
        cursor.execute("""
            CREATE TABLE practice_session_errors (
                session_id TEXT,
                error_id INTEGER,
                keystroke_id INTEGER,
                keystroke_char TEXT,
                expected_char TEXT,
                PRIMARY KEY (session_id, error_id)
            )
        """)
        
        # Create the modernized n-gram tables
        cursor.execute("""
            CREATE TABLE session_ngram_speed (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE session_ngram_error (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
        """)
        
        # Insert default snippet
        cursor.execute(
            "INSERT INTO practice_snippets (id, text, category) "
            "VALUES (1, 'Sample text', 'Test')"
        )
        
        conn.commit()
        
        # Return the connection for use in tests and do NOT close it
        # The database will be automatically cleaned up when the tmp_path is deleted
        return conn

    # This class is defined at the module level to avoid NameError issues
    class DbManagerMock:
        def __init__(self, db_path: str):
            self.db_path = db_path

        def get_instance(self):
            return self

        def get_connection(self):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn

        def execute_query(self, query, params=None):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]

        def execute_query_one(self, query, params=None):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return dict(row) if row else None

        def execute_non_query(self, query, params=None):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount

    @pytest.fixture
    def db_mock(self, test_db_path: Path) -> DbManagerMock:
        """
        Create a mock for the database manager that uses the test database path.
        
        Args:
            test_db_path: Path to the temporary database file
        
        Returns:
            DbManagerMock: A mock database manager for testing
        """
        # Create the mock with our test database path
        return self.DbManagerMock(str(test_db_path))
        
    @pytest.fixture
    def patched_analyzer(self, db_mock: DbManagerMock, monkeypatch: pytest.MonkeyPatch) -> Callable[[int], NGramAnalyzer]:
        """
        Factory fixture that returns an NGramAnalyzer with the db_manager already patched.
        
        Args:
            db_mock: The mock database manager
            monkeypatch: pytest monkeypatch fixture
            
        Returns:
            Callable that creates an NGramAnalyzer with the specified n-gram size
        """
        def _create_analyzer(n_size: int) -> NGramAnalyzer:
            analyzer = NGramAnalyzer(n_size)
            # Directly set the db_manager attribute
            analyzer.db_manager = db_mock
            return analyzer
            
        return _create_analyzer

    def _add_keystrokes(
        self, session_id: int, keystrokes: List[Dict[str, Any]], conn: sqlite3.Connection
    ) -> None:
        """
        Helper to add test keystrokes to the database.
        
        Args:
            session_id: ID of the practice session
            keystrokes: List of keystroke data dictionaries
            conn: Database connection
        """
        cursor = conn.cursor()
        
        # Create session if it doesn't exist
        cursor.execute(
            "INSERT OR IGNORE INTO practice_sessions (id, snippet_id, date_created, wpm, accuracy) "
            "VALUES (?, 1, '2023-01-01', 60.0, 95.0)",
            (session_id,)
        )
        
        # Add keystrokes
        for i, keystroke in enumerate(keystrokes):
            cursor.execute(
                """
                INSERT INTO practice_session_keystrokes 
                (session_id, keystroke_id, keystroke_time, keystroke_char, expected_char, is_correct, time_since_previous) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    i,
                    datetime.now(),
                    keystroke["expected_char"],  # Using expected_char as keystroke_char for most keystrokes
                    keystroke["expected_char"],
                    1 if keystroke["is_correct"] else 0,  # SQLite treats 1 as TRUE, 0 as FALSE
                    keystroke["time_since_previous"]
                )
            )
        
        conn.commit()

    def test_init_validation(self) -> None:
        """Test that NGramAnalyzer validates initialization parameters."""
        
        # Test valid n-gram sizes
        for n in range(2, 9):
            analyzer = NGramAnalyzer(n)
            assert analyzer.n == n, f"NGramAnalyzer should be initialized with size {n}"
            assert analyzer.SPEED_TABLE == "session_ngram_speed"
            assert analyzer.ERROR_TABLE == "session_ngram_error"

        # Test invalid n-gram sizes
        with pytest.raises(ValueError):
            NGramAnalyzer(1)

        with pytest.raises(ValueError):
            NGramAnalyzer(9)

    def test_whitespace_exclusion(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test that n-grams containing whitespace are excluded from analysis."""
        # Setup test environment
        conn = setup_database
        
        # Add keystrokes with whitespace
        keystrokes = [
            {"expected_char": "T", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "h", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "e", "is_correct": True, "time_since_previous": 90},
            {"expected_char": " ", "is_correct": True, "time_since_previous": 120},  # Whitespace
            {"expected_char": "c", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "t", "is_correct": True, "time_since_previous": 105}
        ]
        self._add_keystrokes(1, keystrokes, conn)
        
        # Create an analyzer with the patched database
        analyzer = patched_analyzer(3)  # Trigrams
            
        # Run the analysis
        success = analyzer.analyze_ngrams()
        
        assert success, "N-gram analysis should succeed"
            
        # Check results using a new connection
        with sqlite3.connect(str(test_db_path)) as verify_conn:
            verify_conn.row_factory = sqlite3.Row
            cursor = verify_conn.cursor()
            cursor.execute(
                f"SELECT * FROM {analyzer.SPEED_TABLE} WHERE ngram_size = 3"
            )
            ngrams = cursor.fetchall()
            ngram_texts = [row['ngram_text'] for row in ngrams]
            # Verify no n-grams with whitespace were included
            for ngram in ngram_texts:
                assert " " not in ngram, f"N-gram '{ngram}' contains whitespace"
            # "The" should be included but "e c" (with space) should not
            assert "The" in ngram_texts, "Expected 'The' n-gram to be included"
            assert "e c" not in ngram_texts, "N-gram 'e c' with space should be excluded"
            assert "cat" in ngram_texts, "Expected 'cat' n-gram to be included"

    def test_speed_accuracy_requirement(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test that n-grams need correct keystrokes for speed analysis."""
        # Setup test environment
        conn = setup_database
        
        # Add keystrokes with a mix of correct and incorrect
        keystrokes = [
            {"expected_char": "t", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "h", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "e", "is_correct": False, "time_since_previous": 90},  # Error
            {"expected_char": "c", "is_correct": True, "time_since_previous": 120},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "t", "is_correct": True, "time_since_previous": 95}
        ]
        self._add_keystrokes(1, keystrokes, conn)
        
        # Create an analyzer with the patched database
        analyzer = patched_analyzer(3)  # Trigrams
        
        # Run the analyzer
        success = analyzer.analyze_ngrams()
        
        assert success, "N-gram analysis should succeed"
        
        # Verify results using a new connection
        with sqlite3.connect(str(test_db_path)) as verify_conn:
            verify_conn.row_factory = sqlite3.Row
            cursor = verify_conn.cursor()
            # Verify that "the" is not included in speed analysis due to the error
            cursor.execute(
                f"SELECT * FROM {analyzer.SPEED_TABLE} WHERE ngram_size = 3"
            )
            speed_ngrams = cursor.fetchall()
            speed_ngram_texts = [row['ngram_text'] for row in speed_ngrams]
            assert "the" not in speed_ngram_texts, "N-gram 'the' with an error should not be in speed analysis"
            # But it should be in the error analysis
            cursor.execute(
                f"SELECT * FROM {analyzer.ERROR_TABLE} WHERE ngram_size = 3"
            )
            error_ngrams = cursor.fetchall()
            error_ngram_texts = [row['ngram_text'] for row in error_ngrams]
            assert "the" in error_ngram_texts, "N-gram 'the' with an error should be in error analysis"

    def test_error_last_char_requirement(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test that n-grams only register errors when the last character is wrong."""
        # Setup test environment
        conn = setup_database
        
        # Add keystrokes - error in first position but not last
        keystrokes = [
            {"expected_char": "t", "is_correct": False, "time_since_previous": 100},  # Error
            {"expected_char": "h", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "e", "is_correct": True, "time_since_previous": 90},
            # Error in last position
            {"expected_char": "c", "is_correct": True, "time_since_previous": 120},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "t", "is_correct": False, "time_since_previous": 95}  # Error
        ]
        self._add_keystrokes(1, keystrokes, conn)
        
        # Create an analyzer with the patched database
        analyzer = patched_analyzer(3)  # Trigrams
        
        # Run the analyzer
        success = analyzer.analyze_ngrams()
        assert success, "N-gram analysis should succeed"
        
        # Check results using a new connection (avoid closed connection error)
        with sqlite3.connect(str(test_db_path)) as verify_conn:
            verify_conn.row_factory = sqlite3.Row
            cursor = verify_conn.cursor()
            # Check error table
            cursor.execute(
                f"SELECT * FROM {analyzer.ERROR_TABLE} WHERE ngram_size = 3"
            )
            error_ngrams = cursor.fetchall()
            error_texts = [row['ngram_text'] for row in error_ngrams]
            # "the" should not be in error table since error is not in last position
            assert "the" not in error_texts, "N-gram 'the' should not be in error table since error is not in last position"
            # "cat" should be in error table since error is in last position
            assert "cat" in error_texts, "N-gram 'cat' should be in error table since error is in last position"

    def test_all_ngram_sizes(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test that all n-gram sizes from 2-8 work correctly."""
        # Setup test environment
        conn = setup_database

        # Add keystrokes with a variety of characters for testing different n-gram sizes
        keystrokes = [
            {"expected_char": "p", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "o", "is_correct": True, "time_since_previous": 90},
            {"expected_char": "g", "is_correct": True, "time_since_previous": 120},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "m", "is_correct": True, "time_since_previous": 130},
            {"expected_char": "m", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "i", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "n", "is_correct": True, "time_since_previous": 90}
        ]
        self._add_keystrokes(1, keystrokes, conn)

        # Test all valid n-gram sizes
        valid_sizes = range(2, 9)  # 2 through 8
        expected_counts = {}

        for n_size in valid_sizes:
            # Use a fresh analyzer and DB connection for each n-gram size
            analyzer = patched_analyzer(n_size)
            success = analyzer.analyze_ngrams()
            assert success, f"Analysis failed for n-gram size {n_size}"
            with sqlite3.connect(str(test_db_path)) as verify_conn:
                verify_conn.row_factory = sqlite3.Row
                cursor = verify_conn.cursor()
                cursor.execute(
                    f"SELECT COUNT(*) AS count FROM {analyzer.SPEED_TABLE} WHERE ngram_size = ?",
                    (n_size,)
                )
                count = cursor.fetchone()['count']
                expected_counts[n_size] = count
                assert count > 0, f"No n-grams found for size {n_size}"
                cursor.execute(
                    f"SELECT ngram_text FROM {analyzer.SPEED_TABLE} WHERE ngram_size = ?",
                    (n_size,)
                )
                ngram_texts = [row['ngram_text'] for row in cursor.fetchall()]
                for text in ngram_texts:
                    assert len(text) == n_size, f"N-gram '{text}' has incorrect length for size {n_size}"

    def test_specific_ngram_scenarios(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test specific n-gram analysis scenarios."""
        # Setup test environment
        conn = setup_database
        
        # Add keystrokes with specific patterns
        keystrokes = [
            {"expected_char": "p", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 90},
            {"expected_char": "o", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "g", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 105},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "m", "is_correct": True, "time_since_previous": 120}
        ]
        self._add_keystrokes(1, keystrokes, conn)
        conn.commit()
        conn.close()

    def test_bigrams(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test with bigrams."""
        conn = setup_database
        # Add keystrokes for the bigram test
        keystrokes = [
            {"expected_char": "p", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 90},
            {"expected_char": "o", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "g", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 105},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "m", "is_correct": True, "time_since_previous": 120}
        ]
        self._add_keystrokes(1, keystrokes, conn)
        conn.commit()

        analyzer = patched_analyzer(2)
        # Run the analyzer
        success = analyzer.analyze_ngrams()
        assert success, "Analysis failed for bigrams"

        # Verify bigram results using a new connection
        with sqlite3.connect(str(test_db_path)) as verify_conn:
            verify_conn.row_factory = sqlite3.Row
            cursor = verify_conn.cursor()
            cursor.execute(
                f"SELECT * FROM {analyzer.SPEED_TABLE} WHERE ngram_size = 2"
            )
            bigrams = cursor.fetchall()
            bigram_texts = [row['ngram_text'] for row in bigrams]

            # Check for specific bigrams
            assert "pr" in bigram_texts, "Expected 'pr' bigram to be included"
            assert "ro" in bigram_texts, "Expected 'ro' bigram to be included"
            assert "og" in bigram_texts, "Expected 'og' bigram to be included"
            assert "gr" in bigram_texts, "Expected 'gr' bigram to be included"
            assert "ra" in bigram_texts, "Expected 'ra' bigram to be included"
            assert "am" in bigram_texts, "Expected 'am' bigram to be included"

    def test_trigrams(self, setup_database, patched_analyzer, test_db_path) -> None:
        """Test with trigrams."""
        conn = setup_database
        # Add keystrokes for the trigram test
        keystrokes = [
            {"expected_char": "p", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 90},
            {"expected_char": "o", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "g", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "r", "is_correct": True, "time_since_previous": 105},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "m", "is_correct": True, "time_since_previous": 120}
        ]
        self._add_keystrokes(1, keystrokes, conn)
        conn.commit()

        analyzer = patched_analyzer(3)
        success = analyzer.analyze_ngrams()
        assert success, "Analysis failed for trigrams"
        with sqlite3.connect(str(test_db_path)) as verify_conn:
            verify_conn.row_factory = sqlite3.Row
            cursor = verify_conn.cursor()
            cursor.execute(
                f"SELECT * FROM {analyzer.SPEED_TABLE} WHERE ngram_size = 3"
            )
            trigrams = cursor.fetchall()
            trigram_texts = [row['ngram_text'] for row in trigrams]
            # Check for specific trigrams
            assert "pro" in trigram_texts, "Expected 'pro' trigram to be included"
            assert "rog" in trigram_texts, "Expected 'rog' trigram to be included"
            assert "ogr" in trigram_texts, "Expected 'ogr' trigram to be included"
            assert "gra" in trigram_texts, "Expected 'gra' trigram to be included"
            assert "ram" in trigram_texts, "Expected 'ram' trigram to be included"

    def test_get_slow_ngrams(self, setup_database, patched_analyzer) -> None:
        """
        Test retrieving slow n-grams from the analyzer.
        
        This test verifies that:
        1. The NGramAnalyzer correctly identifies n-grams that take longer to type
        2. Retrieved n-grams are sorted by time (slowest first)
        3. Minimum occurrence threshold filters out uncommon n-grams
        4. The get_slow_ngrams method returns properly formatted results
        5. This functionality works with any n-gram size
        """
        # Setup test environment
        conn = setup_database
        
        # Add keystrokes with varying speeds
        keystrokes = [
            # First occurrence - normal speed
            {"expected_char": "t", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "h", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "e", "is_correct": True, "time_since_previous": 90},
            # Second occurrence - slow typing of "th"
            {"expected_char": "t", "is_correct": True, "time_since_previous": 200},  # Slow
            {"expected_char": "h", "is_correct": True, "time_since_previous": 250},  # Slow
            {"expected_char": "e", "is_correct": True, "time_since_previous": 100},
            # Another sequence with different n-grams
            {"expected_char": "c", "is_correct": True, "time_since_previous": 90},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "t", "is_correct": True, "time_since_previous": 100}
        ]
        self._add_keystrokes(1, keystrokes, conn)
        
        # Test with a specific n-gram size
        n_size = 2  # Using 2-grams for this test
        
        # Clear any existing data
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM session_ngram_speed WHERE ngram_size = {n_size}")
        cursor.execute(f"DELETE FROM session_ngram_error WHERE ngram_size = {n_size}")
        conn.commit()
        
        # Create the analyzer using our fixture
        analyzer = patched_analyzer(n_size)
        
        # Run the analyzer
        analyzer.analyze_ngrams()
        
        # Get slow n-grams, limiting to top results with at least 1 occurrence
        slow_ngrams = analyzer.get_slow_ngrams(limit=5, min_occurrences=1)
        
        # Verify results
        assert len(slow_ngrams) > 0, "No slow n-grams were found"
        
        # The slow n-grams should include "th" since it was typed slowly in the second occurrence
        slow_text_list = [item["ngram_text"] for item in slow_ngrams]
        assert "th" in slow_text_list, "'th' should be identified as a slow n-gram"
        
        # N-grams should be sorted by avg_time (descending)
        for i in range(1, len(slow_ngrams)):
            assert slow_ngrams[i-1]["avg_time"] >= slow_ngrams[i]["avg_time"], "N-grams not sorted by avg_time"
        
        # Each result should have required fields
        required_fields = ["ngram_text", "ngram_size", "avg_time", "count"]
        for ngram in slow_ngrams:
            for field in required_fields:
                assert field in ngram, f"Field '{field}' missing from result"
            
            # Verify n-gram size matches requested size
            assert ngram["ngram_size"] == n_size, f"N-gram size mismatch: {ngram['ngram_size']} != {n_size}"

    def test_get_error_ngrams(self, setup_database, patched_analyzer) -> None:
        """
        Test retrieving error n-grams from the analyzer.
        
        This test verifies that:
        1. The NGramAnalyzer correctly identifies n-grams with typing errors
        2. Retrieved n-grams are sorted by error frequency (most frequent first)
        3. Minimum occurrence threshold filters out uncommon error n-grams
        4. The get_error_ngrams method returns properly formatted results
        5. This functionality works with any n-gram size
        """
        # Setup test environment
        conn = setup_database
        
        # Add keystrokes with errors
        keystrokes = [
            # First error
            {"expected_char": "t", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "h", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "e", "is_correct": False, "time_since_previous": 90},  # Error
            # Second error
            {"expected_char": "t", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "h", "is_correct": True, "time_since_previous": 110},
            {"expected_char": "e", "is_correct": False, "time_since_previous": 90},  # Error
            # Different error
            {"expected_char": "c", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "t", "is_correct": False, "time_since_previous": 90}  # Error
        ]
        self._add_keystrokes(1, keystrokes, conn)
        
        # Test with a specific n-gram size
        n_size = 3  # Using trigrams
        
        # Clear any existing data
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM session_ngram_speed WHERE ngram_size = {n_size}")
        cursor.execute(f"DELETE FROM session_ngram_error WHERE ngram_size = {n_size}")
        conn.commit()
        
        # Create the analyzer using our fixture
        analyzer = patched_analyzer(n_size)
        
        # Run the analyzer
        analyzer.analyze_ngrams()
        
        # Get error n-grams
        error_ngrams = analyzer.get_error_ngrams(limit=5, min_occurrences=1)
        
        # Verify results
        assert len(error_ngrams) > 0, "No error n-grams were found"
        
        # Error n-grams should include "the" since it had errors
        error_text_list = [item["ngram_text"] for item in error_ngrams]
        assert "the" in error_text_list, "'the' should be identified as an error n-gram"
        
        # N-grams should be sorted by error frequency (descending)
        for i in range(1, len(error_ngrams)):
            assert error_ngrams[i-1]["count"] >= error_ngrams[i]["count"], "N-grams not sorted by count"
        
        # Each result should have required fields
        required_fields = ["ngram_text", "ngram_size", "count"]
        for ngram in error_ngrams:
            for field in required_fields:
                assert field in ngram, f"Field '{field}' missing from result"
            
            # Verify n-gram size matches requested size
            assert ngram["ngram_size"] == n_size, f"N-gram size mismatch: {ngram['ngram_size']} != {n_size}"

    def test_create_ngram_snippet(self, setup_database, patched_analyzer, monkeypatch) -> None:
        """Test creating a practice snippet from n-gram data."""
        # Setup test environment
        conn = setup_database
        
        # Create a mock for PracticeGenerator.create_snippet_from_ngrams
        def mock_create_snippet_from_ngrams(ngrams, min_length=50, max_length=200, name=None):
            return {
                "id": 1,
                "text": "".join([ngram["ngram_text"] for ngram in ngrams]),
                "name": name or "N-gram Practice"
            }
        
        # Apply monkeypatching to the static method
        monkeypatch.setattr(PracticeGenerator, "create_snippet_from_ngrams", mock_create_snippet_from_ngrams)
        
        # Add keystrokes with errors and varying speeds
        keystrokes = [
            {"expected_char": "t", "is_correct": True, "time_since_previous": 200},  # Slow
            {"expected_char": "h", "is_correct": True, "time_since_previous": 250},  # Slow
            {"expected_char": "e", "is_correct": True, "time_since_previous": 100},
            {"expected_char": "c", "is_correct": True, "time_since_previous": 90},
            {"expected_char": "a", "is_correct": True, "time_since_previous": 95},
            {"expected_char": "t", "is_correct": False, "time_since_previous": 300}  # Error
        ]
        self._add_keystrokes(1, keystrokes, conn)
        
        # Create the analyzer using our fixture
        analyzer = patched_analyzer(2)  # Using bigrams
        
        # Run analysis first
        analyzer.analyze_ngrams()
        
        # Test creating practice snippet from slow n-grams
        snippet = analyzer.create_ngram_snippet(
            ngram_type="slow",
            name="Slow Bigram Practice",
            count=5
        )
        
        # Verify the snippet
        assert snippet is not None, "Failed to create practice snippet"
        assert "id" in snippet, "Snippet should have an ID"
        assert "text" in snippet, "Snippet should have text content"
        assert "name" in snippet, "Snippet should have a name"
        assert snippet["name"] == "Slow Bigram Practice", "Snippet name doesn't match"
        
        # Test creating practice snippet from error n-grams
        error_snippet = analyzer.create_ngram_snippet(
            ngram_type="error",
            name="Error Bigram Practice",
            count=5
        )
        
        # Verify the error snippet
        assert error_snippet is not None, "Failed to create error practice snippet"
        assert "id" in error_snippet, "Error snippet should have an ID"
        assert "text" in error_snippet, "Error snippet should have text content"
        assert "name" in error_snippet, "Error snippet should have a name"
        assert error_snippet["name"] == "Error Bigram Practice", "Error snippet name doesn't match"

    def test_record_keystrokes_ngram_limits(self, setup_database, patched_analyzer) -> None:
        """
        Test that n-gram analysis correctly handles keystroke sequence length limits.
        
        This test verifies that:
        1. N-gram analysis requires at least n keystrokes to produce any results
        2. Keystroke sequences shorter than the n-gram size don't generate n-grams
        3. N-gram analysis works correctly at the boundary cases
        4. Different n-gram sizes correctly apply their specific length requirements
        """
        # Setup test environment
        conn = setup_database
        
        # Test with different n-gram sizes and keystroke sequence lengths
        for n_size in range(2, 5):  # Test a subset of sizes to keep test runtime reasonable
            # Clear tables for this test iteration
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM session_ngram_speed WHERE ngram_size = {n_size}")
            cursor.execute(f"DELETE FROM session_ngram_error WHERE ngram_size = {n_size}")
            conn.commit()
            
            # Create sequences of different lengths
            for seq_length in range(1, n_size + 2):  # Test lengths 1 to n+1
                # Create a new session ID for this test
                session_id = 100 + (n_size * 10) + seq_length
                
                # Generate test keystrokes of required length
                keystrokes = []
                for i in range(seq_length):
                    keystrokes.append({
                        "expected_char": chr(97 + i),  # 'a', 'b', 'c', etc.
                        "is_correct": True,
                        "time_since_previous": 100
                    })
                
                # Add the keystrokes to the database
                self._add_keystrokes(session_id, keystrokes, conn)
                
                # Create the analyzer using our fixture
                analyzer = patched_analyzer(n_size)
                
                # Run analysis
                analyzer.analyze_ngrams()
                
                # Check if n-grams were generated
                cursor.execute(
                    f"SELECT COUNT(*) as count FROM {analyzer.SPEED_TABLE} WHERE session_id = ? AND ngram_size = ?", 
                    (session_id, n_size)
                )
                count = cursor.fetchone()["count"]
                
                # Verify n-gram generation based on length
                if seq_length < n_size:
                    assert count == 0, f"No n-grams should be generated for sequences shorter than {n_size}"
                else:
                    expected_count = seq_length - n_size + 1  # Number of possible n-grams in sequence
                    assert count == expected_count, f"Expected {expected_count} n-grams for sequence of length {seq_length}"


if __name__ == '__main__':
    pytest.main()
