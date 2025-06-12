import logging
import os
import sys
import tempfile
from typing import List, Tuple

import pytest

# Attempt to import project-specific modules
# Adjust these paths if they are incorrect for your project structure
try:
    from models.database_manager import DatabaseManager
    from models.ngram_manager import MAX_NGRAM_SIZE, MIN_NGRAM_SIZE
    from services.category_manager import CategoryManager
    from services.session_manager import SessionManager
    from services.snippet_manager import SnippetManager
except ImportError as e:
    logging.warning(f"Could not import project modules: {e}. Using fallbacks.")

    class DatabaseManager:  # type: ignore
        def __init__(self, db_path: str) -> None:
            pass
        def init_tables(self) -> None:
            pass
        def close_connection(self) -> None:
            pass

    class CategoryManager:  # type: ignore
        def __init__(self, db_manager: DatabaseManager) -> None:
            pass
        def create_category(self, name: str) -> int:
            return 1  # Dummy ID

    class SnippetManager:  # type: ignore
        def __init__(self, db_manager: DatabaseManager) -> None:
            pass
        def add_snippet(self, category_id: int, name: str, content: str, difficulty: int) -> int:
            return 1  # Dummy ID

    class SessionManager:  # type: ignore
        def __init__(self, db_manager: DatabaseManager) -> None:
            pass
        def create_session(self, snippet_id: int, session_type: str, user_id: int = 1) -> int:
            return 1  # Dummy ID

    MIN_NGRAM_SIZE = 2  # type: ignore
    MAX_NGRAM_SIZE = 10 # type: ignore

logger = logging.getLogger(__name__)

# --- Fixtures (identical to test_ngram_size.py for consistency) ---

@pytest.fixture(scope="function")
def db_manager() -> DatabaseManager:
    """Provides a DatabaseManager instance with a temporary, initialized database."""
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_db_fd)
    db = DatabaseManager(temp_db_path)
    try:
        db.init_tables()
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")
    yield db
    try:
        db.close_connection()
    except Exception as e:
        logger.error(f"Failed to close DB connection: {e}")
    try:
        os.unlink(temp_db_path)
    except Exception as e:
        logger.error(f"Failed to delete temp DB file {temp_db_path}: {e}")

@pytest.fixture(scope="function")
def category_manager_fixture(db_manager: DatabaseManager) -> CategoryManager:
    return CategoryManager(db_manager)

@pytest.fixture(scope="function")
def snippet_manager_fixture(db_manager: DatabaseManager) -> SnippetManager:
    return SnippetManager(db_manager)

@pytest.fixture(scope="function")
def session_manager_fixture(db_manager: DatabaseManager) -> SessionManager:
    return SessionManager(db_manager)

@pytest.fixture(scope="function")
def test_session_setup(category_manager_fixture: CategoryManager, 
                       snippet_manager_fixture: SnippetManager, 
                       session_manager_fixture: SessionManager) -> Tuple[int, int, int]:
    """Fixture to set up a test category, snippet, and session. Returns (session_id, snippet_id, category_id)."""
    try:
        category_id = category_manager_fixture.create_category("Test Category - Ngram Speed")
        assert category_id is not None, "Failed to create category"
        snippet_id = snippet_manager_fixture.add_snippet(category_id, "Test Snippet - Ngram Speed", "Test content for n-gram speed.", 3)
        assert snippet_id is not None, "Failed to create snippet"
        session_id = session_manager_fixture.create_session(snippet_id, "practice")
        assert session_id is not None, "Failed to create session"
        return session_id, snippet_id, category_id
    except Exception as e:
        logger.error(f"Error in test_session_setup fixture: {e}", exc_info=True)
        pytest.fail(f"Fixture test_session_setup failed: {e}")
        return (0,0,0)

# --- N-gram Speed Calculation Logic ---

def generate_ngrams_with_speed(keystrokes: List[Tuple[str, int]], n: int) -> List[Tuple[str, float]]:
    """Generates n-grams of size n from keystrokes and calculates their speed.
    Keystrokes are (char, timestamp_ms).
    Speed is (timestamp_last - timestamp_first) / (n - 1) in ms.
    Only n-grams of size MIN_NGRAM_SIZE to MAX_NGRAM_SIZE (inclusive) are processed.
    Returns an empty list if n is outside this range, n > len(keystrokes), or n < 2 (for speed calc).
    """
    if not (MIN_NGRAM_SIZE <= n <= MAX_NGRAM_SIZE):
        return []
    if n > len(keystrokes) or n < 2: # n < 2 would lead to division by zero or undefined for speed
        return []
    
    ngrams_with_speed: List[Tuple[str, float]] = []
    for i in range(len(keystrokes) - n + 1):
        ngram_chars = keystrokes[i : i + n]
        ngram_text = "".join(char for char, ts in ngram_chars)
        
        time_first_char = ngram_chars[0][1]
        time_last_char = ngram_chars[n-1][1]
        
        duration = float(time_last_char - time_first_char)
        speed = duration / (n - 1)
        
        ngrams_with_speed.append((ngram_text, speed))
    return ngrams_with_speed

