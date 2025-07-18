"""
Tests for the NGramManager class.
"""

import math
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path to allow importing from models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from models.ngram_manager import NGramManager

# Test data
SAMPLE_SESSIONS = [
    {
        "session_id": "session1",
        "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
        "content": "the quick brown fox",
    },
    {
        "session_id": "session2",
        "start_time": datetime.now().isoformat(),
        "content": "jumps over the lazy dog",
    },
]

# Test keyboard and user IDs
TEST_KEYBOARD_ID = "test-keyboard-123"
TEST_USER_ID = "test-user-456"

SAMPLE_NGRAM_SPEED = [
    ("the", 3, 500, 2, "session1"),  # Slow n-gram
    ("qui", 3, 100, 1, "session1"),  # Faster n-gram
    ("bro", 3, 300, 1, "session1"),
    ("fox", 3, 250, 1, "session1"),
    ("jump", 4, 200, 1, "session2"),
    ("over", 4, 150, 1, "session2"),
    ("lazy", 4, 100, 1, "session2"),
]

SAMPLE_NGRAM_ERRORS = [
    ("the", 3, "session1"),
    ("the", 3, "session2"),  # 'the' appears in both sessions
    ("fox", 3, "session1"),
    ("dog", 3, "session2"),
]


class MockDB:
    """Mock database for testing."""

    def __init__(self, results=None):
        self.results = results or []
        self.last_query = None
        self.last_params = None
        self.execute = MagicMock()

    def fetchall(self, query, params=()):
        self.last_query = query
        self.last_params = params
        return self.results


@pytest.fixture
def mock_db():
    """Create a mock database with test data."""
    db = MockDB()
    return db


@pytest.fixture
def ngram_manager(mock_db):
    """Create an NGramManager instance with a mock database."""
    return NGramManager(mock_db)


def test_slowest_n_basic(ngram_manager, mock_db):
    """Test basic functionality of slowest_n method."""
    # Setup
    mock_db.results = [
        {
            "ngram": "the",
            "ngram_size": 3,
            "avg_time_ms": 500,
            "occurrences": 2,
            "last_used": SAMPLE_SESSIONS[1]["start_time"],
            "ngram_score": 500 * math.log(2),  # score = avg_time_ms * log(occurrences)
        },
        {
            "ngram": "bro",
            "ngram_size": 3,
            "avg_time_ms": 300,
            "occurrences": 1,
            "last_used": SAMPLE_SESSIONS[0]["start_time"],
            "ngram_score": 0,  # log10(1) = 0, so score = 300 * 0
        },
    ]

    # Test
    result = ngram_manager.slowest_n(2, TEST_KEYBOARD_ID, TEST_USER_ID, [3])

    # Verify
    assert len(result) == 2
    assert result[0].ngram == "the"
    assert result[0].ngram_size == 3
    assert result[0].avg_speed == pytest.approx(500)  # Now directly using avg_time_ms
    assert result[0].total_occurrences == 2
    assert result[0].ngram_score == pytest.approx(
        500 * math.log(2)
    )  # score = avg_time_ms * log(occurrences)
    assert result[1].ngram == "bro"
    assert result[1].avg_speed == pytest.approx(300)  # Now directly using avg_time_ms
    assert result[1].ngram_score == pytest.approx(0)  # log(1) = 0, so score = 0

    # Verify query parameters
    assert "LIMIT ?" in mock_db.last_query
    assert mock_db.last_params[0] == TEST_KEYBOARD_ID  # keyboard_id
    assert mock_db.last_params[1] == TEST_USER_ID  # user_id
    assert mock_db.last_params[2] == 1000  # lookback_distance
    assert 3 in mock_db.last_params  # ngram_size
    assert mock_db.last_params[-1] == 2  # limit


def test_error_n_basic(ngram_manager, mock_db):
    """Test basic functionality of error_n method."""
    # Setup
    mock_db.results = [
        {
            "ngram_id": "33333333-3333-3333-3333-333333333333",
            "ngram": "the",
            "ngram_size": 3,
            "error_count": 2,
            "last_used": SAMPLE_SESSIONS[1]["start_time"],
        },
        {
            "ngram_id": "44444444-4444-4444-4444-444444444444",
            "ngram": "fox",
            "ngram_size": 3,
            "error_count": 1,
            "last_used": SAMPLE_SESSIONS[0]["start_time"],
        },
    ]

    # Test
    result = ngram_manager.error_n(2, TEST_KEYBOARD_ID, TEST_USER_ID, [3])

    # Verify
    assert len(result) == 2
    assert result[0].ngram == "the"
    assert result[0].ngram_size == 3
    assert result[0].total_occurrences == 2  # error_count
    assert result[1].ngram == "fox"
    assert result[1].total_occurrences == 1

    # Verify query parameters
    assert "ORDER BY error_count DESC" in mock_db.last_query
    assert mock_db.last_params[0] == TEST_KEYBOARD_ID  # keyboard_id
    assert mock_db.last_params[1] == TEST_USER_ID  # user_id
    assert mock_db.last_params[2] == 1000  # lookback_distance
    assert 3 in mock_db.last_params  # ngram_size
    assert mock_db.last_params[-1] == 2  # limit


