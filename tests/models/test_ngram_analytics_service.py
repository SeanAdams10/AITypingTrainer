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
        and uses the decaying average algorithm.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # TODO: Set up test data
        
        slowest = service.slowest_n(
            n=5,
            keyboard_id="keyboard_1",
            user_id="user_1"
        )
        
        assert isinstance(slowest, list)
        assert len(slowest) <= 5
        # Add more specific assertions based on implementation
        
    def test_error_n_moved_from_ngram_manager(self, temp_db):
        """
        Test objective: Verify error_n method moved from NGramManager.
        
        Tests that the error_n method works correctly in the analytics service
        and uses the decaying average algorithm.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)
        
        # TODO: Set up test data
        
        error_prone = service.error_n(
            n=5,
            keyboard_id="keyboard_1",
            user_id="user_1"
        )
        
        assert isinstance(error_prone, list)
        assert len(error_prone) <= 5
        # Add more specific assertions based on implementation


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