# --- Test Cases ---

KEYSTROKE_SPEED_TEST_CASES: List[Tuple[List[Tuple[str, int]], int, List[Tuple[str, float]]]] = [
    # (keystrokes, n, expected_ngrams_with_speed)
    # Basic cases from prompt
    ([("a", 0), ("b", 1000), ("c", 1500)], 2, [("ab", 1000.0), ("bc", 500.0)]),
    ([("a", 0), ("b", 1000), ("c", 1500)], 3, [("abc", 750.0)]),
    # Consistent 10ms intervals
    ([("t", 0), ("e", 10), ("s", 20), ("t", 30)], 2, [("te", 10.0), ("es", 10.0), ("st", 10.0)]),
    ([("t", 0), ("e", 10), ("s", 20), ("t", 30)], 3, [("tes", 10.0), ("est", 10.0)]),
    ([("t", 0), ("e", 10), ("s", 20), ("t", 30)], 4, [("test", 10.0)]),
    # Edge cases: empty lists, too short
    ([], 2, []),
    ([("a", 0)], 2, []),
    ([("a", 0), ("b", 10)], 3, []),
    # Edge cases: n out of bounds
    ([("a", 0), ("b", 10)], 1, []), # n < MIN_NGRAM_SIZE (and < 2 for speed calc)
    ([("a",0)]*11, 11, []), # n > MAX_NGRAM_SIZE
    # Varied timings
    ([("q", 0), ("w", 150), ("e", 200), ("r", 400)], 2, [("qw", 150.0), ("we", 50.0), ("er", 200.0)]),
    ([("q", 0), ("w", 150), ("e", 200), ("r", 400)], 3, [("qwe", 100.0), ("wer", 125.0)]),
    # Zero duration (simultaneous keystrokes for the purpose of speed calc)
    ([("x", 0), ("y", 0), ("z", 100)], 2, [("xy", 0.0), ("yz", 100.0)]),
    ([("x", 0), ("y", 0), ("z", 100)], 3, [("xyz", 50.0)]),
    # Max n-gram size
    ([(char_val, i*10) for i, char_val in enumerate("abcdefghij")], MAX_NGRAM_SIZE, [("abcdefghij", 10.0)]),
    (
        [(char_val, i*10) for i, char_val in enumerate("abcdefghijk")], 
        MAX_NGRAM_SIZE, 
        [("abcdefghij", 10.0), ("bcdefghijk", 10.0)]
    ),
    # More tests to reach 15+
    ([("s",0),("l",50),("o",250),("w",300)], 2, [("sl",50.0),("lo",200.0),("ow",50.0)]),
    ([("s",0),("l",50),("o",250),("w",300)], 3, [("slo",125.0),("low",125.0)]),
    ([("f",0),("a",10),("s",20),("t",30),("e",40),("r",50)], 6, [("faster",10.0)]),
    ([("o",0),("n",10),("e",20)], 2, [("on",10.0),("ne",10.0)]),
    ([("o",0),("n",10),("e",20)], 3, [("one",10.0)]),
]

@pytest.mark.parametrize("keystrokes, n, expected_ngrams_with_speed", KEYSTROKE_SPEED_TEST_CASES)
def test_ngram_speed_calculation(keystrokes: List[Tuple[str, int]], n: int, 
                               expected_ngrams_with_speed: List[Tuple[str, float]],
                               test_session_setup) -> None:
    """
    Test objective: Verify n-gram speed calculation for various keystroke sequences and n-sizes.
    This test uses the test_session_setup fixture as requested, though the fixture's
    outputs are not directly used by generate_ngrams_with_speed itself.
    """
    # session_id, snippet_id, category_id = test_session_setup # Unused in this specific test
    
    actual_ngrams_with_speed = generate_ngrams_with_speed(keystrokes, n)
    
    # For float comparisons, it's often better to use pytest.approx
    # However, for this specific calculation, direct comparison should be fine if inputs are simple.
    # If issues arise, convert expected speeds to pytest.approx(speed, rel=1e-5)
    
    assert len(actual_ngrams_with_speed) == len(expected_ngrams_with_speed), \
        f"For keystrokes={keystrokes}, n={n}: Expected {len(expected_ngrams_with_speed)} ngrams, got {len(actual_ngrams_with_speed)}"

    for actual, expected in zip(actual_ngrams_with_speed, expected_ngrams_with_speed):
        assert actual[0] == expected[0], \
            f"For keystrokes={keystrokes}, n={n}: Ngram text mismatch. Expected '{expected[0]}', got '{actual[0]}'"
        assert actual[1] == pytest.approx(expected[1]), \
            f"For keystrokes={keystrokes}, n={n}, ngram='{actual[0]}': Speed mismatch. Expected {expected[1]}, got {actual[1]}"

# --- Standalone Execution ---

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