def test_slowest_n_empty_result(ngram_manager, mock_db):
    """Test slowest_n with no results."""
    # Setup
    mock_db.results = []

    # Test
    result = ngram_manager.slowest_n(5, TEST_KEYBOARD_ID, TEST_USER_ID, [3, 4])

    # Verify
    assert result == []
    assert "ngram_size IN (" in mock_db.last_query
    assert mock_db.last_params[0] == TEST_KEYBOARD_ID  # keyboard_id
    assert mock_db.last_params[1] == TEST_USER_ID  # user_id
    assert mock_db.last_params[2] == 1000  # lookback_distance
    assert set(mock_db.last_params[3:5]) == {3, 4}  # ngram_sizes
    assert mock_db.last_params[-1] == 5  # limit


def test_error_n_custom_lookback(ngram_manager, mock_db):
    """Test error_n with custom lookback distance."""
    # Setup
    mock_db.results = []

    # Test with custom lookback
    ngram_manager.error_n(5, TEST_KEYBOARD_ID, TEST_USER_ID, lookback_distance=500)

    # Verify lookback was used in query
    assert mock_db.last_params[0] == TEST_KEYBOARD_ID  # keyboard_id
    assert mock_db.last_params[1] == TEST_USER_ID  # user_id
    assert mock_db.last_params[2] == 500  # custom lookback_distance


def test_slowest_n_included_keys_basic(ngram_manager, mock_db):
    """Test objective: Test slowest_n with included_keys parameter basic functionality."""
    # Setup
    mock_db.results = [
        {
            "ngram": "the",
            "ngram_size": 3,
            "avg_time_ms": 500,
            "occurrences": 2,
            "last_used": SAMPLE_SESSIONS[1]["start_time"],
            "ngram_score": 500 * math.log(2),
        },
        {
            "ngram": "cat",
            "ngram_size": 3,
            "avg_time_ms": 300,
            "occurrences": 1,
            "last_used": SAMPLE_SESSIONS[0]["start_time"],
            "ngram_score": 300 * math.log(1),
        },
    ]

    # Test with included_keys filter
    included_keys = ["t", "h", "e", "c", "a"]
    result = ngram_manager.slowest_n(
        2, TEST_KEYBOARD_ID, TEST_USER_ID, [3], included_keys=included_keys
    )

    # Verify results
    assert len(result) == 2
    assert result[0].ngram == "the"
    assert result[1].ngram == "cat"

    # Verify query includes key filtering
    assert "GLOB" in mock_db.last_query
    assert "[^' || ? || ']*' = 0" in mock_db.last_query

    # Verify parameters include the allowed characters
    assert "theca" in mock_db.last_params  # joined included_keys


def test_slowest_n_included_keys_no_filter(ngram_manager, mock_db):
    """Test objective: Test slowest_n with included_keys=None (no filtering)."""
    # Setup
    mock_db.results = [
        {
            "ngram": "the",
            "ngram_size": 3,
            "avg_time_ms": 500,
            "occurrences": 2,
            "last_used": SAMPLE_SESSIONS[1]["start_time"],
            "ngram_score": 500 * math.log(2),
        },
    ]

    # Test with no included_keys filter
    result = ngram_manager.slowest_n(
        2, TEST_KEYBOARD_ID, TEST_USER_ID, [3], included_keys=None
    )

    # Verify results
    assert len(result) == 1
    assert result[0].ngram == "the"

    # Verify query does NOT include key filtering
    assert "GLOB" not in mock_db.last_query
    assert "[^' || ? || ']*' = 0" not in mock_db.last_query


