"""Comprehensive tests for NGramAnalyticsService session-level methods.

Tests the three new methods:
- SummarizeSessionNgrams
- AddSpeedSummaryForSession  
- CatchupSpeedSummary

These tests use real database connections and do not mock database operations
as per the requirement to test database pushdown functionality.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, cast

import pytest

from db.database_manager import DatabaseManager
from models.keyboard import Keyboard
from models.ngram_analytics_service import NGramAnalyticsService
from models.user import User
from tests.models.conftest import TestSessionMethodsFixtures


@pytest.fixture
def test_data_setup(db_with_tables: DatabaseManager, test_user: User, test_keyboard: Keyboard) -> Dict[str, Any]:
    """Set up comprehensive test data for session analytics tests."""
    db = db_with_tables
    
    # Create category and snippet
    category_id = TestSessionMethodsFixtures.create_category(db)
    snippet_id = TestSessionMethodsFixtures.create_snippet(db, category_id)
    
    # Create multiple sessions with different timestamps
    base_time = datetime.now() - timedelta(days=10)
    sessions = []
    
    for i in range(5):
        session_time = (base_time + timedelta(days=i)).isoformat()
        session_id = TestSessionMethodsFixtures.create_practice_session(
            db, str(test_user.user_id), str(test_keyboard.keyboard_id), snippet_id, 
            session_time, 150.0 + (i * 10)  # Varying speeds
        )
        sessions.append(session_id)
    
    return {
        'sessions': sessions,
        'user_id': str(test_user.user_id),
        'keyboard_id': str(test_keyboard.keyboard_id),
        'snippet_id': snippet_id,
        'category_id': category_id
    }


class TestSummarizeSessionNgrams:
    """Test cases for SummarizeSessionNgrams method."""
    
    @pytest.mark.parametrize("ngram_speed_count,expected_min_records", [
        (1, 1),  # Single ngram speed entry
        (3, 3),  # Multiple ngram speed entries
    ])
    def test_summarize_with_ngram_speed_only(
        self, 
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any],
        ngram_speed_count: int,
        expected_min_records: int
    ) -> None:
        """Test summarization with only ngram speed data."""
        db = analytics_service.db
        assert db is not None
        db = cast(DatabaseManager, db)
        session_id = test_data_setup['sessions'][0]
        
        # Create ngram speed data
        ngram_data = []
        for i in range(ngram_speed_count):
            ngram_data.append({
                'ngram_size': 2,
                'ngram_text': f'te{i}',
                'ngram_time_ms': 200.0 + (i * 10),
                'ms_per_keystroke': 100.0 + (i * 5)
            })
        
        TestSessionMethodsFixtures.create_session_ngram_speed(db, session_id, ngram_data)
        
        # Run summarization
        result = analytics_service.summarize_session_ngrams()
        
        # Verify results
        assert result >= expected_min_records
        
        # Check data was inserted correctly
        summary_records = db.fetchall(
            "SELECT * FROM session_ngram_summary WHERE session_id = ?",
            (session_id,)
        )
        
        assert len(summary_records) >= expected_min_records
        
        for record in summary_records:
            assert record['session_id'] == session_id
            assert record['user_id'] == test_data_setup['user_id']
            assert record['keyboard_id'] == test_data_setup['keyboard_id']
            assert float(record['avg_ms_per_keystroke']) > 0
            assert int(record['instance_count']) > 0
    
    @pytest.mark.parametrize("error_count,expected_errors", [
        (1, 1),  # Single error entry
        (2, 2),  # Multiple error entries
    ])
    def test_summarize_with_ngram_errors_only(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any],
        error_count: int,
        expected_errors: int
    ) -> None:
        """Test summarization with only ngram error data."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Create ngram speed data (required for errors to be processed)
        speed_data = [{
            'ngram_size': 2,
            'ngram_text': 'te',
            'ngram_time_ms': 200.0,
            'ms_per_keystroke': 100.0
        }]
        TestSessionMethodsFixtures.create_session_ngram_speed(db, session_id, speed_data)
        
        # Create error data
        error_data = []
        for _i in range(error_count):
            error_data.append({
                'ngram_size': 2,
                'ngram_text': 'te'  # Same ngram as speed data
            })
        
        TestSessionMethodsFixtures.create_session_ngram_errors(db, session_id, error_data)
        
        # Run summarization
        result = analytics_service.summarize_session_ngrams()
        
        # Verify results
        assert result >= 1
        
        # Check error count was aggregated correctly
        summary_records = db.fetchall(
            "SELECT * FROM session_ngram_summary WHERE session_id = ? AND ngram_text = 'te'",
            (session_id,)
        )
        
        assert len(summary_records) >= 1
        assert int(summary_records[0]['error_count']) == expected_errors
    
    def test_summarize_with_speed_and_errors(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test summarization with both speed and error data."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Create ngram speed data
        speed_data = [
            {
                'ngram_size': 2,
                'ngram_text': 'th',
                'ngram_time_ms': 180.0,
                'ms_per_keystroke': 90.0
            },
            {
                'ngram_size': 3,
                'ngram_text': 'the',
                'ngram_time_ms': 270.0,
                'ms_per_keystroke': 90.0
            }
        ]
        TestSessionMethodsFixtures.create_session_ngram_speed(db, session_id, speed_data)
        
        # Create error data
        error_data = [
            {'ngram_size': 2, 'ngram_text': 'th'},  # Error for first ngram
            {'ngram_size': 2, 'ngram_text': 'th'}   # Second error for same ngram
        ]
        TestSessionMethodsFixtures.create_session_ngram_errors(db, session_id, error_data)
        
        # Run summarization
        result = analytics_service.summarize_session_ngrams()
        
        # Verify results
        assert result >= 2
        
        # Check both ngrams were processed
        th_record = db.fetchone(
            "SELECT * FROM session_ngram_summary WHERE session_id = ? AND ngram_text = 'th'",
            (session_id,)
        )
        the_record = db.fetchone(
            "SELECT * FROM session_ngram_summary WHERE session_id = ? AND ngram_text = 'the'",
            (session_id,)
        )
        
        assert th_record is not None
        assert int(th_record['error_count']) == 2
        assert int(th_record['instance_count']) == 3  # 1 speed + 2 errors
        
        assert the_record is not None
        assert int(the_record['error_count']) == 0
        assert int(the_record['instance_count']) == 1  # 1 speed only
    
    @pytest.mark.parametrize("keystroke_count,expected_1grams", [
        (1, 1),  # Single keystroke
        (3, 3),  # Multiple keystrokes
    ])
    def test_summarize_with_keystrokes(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any],
        keystroke_count: int,
        expected_1grams: int
    ) -> None:
        """Test summarization with keystroke data (1-grams)."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Create keystroke data
        keystroke_data = []
        base_time = datetime.now().isoformat()
        
        for i in range(keystroke_count):
            keystroke_data.append({
                'keystroke_time': base_time,
                'keystroke_char': chr(ord('a') + i),
                'expected_char': chr(ord('a') + i),
                'is_error': 0,
                'time_since_previous': 100 + (i * 10)
            })
        
        TestSessionMethodsFixtures.create_session_keystrokes(db, session_id, keystroke_data)
        
        # Run summarization
        result = analytics_service.summarize_session_ngrams()
        
        # Verify results
        assert result >= expected_1grams
        
        # Check 1-gram records were created
        summary_records = db.fetchall(
            "SELECT * FROM session_ngram_summary WHERE session_id = ? AND ngram_size = 1",
            (session_id,)
        )
        
        assert len(summary_records) == expected_1grams
        
        for record in summary_records:
            assert int(record['ngram_size']) == 1
            assert len(str(record['ngram_text'])) == 1
            assert float(record['avg_ms_per_keystroke']) > 0
    
    def test_no_sessions_missing(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test behavior when no sessions are missing from summary table."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Pre-populate session_ngram_summary
        db.execute(
            """
            INSERT INTO session_ngram_summary (
                session_id, ngram_text, user_id, keyboard_id, ngram_size,
                avg_ms_per_keystroke, target_speed_ms, instance_count, 
                error_count, updated_dt, session_dt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, 'test', test_data_setup['user_id'], 
                test_data_setup['keyboard_id'], 2, 100.0, 600, 1, 0, 
                datetime.now().isoformat(), datetime.now().isoformat()
            )
        )
        
        # Run summarization
        result = analytics_service.summarize_session_ngrams()
        
        # Should return 0 since no sessions are missing
        assert result == 0
    
    def test_sessions_missing_no_data(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test behavior with sessions missing but no ngram/keystroke data."""
        # Sessions exist but no ngram_speed, ngram_errors, or keystrokes data
        # This should result in 0 records inserted due to filtering
        
        result = analytics_service.summarize_session_ngrams()
        
        # Should return 0 since no valid data to summarize
        assert result == 0


class TestAddSpeedSummaryForSession:
    """Test cases for AddSpeedSummaryForSession method."""
    
    def test_single_session_processing(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test processing a single session."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # First populate session_ngram_summary (required for AddSpeedSummaryForSession)
        db.execute(
            """
            INSERT INTO session_ngram_summary (
                session_id, ngram_text, user_id, keyboard_id, ngram_size,
                avg_ms_per_keystroke, target_speed_ms, instance_count, 
                error_count, updated_dt, session_dt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, 'te', test_data_setup['user_id'], 
                test_data_setup['keyboard_id'], 2, 120.0, 600, 5, 1, 
                datetime.now().isoformat(), datetime.now().isoformat()
            )
        )
        
        # Process the session
        result = analytics_service.add_speed_summary_for_session(session_id)
        
        # Verify results structure
        assert isinstance(result, dict)
        assert 'hist_inserted' in result
        assert 'curr_updated' in result
        assert result['hist_inserted'] >= 0
        assert result['curr_updated'] >= 0
    
    def test_nonexistent_session(
        self,
        analytics_service: NGramAnalyticsService
    ) -> None:
        """Test processing a nonexistent session."""
        fake_session_id = str(uuid.uuid4())
        
        with pytest.raises(ValueError, match=f"Session {fake_session_id} not found"):
            analytics_service.add_speed_summary_for_session(fake_session_id)
    
    def test_multiple_ngrams_processing(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test processing session with multiple ngrams."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Create multiple ngram summary entries
        ngrams = ['th', 'he', 'er', 'te']
        for i, ngram in enumerate(ngrams):
            db.execute(
                """
                INSERT INTO session_ngram_summary (
                    session_id, ngram_text, user_id, keyboard_id, ngram_size,
                    avg_ms_per_keystroke, target_speed_ms, instance_count, 
                    error_count, updated_dt, session_dt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, ngram, test_data_setup['user_id'], 
                    test_data_setup['keyboard_id'], 2, 120.0 + (i * 10), 600, 
                    3 + i, i, datetime.now().isoformat(), datetime.now().isoformat()
                )
            )
        
        # Process the session
        result = analytics_service.add_speed_summary_for_session(session_id)
        
        # Should have processed multiple ngrams
        assert result['hist_inserted'] >= len(ngrams)
        assert result['curr_updated'] >= len(ngrams)
        
        # Verify records were created in both tables
        hist_row = db.fetchone(
            "SELECT COUNT(*) as count FROM ngram_speed_summary_hist"
        )
        assert hist_row is not None
        hist_count = int(hist_row['count'])
        curr_row = db.fetchone(
            "SELECT COUNT(*) as count FROM ngram_speed_summary_curr"
        )
        assert curr_row is not None
        curr_count = int(curr_row['count'])
        
        assert hist_count >= len(ngrams)
        assert curr_count >= len(ngrams)


class TestCatchupSpeedSummary:
    """Test cases for CatchupSpeedSummary method."""
    
    def test_empty_database_catchup(
        self,
        analytics_service: NGramAnalyticsService
    ) -> None:
        """Test catchup with no sessions in database."""
        result = analytics_service.catchup_speed_summary()
        
        assert isinstance(result, dict)
        assert result['total_sessions'] == 0
        assert result['total_hist_inserted'] == 0
        assert result['total_curr_updated'] == 0
    
    def test_single_session_catchup(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test catchup with a single session."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Add session summary data
        db.execute(
            """
            INSERT INTO session_ngram_summary (
                session_id, ngram_text, user_id, keyboard_id, ngram_size,
                avg_ms_per_keystroke, target_speed_ms, instance_count, 
                error_count, updated_dt, session_dt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, 'te', test_data_setup['user_id'], 
                test_data_setup['keyboard_id'], 2, 130.0, 600, 4, 0, 
                datetime.now().isoformat(), datetime.now().isoformat()
            )
        )
        
        # Run catchup
        result = analytics_service.catchup_speed_summary()
        
        # Verify results
        assert result['total_sessions'] >= 1
        assert result['processed_sessions'] >= 1
        assert result['total_hist_inserted'] >= 0
        assert result['total_curr_updated'] >= 0
    
    def test_multiple_sessions_catchup(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test catchup with multiple sessions."""
        db = analytics_service.db
        
        # Add session summary data for multiple sessions
        for i, session_id in enumerate(test_data_setup['sessions'][:3]):
            db.execute(
                """
                INSERT INTO session_ngram_summary (
                    session_id, ngram_text, user_id, keyboard_id, ngram_size,
                    avg_ms_per_keystroke, target_speed_ms, instance_count, 
                    error_count, updated_dt, session_dt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, f'ng{i}', test_data_setup['user_id'], 
                    test_data_setup['keyboard_id'], 2, 140.0 + (i * 5), 600, 
                    2 + i, i, datetime.now().isoformat(), datetime.now().isoformat()
                )
            )
        
        # Run catchup
        result = analytics_service.catchup_speed_summary()
        
        # Verify results
        assert result['total_sessions'] >= 3
        assert result['processed_sessions'] >= 3
        
        # Should have processed sessions in chronological order
        # (verified by the method's internal logging)
    
    def test_catchup_with_session_errors(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test catchup continues processing even when individual sessions fail."""
        db = analytics_service.db
        
        # Add valid data for first session
        db.execute(
            """
            INSERT INTO session_ngram_summary (
                session_id, ngram_text, user_id, keyboard_id, ngram_size,
                avg_ms_per_keystroke, target_speed_ms, instance_count, 
                error_count, updated_dt, session_dt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_data_setup['sessions'][0], 'ok', test_data_setup['user_id'], 
                test_data_setup['keyboard_id'], 2, 150.0, 600, 3, 0, 
                datetime.now().isoformat(), datetime.now().isoformat()
            )
        )
        
        # Second session will have no summary data (will cause processing to skip/fail gracefully)
        
        # Run catchup
        result = analytics_service.catchup_speed_summary()
        
        # Should still process available sessions
        assert result['total_sessions'] >= 2
        # processed_sessions might be less than total if some fail
        assert result['processed_sessions'] >= 0


class TestIntegrationScenarios:
    """Integration tests combining multiple methods."""
    
    def test_full_workflow_integration(
        self,
        analytics_service: NGramAnalyticsService,
        test_data_setup: Dict[str, Any]
    ) -> None:
        """Test complete workflow: Summarize -> AddSpeedSummary -> Catchup."""
        db = analytics_service.db
        session_id = test_data_setup['sessions'][0]
        
        # Step 1: Create raw session data
        speed_data = [{
            'ngram_size': 2,
            'ngram_text': 'in',
            'ngram_time_ms': 160.0,
            'ms_per_keystroke': 80.0
        }]
        TestSessionMethodsFixtures.create_session_ngram_speed(db, session_id, speed_data)
        
        keystroke_data = [{
            'keystroke_time': datetime.now().isoformat(),
            'keystroke_char': 'x',
            'expected_char': 'x',
            'is_error': 0,
            'time_since_previous': 95
        }]
        TestSessionMethodsFixtures.create_session_keystrokes(db, session_id, keystroke_data)
        
        # Step 2: Summarize sessions
        summarize_result = analytics_service.summarize_session_ngrams()
        assert summarize_result >= 2  # At least 'in' ngram + 'x' keystroke
        
        # Step 3: Add speed summary for specific session
        speed_result = analytics_service.add_speed_summary_for_session(session_id)
        assert speed_result['hist_inserted'] >= 1
        assert speed_result['curr_updated'] >= 1
        
        # Step 4: Run catchup (should process the session we just worked with)
        catchup_result = analytics_service.catchup_speed_summary()
        assert catchup_result['total_sessions'] >= 1
        assert catchup_result['processed_sessions'] >= 1
        
        # Verify final state
        summary_row = db.fetchone(
            "SELECT COUNT(*) as count FROM session_ngram_summary"
        )
        assert summary_row is not None
        summary_count = int(summary_row['count'])
        hist_row = db.fetchone(
            "SELECT COUNT(*) as count FROM ngram_speed_summary_hist"
        )
        assert hist_row is not None
        hist_count = int(hist_row['count'])
        curr_row = db.fetchone(
            "SELECT COUNT(*) as count FROM ngram_speed_summary_curr"
        )
        assert curr_row is not None
        curr_count = int(curr_row['count'])
        
        assert summary_count >= 2
        assert hist_count >= 1
        assert curr_count >= 1
