"""
Tests for NGramAnalyticsService class.

This module contains comprehensive tests for the NGramAnalyticsService class,
including tests for decaying average calculations, performance summaries,
historical analysis, and analytics methods moved from NGramManager.
"""

import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, TypedDict
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

# Add the project root to the path
sys.path.insert(0, 'd:\\SeanDevLocal\\AITypingTrainer')

from db.database_manager import DatabaseManager
from models.ngram_analytics_service import (
    NGramAnalyticsService,
    NGramPerformanceData,
    NGramHeatmapData,
    NGramHistoricalData,
    NGramSummaryData,
    DecayingAverageCalculator
)
from models.ngram import NGram
from models.ngram_manager import NGramManager, NGramStats


class MockSessionData(TypedDict):
    """Test data structure for mock sessions."""
    session_id: str
    user_id: str
    keyboard_id: str
    start_time: str
    target_ms_per_keystroke: int


class MockNGramSpeedData(TypedDict):
    """Test data structure for mock n-gram speed data."""
    ngram_speed_id: str
    session_id: str
    ngram_size: int
    ngram_text: str
    ngram_time_ms: float
    ms_per_keystroke: float


@pytest.fixture
def temp_db():
    """
    Test objective: Provide a temporary, isolated database for testing.
    
    Creates a temporary DatabaseManager instance with an in-memory database,
    initializes the schema, and ensures cleanup after the test.
    """
    db = DatabaseManager(":memory:")
    db.init_tables()
    yield db
    db.close()


@pytest.fixture
def mock_sessions() -> List[MockSessionData]:
    """
    Test objective: Provide mock session data for testing.
    
    Returns a list of mock session data with different timestamps
    for testing historical analysis and decaying averages.
    """
    base_time = datetime.now() - timedelta(days=30)
    return [
        {
            "session_id": str(uuid.uuid4()),
            "user_id": "user_1",
            "keyboard_id": "keyboard_1",
            "start_time": (base_time + timedelta(days=i)).isoformat(),
            "target_ms_per_keystroke": 200
        }
        for i in range(20)
    ]


@pytest.fixture
def mock_ngram_data() -> List[MockNGramSpeedData]:
    """
    Test objective: Provide mock n-gram speed data for testing.
    
    Returns a list of mock n-gram speed data with varying performance
    for testing decaying average calculations and analytics.
    """
    return [
        {
            "ngram_speed_id": str(uuid.uuid4()),
            "session_id": "session_1",
            "ngram_size": 2,
            "ngram_text": "th",
            "ngram_time_ms": 400.0,
            "ms_per_keystroke": 200.0
        },
        {
            "ngram_speed_id": str(uuid.uuid4()),
            "session_id": "session_2",
            "ngram_size": 2,
            "ngram_text": "th",
            "ngram_time_ms": 350.0,
            "ms_per_keystroke": 175.0
        },
        {
            "ngram_speed_id": str(uuid.uuid4()),
            "session_id": "session_3",
            "ngram_size": 2,
            "ngram_text": "th",
            "ngram_time_ms": 300.0,
            "ms_per_keystroke": 150.0
        }
    ]


class TestDecayingAverageCalculator:
    """Test the DecayingAverageCalculator class."""
    
    def test_calculate_decaying_average_basic(self):
        """
        Test objective: Verify basic decaying average calculation.
        
        Tests that the calculator properly computes a decaying average
        where more recent values have higher weights.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=20)
        
        # Test with simple values where recent should weigh more
        values = [100.0, 200.0, 300.0]  # Most recent is 300
        timestamps = [
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now()
        ]
        
        result = calc.calculate_decaying_average(values, timestamps)
        
        # Most recent value should have highest influence
        # With decay_factor=0.9: 300*1.0 + 200*0.9 + 100*0.81 = 561
        # weight_sum = 1.0 + 0.9 + 0.81 = 2.71, result = 561/2.71 ≈ 207
        assert result > 200.0  # Should be higher than simple average (200)
        assert result < 220.0  # But not too much higher with decay_factor=0.9
        assert abs(result - 207.01) < 1.0  # Should be close to calculated value
        
    def test_calculate_decaying_average_single_value(self):
        """
        Test objective: Verify decaying average with single value.
        
        Tests that a single value returns itself as the average.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=20)
        
        values = [150.0]
        timestamps = [datetime.now()]
        
        result = calc.calculate_decaying_average(values, timestamps)
        assert result == 150.0
        
    def test_calculate_decaying_average_empty_values(self):
        """
        Test objective: Verify decaying average with empty input.
        
        Tests that empty input returns 0.0.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=20)
        
        result = calc.calculate_decaying_average([], [])
        assert result == 0.0
        
    def test_calculate_decaying_average_max_samples(self):
        """
        Test objective: Verify decaying average respects max_samples limit.
        
        Tests that only the most recent max_samples values are used.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=3)
        
        # Provide more values than max_samples
        values = [100.0, 200.0, 300.0, 400.0, 500.0]
        timestamps = [
            datetime.now() - timedelta(days=4),
            datetime.now() - timedelta(days=3),
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now()
        ]
        
        result = calc.calculate_decaying_average(values, timestamps)
        
        # Should only use the last 3 values (300, 400, 500)
        # and should be closer to 500 due to decay
        assert result > 400.0
        assert result < 500.0