def test_slowest_n_included_keys_empty_list(ngram_manager, mock_db):
    """Test objective: Test slowest_n with empty included_keys list."""
    # Setup
    mock_db.results = []

    # Test with empty included_keys list
    result = ngram_manager.slowest_n(
        2, TEST_KEYBOARD_ID, TEST_USER_ID, [3], included_keys=[]
    )

    # Verify results
    assert len(result) == 0

    # Verify query does NOT include key filtering for empty list
    assert "GLOB" not in mock_db.last_query
    assert "[^' || ? || ']*' = 0" not in mock_db.last_query


def test_error_n_included_keys_basic(ngram_manager, mock_db):
    """Test objective: Test error_n with included_keys parameter basic functionality."""
    # Setup
    mock_db.results = [
        {
            "ngram_id": "33333333-3333-3333-3333-333333333333",
            "ngram": "the",
            "ngram_size": 3,
            "error_count": 2,
            "last_used": SAMPLE_SESSIONS[1]["start_time"],
        },
        {
            "ngram_id": "44444444-4444-4444-4444-444444444444",
            "ngram": "cat",
            "ngram_size": 3,
            "error_count": 1,
            "last_used": SAMPLE_SESSIONS[0]["start_time"],
        },
    ]

    # Test with included_keys filter
    included_keys = ["t", "h", "e", "c", "a"]
    result = ngram_manager.error_n(
        2, TEST_KEYBOARD_ID, TEST_USER_ID, [3], included_keys=included_keys
    )

    # Verify results
    assert len(result) == 2
    assert result[0].ngram == "the"
    assert result[1].ngram == "cat"

    # Verify query includes key filtering
    assert "GLOB" in mock_db.last_query
    assert "[^' || ? || ']*' = 0" in mock_db.last_query

    # Verify parameters include the allowed characters
    assert "theca" in mock_db.last_params  # joined included_keys


def test_error_n_included_keys_no_filter(ngram_manager, mock_db):
    """Test objective: Test error_n with included_keys=None (no filtering)."""
    # Setup
    mock_db.results = [
        {
            "ngram_id": "33333333-3333-3333-3333-333333333333",
            "ngram": "the",
            "ngram_size": 3,
            "error_count": 2,
            "last_used": SAMPLE_SESSIONS[1]["start_time"],
        },
    ]

    # Test with no included_keys filter
    result = ngram_manager.error_n(
        2, TEST_KEYBOARD_ID, TEST_USER_ID, [3], included_keys=None
    )

    # Verify results
    assert len(result) == 1
    assert result[0].ngram == "the"

    # Verify query does NOT include key filtering
    assert "GLOB" not in mock_db.last_query
    assert "[^' || ? || ']*' = 0" not in mock_db.last_query


def test_error_n_included_keys_empty_list(ngram_manager, mock_db):
    """Test objective: Test error_n with empty included_keys list."""
    # Setup
    mock_db.results = []

    # Test with empty included_keys list
    result = ngram_manager.error_n(
        2, TEST_KEYBOARD_ID, TEST_USER_ID, [3], included_keys=[]
    )

    # Verify results
    assert len(result) == 0

    # Verify query does NOT include key filtering for empty list
    assert "GLOB" not in mock_db.last_query
    assert "[^' || ? || ']*' = 0" not in mock_db.last_query


class TestNGramManager:
    """Test cases for NGramManager class."""

    def test_delete_all_ngrams_success(self, mock_db):
        """Test that delete_all_ngrams deletes all n-gram data."""
        # Setup
        mock_db.execute.return_value = None
        ngram_manager = NGramManager(mock_db)

        # Execute
        result = ngram_manager.delete_all_ngrams()

        # Verify
        assert result is True
        # Verify both tables were cleared
        assert mock_db.execute.call_count == 2
        calls = [call[0][0] for call in mock_db.execute.call_args_list]
        assert "DELETE FROM session_ngram_speed" in calls
        assert "DELETE FROM session_ngram_errors" in calls

    def test_delete_all_ngrams_error(self, mock_db):
        """Test that delete_all_ngrams handles database errors."""
        # Setup
        from sqlite3 import Error as SQLiteError

        mock_db.execute.side_effect = SQLiteError("Database error")
        ngram_manager = NGramManager(mock_db)

        # Execute
        with patch("models.ngram_manager.logger") as mock_logger:
            result = ngram_manager.delete_all_ngrams()

            # Verify
            assert result is False
            mock_logger.error.assert_called_once()
            assert "Error deleting n-gram data" in mock_logger.error.call_args[0][0]
            assert "Database error" in str(mock_logger.error.call_args[0][1])


if __name__ == "__main__":
    # When run directly, use pytest to run the tests
    sys.exit(pytest.main(["-v", "-s", __file__]))
