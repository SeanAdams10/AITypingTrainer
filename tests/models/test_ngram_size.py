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

# --- Fixtures ---

@pytest.fixture(scope="function")
def db_manager() -> DatabaseManager:
    """Provides a DatabaseManager instance with a temporary, initialized database."""
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(temp_db_fd)
    db = DatabaseManager(temp_db_path)
    try:
        db.init_tables()  # Ensure tables are created
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")
        # Depending on how critical init_tables is, you might re-raise or handle
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
    """Provides a CategoryManager instance."""
    return CategoryManager(db_manager)

@pytest.fixture(scope="function")
def snippet_manager_fixture(db_manager: DatabaseManager) -> SnippetManager:
    """Provides a SnippetManager instance."""
    return SnippetManager(db_manager)

@pytest.fixture(scope="function")
def session_manager_fixture(db_manager: DatabaseManager) -> SessionManager:
    """Provides a SessionManager instance."""
    return SessionManager(db_manager)

@pytest.fixture(scope="function")
def test_session_setup(category_manager_fixture: CategoryManager, 
                       snippet_manager_fixture: SnippetManager, 
                       session_manager_fixture: SessionManager) -> Tuple[int, int, int]:
    """Fixture to set up a test category, snippet, and session.
    
    Returns (session_id, snippet_id, category_id).
    """
    try:
        category_id = category_manager_fixture.create_category("Test Category - Ngram Size")
        assert category_id is not None, "Failed to create category"
        
        snippet_id = snippet_manager_fixture.add_snippet(
            category_id, "Test Snippet - Ngram Size", 
            "This is test content for n-gram size tests.", 3
        )
        assert snippet_id is not None, "Failed to create snippet"
        
        # Assuming default user_id=1 if not specified by SessionManager.create_session
        session_id = session_manager_fixture.create_session(snippet_id, "practice") 
        assert session_id is not None, "Failed to create session"
        
        return session_id, snippet_id, category_id
    except Exception as e:
        logger.error(f"Error in test_session_setup fixture: {e}", exc_info=True)
        pytest.fail(f"Fixture test_session_setup failed: {e}")
        # To satisfy type hints in case of failure before return
        return (0,0,0) # Should not be reached if pytest.fail works

# --- N-gram Generation Logic ---

def generate_ngrams(text: str, n: int) -> List[str]:
    """Generates n-grams of size n from the given text.
    Only n-grams of size MIN_NGRAM_SIZE to MAX_NGRAM_SIZE (inclusive) are generated.
    Returns an empty list if n is outside this range or if n > len(text).
    """
    if not (MIN_NGRAM_SIZE <= n <= MAX_NGRAM_SIZE):
        return []
    if n > len(text):
        return []
    
    ngrams: List[str] = []
    for i in range(len(text) - n + 1):
        ngrams.append(text[i:i+n])
    return ngrams

# --- Test Cases ---

NGRAM_GENERATION_TEST_CASES = [
    # (text, n, expected_ngrams)
    ("abcde", 2, ["ab", "bc", "cd", "de"]),
    ("abcde", 3, ["abc", "bcd", "cde"]),
    ("abcde", 5, ["abcde"]),
    ("abcde", 1, []),  # n < MIN_NGRAM_SIZE
    ("abcde", 0, []),  # n < MIN_NGRAM_SIZE
    ("abcde", 6, []),  # n > len(text) but < MAX_NGRAM_SIZE
    ("abc", 3, ["abc"]),
    ("abc", 4, []),    # n > len(text)
    ("abcdefghij", MAX_NGRAM_SIZE, ["abcdefghij"]),  # len 10, n=MAX_NGRAM_SIZE
    ("abcdefghijk", MAX_NGRAM_SIZE, ["abcdefghij", "bcdefghijk"]),  # len 11, n=MAX_NGRAM_SIZE
    (
        "abcdefghijkl", 
        MAX_NGRAM_SIZE, 
        ["abcdefghij", "bcdefghijk", "cdefghijkl"]
    ),  # len 12, n=MAX_NGRAM_SIZE
    ("abcdefghij", MAX_NGRAM_SIZE + 1, []), # n > MAX_NGRAM_SIZE
    ("", 2, []),          # empty text
    ("a", 2, []),          # text too short for n=2
    ("ab", 2, ["ab"]),      # text len == n
    ("short", MIN_NGRAM_SIZE, ["sh", "ho", "or", "rt"]),
    ("short", MAX_NGRAM_SIZE, []), # n > len(text)
    (
        "verylongtext", 
        3, 
        ["ver", "ery", "ryl", "ylo", "lon", "ong", "ngt", "gte", "tex", "ext"]
    ),
    ("test", 4, ["test"]),
    ("test", 5, []), # n > len(text)
]

@pytest.mark.parametrize(
    "text, n, expected_ngrams", 
    NGRAM_GENERATION_TEST_CASES
)
def test_ngram_generation_logic(
    text: str, 
    n: int, 
    expected_ngrams: List[str],
    test_session_setup: Tuple[int, int, int]
) -> None:
    """
    Test objective: Verify n-gram generation logic for various texts and n-sizes.
    This test uses the test_session_setup fixture as requested, though the fixture's
    outputs (session_id, etc.) are not directly used by generate_ngrams itself.
    """
    # The test_session_setup fixture runs to ensure the environment can be set up.
    # session_id, snippet_id, category_id = test_session_setup # Unused in this specific test
    
    actual_ngrams = generate_ngrams(text, n)
    assert actual_ngrams == expected_ngrams, \
        f"For text='{text}', n={n}: Expected {expected_ngrams}, got {actual_ngrams}"

# --- Standalone Execution ---

if __name__ == "__main__":
    # This allows running the tests directly from this file, e.g., for debugging.
    # Ensure pytest is installed and accessible.
    sys.exit(pytest.main([__file__, "-v"]))
