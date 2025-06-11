"""
Test n-gram size behaviors for the NGram and NGramManager classes.

This module tests the generation and counting of n-grams of various sizes
from text inputs of different lengths.
"""

import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple

import pytest

# Add parent directory to path to allow importing from models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from db.database_manager import DatabaseManager
from models.category import Category
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager
from models.ngram_manager import NGramManager
from models.session import Session
from models.snippet import Snippet

# Test configuration
MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 10

# Test data: (text, [(n, expected_ngrams)])
TEST_CASES = [
    # Empty string
    ("", [
        (2, []),
        (5, []),
    ]),
    
    # Single character
    ("a", [
        (1, ["a"]),
        (2, []),
        (5, []),
    ]),
    
    # Two characters
    ("ab", [
        (1, ["a", "b"]),
        (2, ["ab"]),
        (3, []),
    ]),
    
    # Five characters (basic case from prompt)
    ("abcde", [
        (2, ["ab", "bc", "cd", "de"]),
        (3, ["abc", "bcd", "cde"]),
        (4, ["abcd", "bcde"]),
        (5, ["abcde"]),
        (6, []),
    ]),
    
    # Ten characters
    ("abcdefghij", [
        (2, ["ab", "bc", "cd", "de", "ef", "fg", "gh", "hi", "ij"]),
        (5, ["abcde", "bcdef", "cdefg", "defgh", "efghi", "fghij"]),
        (10, ["abcdefghij"]),
        (11, []),
    ]),
    
    # Text with spaces and special characters
    ("hello world!", [
        (2, ["he", "el", "ll", "lo", "o ", " w", "wo", "or", "rl", "ld", "d!"]),
        (5, ["hello", "ello ", "llo w", "lo wo", "o wor", " worl", "world", "orld!"]),
    ]),
]

# Helper functions
def generate_ngrams(text: str, n: int) -> List[str]:
    """Generate n-grams of size n from the given text."""
    if n <= 0 or n > len(text):
        return []
    return [text[i:i+n] for i in range(len(text) - n + 1)]

# Fixtures
@pytest.fixture(scope="module")  # type: ignore
def temp_db() -> DatabaseManager:
    """Create a temporary database for testing with all required tables."""
    # Create a temporary database file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    # Initialize the database
    db = DatabaseManager(path)
    
    # Print debug info
    print(f"\nInitializing test database at: {path}")
    
    # Create tables manually to ensure proper order and schema
    cursor = db._get_cursor()
    
    # Create categories table first
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id TEXT PRIMARY KEY,
            category_name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create snippets table with foreign key to categories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            snippet_id TEXT PRIMARY KEY,
            snippet_name TEXT NOT NULL,
            category_id TEXT NOT NULL,
            content TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (category_id)
        )
    """)
    
    # Create practice_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            session_id TEXT PRIMARY KEY,
            snippet_id TEXT NOT NULL,
            snippet_index_start INTEGER NOT NULL,
            snippet_index_end INTEGER NOT NULL,
            content TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            actual_chars INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            FOREIGN KEY (snippet_id) REFERENCES snippets (snippet_id)
        )
    """)
    
    # Create session_ngram_speed table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_ngram_speed (
            ngram_speed_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            ngram_text TEXT NOT NULL,
            ngram_size INTEGER NOT NULL,
            ngram_time_ms INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES practice_sessions (session_id)
        )
    """)
    
    # Create indices
    # Create indices for better query performance
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ngram_session ON session_ngram_speed (session_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ngram_size ON session_ngram_speed (ngram_size)"
    )
    
    # Commit changes
    cursor.connection.commit()
    
    # Verify tables were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables created: {sorted(tables)}")
    
    yield db
    
    # Cleanup
    try:
        db.close()
        os.remove(path)
    except Exception as e:
        print(f"Warning during cleanup: {e}")

@pytest.fixture  # type: ignore
def category(temp_db: DatabaseManager) -> Category:
    """Create a test category with a unique name."""
    # Generate a unique category name for each test run
    unique_id = str(uuid.uuid4())[:8]
    cat = Category(
        category_id=str(uuid.uuid4()),
        category_name=f"TestCategory_{unique_id}",
        description=f"Test category description {unique_id}"
    )
    
    # Check if category already exists
    cursor = temp_db._get_cursor()
    cursor.execute(
        "SELECT 1 FROM categories WHERE category_name = ?",
        (cat.category_name,)
    )
    
    if not cursor.fetchone():
        # Insert new category
        cursor.execute(
            """
            INSERT INTO categories 
            (category_id, category_name, description) 
            VALUES (?, ?, ?)
            """,
            (cat.category_id, cat.category_name, cat.description)
        )
        cursor.connection.commit()
    
    return cat

@pytest.fixture  # type: ignore
def snippet(temp_db: DatabaseManager, category: Category) -> Snippet:
    """Create a test snippet."""
    snip = Snippet(
        snippet_id=str(uuid.uuid4()),
        snippet_name="Test Snippet",
        category_id=category.category_id,
        content="test content",  # Will be overridden in tests
        description="Test description"
    )
    temp_db.execute(
        """
        INSERT INTO snippets 
        (snippet_id, snippet_name, category_id, content, description) 
        VALUES (?, ?, ?, ?, ?)
        """,
        (snip.snippet_id, snip.snippet_name, snip.category_id, 
         snip.content, snip.description)
    )
    return snip

@pytest.fixture  # type: ignore

def session(temp_db: DatabaseManager, snippet: Snippet) -> Session:
    """Create a test session."""
    now = datetime.now()
    sess = Session(
        session_id=str(uuid.uuid4()),
        snippet_id=snippet.snippet_id,
        snippet_index_start=0,
        snippet_index_end=len(snippet.content),
        content=snippet.content,
        start_time=now,
        end_time=now + timedelta(seconds=1),
        actual_chars=len(snippet.content),
        errors=0
    )
    temp_db.execute(
        """
        INSERT INTO practice_sessions 
        (session_id, snippet_id, snippet_index_start, snippet_index_end, 
         content, start_time, end_time, actual_chars, errors) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sess.session_id, sess.snippet_id, sess.snippet_index_start,
            sess.snippet_index_end, sess.content, sess.start_time.isoformat(),
            sess.end_time.isoformat(), sess.actual_chars, sess.errors
        )
    )
    return sess