class TestNGramAnalyticsService:
    """Test the NGramAnalyticsService class."""
    
    def test_init_with_valid_dependencies(self, temp_db):
        """
        Test objective: Verify NGramAnalyticsService initialization.
        
        Tests that the service initializes properly with valid dependencies.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        assert service.db == temp_db
        assert service.ngram_manager == ngram_manager
        assert service.decaying_average_calculator is not None
        
    def test_init_with_none_dependencies(self):
        """
        Test objective: Verify NGramAnalyticsService handles None dependencies.
        
        Tests that the service handles None dependencies gracefully.
        """
        service = NGramAnalyticsService(None, None)
        
        assert service.db is None
        assert service.ngram_manager is None
        assert service.decaying_average_calculator is not None
        
    def test_refresh_speed_summaries_basic(self, temp_db, mock_sessions, mock_ngram_data):
        """
        Test objective: Verify speed summaries refresh functionality.
        
        Tests that speed summaries are properly calculated and stored
        in the summary table.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # Set up mock data - insert user, keyboard, sessions, and ngram data
        # First insert user (required for foreign key constraint)
        temp_db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            ("user_1", "Test", "User", "test@example.com")
        )
        
        # Then insert keyboard
        temp_db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            ("keyboard_1", "user_1", "Test Keyboard")
        )
        
        # Insert practice_sessions from mock data
        # First insert a category (required for foreign key constraint)
        temp_db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_1", "Test Category")
        )
        
        # Then insert a snippet (required for foreign key constraint)
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("snippet_1", "cat_1", "Test Snippet")
        )
        
        for session in mock_sessions:
            temp_db.execute(
                "INSERT INTO practice_sessions (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, content, start_time, end_time, actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session["session_id"], "user_1", session["keyboard_id"], "snippet_1", 0, 10, "hello world", session["start_time"], session["start_time"], 10, 0, session["target_ms_per_keystroke"])
            )
        
        # Insert ngram speed data
        for ngram in mock_ngram_data:
            temp_db.execute(
                "INSERT INTO session_ngram_speed (ngram_speed_id, session_id, ngram_text, ngram_size, ngram_time_ms, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?)",
                (ngram["ngram_speed_id"], mock_sessions[0]["session_id"], ngram["ngram_text"], ngram["ngram_size"], ngram["ms_per_keystroke"], ngram["ms_per_keystroke"])
            )
        
        # Test refresh
        service.refresh_speed_summaries("user_1", "keyboard_1")
        
        # Verify summaries were created
        summaries = temp_db.fetchall(
            "SELECT * FROM ngram_speed_summaries WHERE user_id = ? AND keyboard_id = ?",
            ("user_1", "keyboard_1")
        )
        
        # Should have summaries for the mock data
        assert len(summaries) > 0
        
    def test_get_speed_heatmap_data_basic(self, temp_db):
        """
        Test objective: Verify speed heatmap data retrieval.
        
        Tests that heatmap data is properly retrieved with correct
        performance calculations and color coding.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # TODO: Set up test data
        
        heatmap_data = service.get_speed_heatmap_data(
            user_id="user_1",
            keyboard_id="keyboard_1",
            target_speed_ms=200.0
        )
        
        assert isinstance(heatmap_data, list)
        # Add more specific assertions based on implementation
        
    def test_get_performance_trends_basic(self, temp_db):
        """
        Test objective: Verify performance trends calculation.
        
        Tests that historical performance trends are properly calculated
        over the specified time window.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # TODO: Set up test data
        
        trends = service.get_performance_trends(
            user_id="user_1",
            keyboard_id="keyboard_1",
            time_window_days=30
        )
        
        assert isinstance(trends, dict)
        # Add more specific assertions based on implementation
        
    def test_slowest_n_moved_from_ngram_manager(self, temp_db):
        """
        Test objective: Verify slowest_n method moved from NGramManager.
        
        Tests that the slowest_n method works correctly in the analytics service
        with proper parameter handling and filtering.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # Set up test data - create practice session and n-gram data
        session_id = "test_session_1"
        user_id = "user_1"
        keyboard_id = "keyboard_1"
        
        # Insert test session with all required fields
        temp_db.execute(
            """INSERT INTO practice_sessions 
            (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, 
             content, start_time, end_time, actual_chars, errors, ms_per_keystroke) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, keyboard_id, "test_snippet_1", 0, 10, "test content", 
             "2024-01-01 10:00:00", "2024-01-01 10:05:00", 10, 0, 150.0)
        )
        
        # Insert test n-gram speed data
        temp_db.execute(
            "INSERT INTO session_ngram_speed (session_id, ngram_text, ngram_size, ms_per_keystroke) VALUES (?, ?, ?, ?)",
            (session_id, "th", 2, 150.0)
        )
        temp_db.execute(
            "INSERT INTO session_ngram_speed (session_id, ngram_text, ngram_size, ms_per_keystroke) VALUES (?, ?, ?, ?)",
            (session_id, "the", 3, 200.0)
        )
        temp_db.execute(
            "INSERT INTO session_ngram_speed (session_id, ngram_text, ngram_size, ms_per_keystroke) VALUES (?, ?, ?, ?)",
            (session_id, "er", 2, 100.0)
        )
        # Add more occurrences to meet the minimum count requirement
        for i in range(2):
            temp_db.execute(
                "INSERT INTO session_ngram_speed (session_id, ngram_text, ngram_size, ms_per_keystroke) VALUES (?, ?, ?, ?)",
                (session_id, "th", 2, 150.0 + i * 10)
            )
            temp_db.execute(
                "INSERT INTO session_ngram_speed (session_id, ngram_text, ngram_size, ms_per_keystroke) VALUES (?, ?, ?, ?)",
                (session_id, "the", 3, 200.0 + i * 10)
            )
            temp_db.execute(
                "INSERT INTO session_ngram_speed (session_id, ngram_text, ngram_size, ms_per_keystroke) VALUES (?, ?, ?, ?)",
                (session_id, "er", 2, 100.0 + i * 10)
            )
        
        # Test basic functionality
        slowest = service.slowest_n(
            n=5,
            keyboard_id=keyboard_id,
            user_id=user_id
        )
        
        assert isinstance(slowest, list)
        assert len(slowest) <= 5
        
        # Test with specific n-gram sizes
        slowest_bigrams = service.slowest_n(
            n=2,
            keyboard_id=keyboard_id,
            user_id=user_id,
            ngram_sizes=[2]
        )
        
        assert isinstance(slowest_bigrams, list)
        assert len(slowest_bigrams) <= 2
        
        # Test with included_keys parameter
        slowest_filtered = service.slowest_n(
            n=3,
            keyboard_id=keyboard_id,
            user_id=user_id,
            included_keys=["t", "h", "e"]
        )
        
        assert isinstance(slowest_filtered, list)
        # Should only return n-grams containing only 't', 'h', 'e'
        for ngram_stat in slowest_filtered:
            assert all(char in ["t", "h", "e"] for char in ngram_stat.ngram)
        
        # Test edge cases
        empty_result = service.slowest_n(n=0, keyboard_id=keyboard_id, user_id=user_id)
        assert empty_result == []
        
        no_sizes = service.slowest_n(n=5, keyboard_id=keyboard_id, user_id=user_id, ngram_sizes=[])
        assert no_sizes == []

    def test_error_n_moved_from_ngram_manager(self, temp_db):
        """
        Test objective: Verify error_n method moved from NGramManager.
        
        Tests that the error_n method works correctly in the analytics service
        with proper parameter handling and filtering.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # Set up test data - create practice session and n-gram error data
        session_id = "test_session_1"
        user_id = "user_1"
        keyboard_id = "keyboard_1"
        
        # Insert test session with all required fields
        temp_db.execute(
            """INSERT INTO practice_sessions 
            (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, 
             content, start_time, end_time, actual_chars, errors, ms_per_keystroke) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, user_id, keyboard_id, "test_snippet_1", 0, 10, "test content", 
             "2024-01-01 10:00:00", "2024-01-01 10:05:00", 10, 0, 150.0)
        )
        
        # Insert test n-gram error data
        temp_db.execute(
            "INSERT INTO session_ngram_errors (session_id, ngram_text, ngram_size) VALUES (?, ?, ?)",
            (session_id, "th", 2)
        )
        temp_db.execute(
            "INSERT INTO session_ngram_errors (session_id, ngram_text, ngram_size) VALUES (?, ?, ?)",
            (session_id, "the", 3)
        )
        temp_db.execute(
            "INSERT INTO session_ngram_errors (session_id, ngram_text, ngram_size) VALUES (?, ?, ?)",
            (session_id, "er", 2)
        )
        # Add more occurrences to meet minimum count requirement
        temp_db.execute(
            "INSERT INTO session_ngram_errors (session_id, ngram_text, ngram_size) VALUES (?, ?, ?)",
            (session_id, "th", 2)
        )
        temp_db.execute(
            "INSERT INTO session_ngram_errors (session_id, ngram_text, ngram_size) VALUES (?, ?, ?)",
            (session_id, "the", 3)
        )
        
        # Test basic functionality
        error_prone = service.error_n(
            n=5,
            keyboard_id=keyboard_id,
            user_id=user_id
        )
        
        assert isinstance(error_prone, list)
        assert len(error_prone) <= 5
        
        # Test with specific n-gram sizes
        error_bigrams = service.error_n(
            n=2,
            keyboard_id=keyboard_id,
            user_id=user_id,
            ngram_sizes=[2]
        )
        
        assert isinstance(error_bigrams, list)
        assert len(error_bigrams) <= 2
        
        # Test with included_keys parameter
        error_filtered = service.error_n(
            n=3,
            keyboard_id=keyboard_id,
            user_id=user_id,
            included_keys=["t", "h", "e"]
        )
        
        assert isinstance(error_filtered, list)
        # Should only return n-grams containing only 't', 'h', 'e'
        for ngram_stat in error_filtered:
            assert all(char in ["t", "h", "e"] for char in ngram_stat.ngram)
        
        # Test edge cases
        empty_result = service.error_n(n=0, keyboard_id=keyboard_id, user_id=user_id)
        assert empty_result == []
        
        no_sizes = service.error_n(n=5, keyboard_id=keyboard_id, user_id=user_id, ngram_sizes=[])
        assert no_sizes == []

    def test_dual_insert_creates_records_in_both_tables(self, temp_db, mock_sessions, mock_ngram_data):
        """
        Test objective: Verify dual-insert creates records in both current and history tables.
        
        Tests that when refresh_speed_summaries is called, records are created
        in both ngram_speed_summaries and ngram_speed_history tables.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # Set up test data
        user_id = "user_1"
        keyboard_id = "keyboard_1"
        
        # Insert test session and keyboard data
        for session in mock_sessions:
            temp_db.execute(
                """INSERT INTO practice_sessions 
                (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, 
                 content, start_time, end_time, actual_chars, errors, ms_per_keystroke) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session['session_id'], session['user_id'], session['keyboard_id'], 
                 "test_snippet_1", 0, 10, "test content", session['start_time'], 
                 session['start_time'], "test", 0, session['target_ms_per_keystroke'])
            )
        
        for ngram_data in mock_ngram_data:
            temp_db.execute(
                """INSERT INTO session_ngram_speed 
                (ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (ngram_data['ngram_speed_id'], ngram_data['session_id'], 
                 ngram_data['ngram_size'], ngram_data['ngram_text'], 
                 ngram_data['ngram_time_ms'], ngram_data['ms_per_keystroke'])
            )
        
        # Insert keyboard data
        temp_db.execute(
            "INSERT INTO keyboards (keyboard_id, keyboard_name, target_ms_per_keystroke) VALUES (?, ?, ?)",
            (keyboard_id, "Test Keyboard", 100)
        )
        
        # Refresh speed summaries
        service.refresh_speed_summaries(user_id, keyboard_id)
        
        # Check that records exist in both tables
        current_count = temp_db.fetchone("SELECT COUNT(*) FROM ngram_speed_summaries")[0]
        history_count = temp_db.fetchone("SELECT COUNT(*) FROM ngram_speed_history")[0]
        
        assert current_count > 0, "Current table should have records"
        assert history_count > 0, "History table should have records"
        assert current_count == history_count, "Both tables should have same number of records"

    def test_history_table_accumulates_all_records(self, temp_db, mock_sessions, mock_ngram_data):
        """
        Test objective: Verify history table contains all records over multiple refreshes.
        
        Tests that the history table accumulates all records from multiple
        refresh operations while current table only contains latest values.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        user_id = "user_1"
        keyboard_id = "keyboard_1"
        
        # Set up initial test data
        for session in mock_sessions:
            temp_db.execute(
                """INSERT INTO practice_sessions 
                (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, 
                 content, start_time, end_time, actual_chars, errors, ms_per_keystroke) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session['session_id'], session['user_id'], session['keyboard_id'], 
                 "test_snippet_1", 0, 10, "test content", session['start_time'], 
                 session['start_time'], "test", 0, session['target_ms_per_keystroke'])
            )
        
        for ngram_data in mock_ngram_data:
            temp_db.execute(
                """INSERT INTO session_ngram_speed 
                (ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (ngram_data['ngram_speed_id'], ngram_data['session_id'], 
                 ngram_data['ngram_size'], ngram_data['ngram_text'], 
                 ngram_data['ngram_time_ms'], ngram_data['ms_per_keystroke'])
            )
        
        temp_db.execute(
            "INSERT INTO keyboards (keyboard_id, keyboard_name, target_ms_per_keystroke) VALUES (?, ?, ?)",
            (keyboard_id, "Test Keyboard", 100)
        )
        
        # First refresh
        service.refresh_speed_summaries(user_id, keyboard_id)
        history_count_1 = temp_db.fetchone("SELECT COUNT(*) FROM ngram_speed_history")[0]
        
        # Add more data and refresh again
        session_id_2 = "session_2"
        temp_db.execute(
            """INSERT INTO practice_sessions 
            (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, 
             content, start_time, end_time, actual_chars, errors, ms_per_keystroke) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id_2, user_id, keyboard_id, "test_snippet_2", 0, 10, "test content 2", 
             "2024-01-01 10:00:00", "2024-01-01 10:00:00", "test", 0, 150)
        )
        
        temp_db.execute(
            """INSERT INTO session_ngram_speed 
            (ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("new_ngram_1", session_id_2, 2, "ab", 200.0, 100.0)
        )
        
        # Second refresh
        service.refresh_speed_summaries(user_id, keyboard_id)
        history_count_2 = temp_db.fetchone("SELECT COUNT(*) FROM ngram_speed_history")[0]
        
        # History should accumulate all records
        assert history_count_2 > history_count_1, "History should accumulate records from multiple refreshes"
        
        # Current table should only have latest values
        current_count = temp_db.fetchone("SELECT COUNT(*) FROM ngram_speed_summaries")[0]
        assert current_count <= history_count_2, "Current table should have same or fewer records than history"

    def test_get_ngram_history_retrieval(self, temp_db, mock_sessions, mock_ngram_data):
        """
        Test objective: Verify history retrieval functionality.
        
        Tests that historical data can be retrieved properly with correct
        timestamps and performance metrics.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        user_id = "user_1"
        keyboard_id = "keyboard_1"
        
        # Set up test data and refresh
        for session in mock_sessions:
            temp_db.execute(
                """INSERT INTO practice_sessions 
                (session_id, user_id, keyboard_id, snippet_id, snippet_index_start, snippet_index_end, 
                 content, start_time, end_time, actual_chars, errors, ms_per_keystroke) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session['session_id'], session['user_id'], session['keyboard_id'], 
                 "test_snippet_1", 0, 10, "test content", session['start_time'], 
                 session['start_time'], "test", 0, session['target_ms_per_keystroke'])
            )
        
        for ngram_data in mock_ngram_data:
            temp_db.execute(
                """INSERT INTO session_ngram_speed 
                (ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (ngram_data['ngram_speed_id'], ngram_data['session_id'], 
                 ngram_data['ngram_size'], ngram_data['ngram_text'], 
                 ngram_data['ngram_time_ms'], ngram_data['ms_per_keystroke'])
            )
        
        temp_db.execute(
            "INSERT INTO keyboards (keyboard_id, keyboard_name, target_ms_per_keystroke) VALUES (?, ?, ?)",
            (keyboard_id, "Test Keyboard", 100)
        )
        
        service.refresh_speed_summaries(user_id, keyboard_id)
        
        # Test the get_ngram_history method (to be implemented)
        history = service.get_ngram_history(user_id, keyboard_id, "th")
        
        assert len(history) > 0, "Should return history records"
        assert all(isinstance(record, NGramHistoricalData) for record in history), "Should return NGramHistoricalData objects"
        assert all(record.ngram_text == "th" for record in history), "Should filter by ngram_text"

    def test_history_table_schema_compatibility(self, temp_db):
        """
        Test objective: Verify history table schema matches current table.
        
        Tests that the history table has the same essential columns as
        the current table plus additional history-specific fields.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # Check that both tables exist
        current_schema = temp_db.fetchall("PRAGMA table_info(ngram_speed_summaries)")
        history_schema = temp_db.fetchall("PRAGMA table_info(ngram_speed_history)")
        
        assert len(current_schema) > 0, "Current table should exist"
        assert len(history_schema) > 0, "History table should exist"
        
        # Check that history table has all essential columns from current table
        current_columns = {col[1] for col in current_schema}  # column name is index 1
        history_columns = {col[1] for col in history_schema}
        
        essential_columns = {
            'user_id', 'keyboard_id', 'ngram_text', 'ngram_size', 
            'decaying_average_ms', 'target_performance_pct', 'sample_count'
        }
        
        assert essential_columns.issubset(current_columns), "Current table missing essential columns"
        assert essential_columns.issubset(history_columns), "History table missing essential columns"
        
        # History table should have additional history-specific columns
        assert 'measurement_date' in history_columns, "History table should have measurement_date"


class TestNGramPerformanceData:
    """Test the NGramPerformanceData model."""
    
    def test_valid_performance_data(self):
        """
        Test objective: Verify NGramPerformanceData model validation.
        
        Tests that the model properly validates correct performance data.
        """
        data = NGramPerformanceData(
            ngram_text="th",
            ngram_size=2,
            decaying_average_ms=150.0,
            target_performance_pct=75.0,
            sample_count=10,
            last_measured=datetime.now(),
            performance_category="amber"
        )
        
        assert data.ngram_text == "th"
        assert data.ngram_size == 2
        assert data.decaying_average_ms == 150.0
        assert data.target_performance_pct == 75.0
        assert data.sample_count == 10
        assert data.performance_category == "amber"
        
    def test_invalid_performance_data(self):
        """
        Test objective: Verify NGramPerformanceData model validation errors.
        
        Tests that the model properly rejects invalid performance data.
        """
        with pytest.raises(ValidationError):
            NGramPerformanceData(
                ngram_text="",  # Empty string should fail
                ngram_size=2,
                decaying_average_ms=150.0,
                target_performance_pct=75.0,
                sample_count=10,
                last_measured=datetime.now(),
                performance_category="amber"
            )


class TestNGramHeatmapData:
    """Test the NGramHeatmapData model."""
    
    def test_valid_heatmap_data(self):
        """
        Test objective: Verify NGramHeatmapData model validation.
        
        Tests that the model properly validates correct heatmap data.
        """
        data = NGramHeatmapData(
            ngram_text="th",
            ngram_size=2,
            decaying_average_ms=150.0,
            decaying_average_wpm=60.0,
            target_performance_pct=75.0,
            sample_count=10,
            last_measured=datetime.now(),
            performance_category="amber",
            color_code="#FFD700"
        )
        
        assert data.ngram_text == "th"
        assert data.color_code == "#FFD700"
        assert data.decaying_average_wpm == 60.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