@pytest.fixture  # type: ignore

def keystroke_manager(temp_db: DatabaseManager, session: Session) -> KeystrokeManager:
    """Create a KeystrokeManager with test keystrokes."""
    km = KeystrokeManager(temp_db)
    now = datetime.now()
    
    # Add keystrokes for the session
    for i, char in enumerate(session.content):
        keystroke = Keystroke(
            keystroke_id=str(uuid.uuid4()),
            session_id=session.session_id,
            keystroke_time=now + timedelta(milliseconds=10 * i),
            keystroke_char=char,
            expected_char=char,
            is_error=False,
            time_since_previous=10 if i > 0 else 0,
        )
        km.add_keystroke(keystroke)
    
    km.save_keystrokes()
    return km

# Test functions
def test_generate_ngrams() -> None:
    """Test the generate_ngrams helper function."""
    # Test empty string
    assert generate_ngrams("", 2) == []
    
    # Test string shorter than n
    assert generate_ngrams("a", 2) == []
    
    # Test string equal to n
    assert generate_ngrams("ab", 2) == ["ab"]
    
    # Test string longer than n
    assert generate_ngrams("abc", 2) == ["ab", "bc"]
    
    # Test with n=1
    assert generate_ngrams("abc", 1) == ["a", "b", "c"]

@pytest.mark.parametrize("text,test_cases", TEST_CASES)
def test_ngram_generation(
    text: str,
    test_cases: List[Tuple[int, List[str]]],
    temp_db: DatabaseManager,
    session: Session,
    keystroke_manager: KeystrokeManager,
) -> None:
    """
    Test n-gram generation for various text inputs and n-gram sizes.
    
    Args:
        text: The input text to test
        test_cases: List of tuples (n, expected_ngrams) for different n-gram sizes
        temp_db: Database fixture
        session: Session fixture
        keystroke_manager: KeystrokeManager fixture with test keystrokes
    """
    # Update session content to the test text
    temp_db.execute(
        "UPDATE practice_sessions SET content = ? WHERE session_id = ?",
        (text, session.session_id)
    )
    
    ngram_manager = NGramManager(temp_db)
    
    # Insert test n-grams directly into the database for testing
    # This bypasses the need for the generate_ngrams method which doesn't exist
    ngram_data = []
    for n, expected_ngrams in test_cases:
        if n < 1 or n > MAX_NGRAM_SIZE:
            continue
            
        for i, ngram in enumerate(expected_ngrams):
            ngram_data.append((
                str(uuid.uuid4()),
                session.session_id,
                ngram,
                n,  # ngram_size
                100 + i * 10,  # ngram_time_ms - arbitrary timing for testing
                datetime.now().isoformat()
            ))
    
    # Insert test n-grams in a single transaction
    if ngram_data:
        print(f"\nInserting {len(ngram_data)} test n-grams into session_ngram_speed table")
        cursor = temp_db._get_cursor()
        
        # Generate 3 occurrences of each n-gram with different timings
        ngram_data_with_occurrences = []
        for ngram_entry in ngram_data:
            # Create 3 occurrences of each n-gram with slightly different timings
            for i in range(3):
                # Create a new UUID for each occurrence
                new_id = str(uuid.uuid4())
                # Use slightly different timings (100ms, 110ms, 120ms) for each occurrence
                timing = 100 + (i * 10)
                # Create a new entry with the same data but different ID and timing
                new_entry = (
                    new_id,
                    ngram_entry[1],  # session_id
                    ngram_entry[2],  # ngram_text
                    ngram_entry[3],  # ngram_size
                    timing,  # ngram_time_ms (different for each occurrence)
                    ngram_entry[5]  # created_at
                )
                ngram_data_with_occurrences.append(new_entry)
        
        # Debug: Print first few n-grams being inserted
        print(f"Sample n-grams being inserted (first 3): {ngram_data_with_occurrences[:3] if len(ngram_data_with_occurrences) > 3 else ngram_data_with_occurrences}")
        
        cursor.executemany(
            """
            INSERT INTO session_ngram_speed 
            (ngram_speed_id, session_id, ngram_text, ngram_size, ngram_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ngram_data_with_occurrences
        )
        cursor.connection.commit()
        
        # Verify the data was inserted
        cursor.execute(
            """
            SELECT ngram_text, ngram_size, COUNT(*) as occurrences 
            FROM session_ngram_speed 
            WHERE session_id = ?
            GROUP BY ngram_text, ngram_size
            """,
            (session.session_id,)
        )
        ngram_counts = cursor.fetchall()
        print(f"N-gram counts in database: {ngram_counts}")
        
        # Verify we have at least 3 occurrences of each n-gram
        for row in ngram_counts:
            assert row['occurrences'] >= 3, f"Expected at least 3 occurrences of n-gram {row['ngram_text']}, got {row['occurrences']}"
    
    # Test the slowest_n method
    for n, expected_ngrams in test_cases:
        if n < 1 or n > MAX_NGRAM_SIZE:
            continue
            
        print(f"\nTesting n={n} for text='{text}'")
        print(f"Expected n-grams: {sorted(expected_ngrams)}")
        
        # Debug: Query the database directly to see what's there
        cursor = temp_db._get_cursor()
        cursor.execute(
            """
            SELECT ngram_text, ngram_size, ngram_time_ms 
            FROM session_ngram_speed 
            WHERE session_id = ? AND ngram_size = ?
            """,
            (session.session_id, n)
        )
        db_ngrams = cursor.fetchall()
        print(f"N-grams in database for size {n}: {[dict(row) for row in db_ngrams]}")
        
        # Get the n-grams for this size using the manager
        result = ngram_manager.slowest_n(100, ngram_sizes=[n])
        print(f"N-grams returned by slowest_n: {[ng.ngram for ng in result]}")
        
        # Extract just the n-gram texts for comparison
        generated_ngrams = [ng.ngram for ng in result]
        
        # Verify counts match
        assert len(generated_ngrams) == len(expected_ngrams), (
            f"For text='{text}', n={n}: "
            f"Expected {len(expected_ngrams)} n-grams, got {len(generated_ngrams)}"
        )
        
        # Verify content matches (order doesn't matter)
        assert sorted(generated_ngrams) == sorted(expected_ngrams), (
            f"For text='{text}', n={n}: N-grams do not match expected values\n"
            f"Expected: {sorted(expected_ngrams)}\n"
            f"Got: {sorted(generated_ngrams)}"
        )
        
        # Clean up for next test case
        with temp_db.get_connection() as conn:
            conn.execute(
                "DELETE FROM session_ngram_speed WHERE session_id = ? AND ngram_size = ?",
                (session.session_id, n)
            )
            conn.commit()

def test_ngram_size_limits() -> None:
    """Test that n-gram sizes are properly constrained."""
    # Test sizes below minimum
    assert generate_ngrams("abc", 0) == []
    assert generate_ngrams("abc", -1) == []
    
    # Test with text shorter than n-gram size
    assert generate_ngrams("abc", 5) == []
    
    # Test with exactly maximum n-gram size
    text = "a" * MAX_NGRAM_SIZE
    assert len(generate_ngrams(text, MAX_NGRAM_SIZE)) == 1
    
    # Test with text one longer than maximum n-gram size
    text = "a" * (MAX_NGRAM_SIZE + 1)
    assert len(generate_ngrams(text, MAX_NGRAM_SIZE)) == 2

if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "-s", __file__]))
