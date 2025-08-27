"""Tests for NGramAnalyticsService class.

This module contains comprehensive tests for the NGramAnalyticsService class,
including tests for decaying average calculations, performance summaries,
historical analysis, and analytics methods moved from NGramManager.
"""

import sys
from datetime import datetime, timedelta
from typing import List, Tuple

import pytest
from pydantic import ValidationError

# Add the project root to the path
sys.path.insert(0, "d:\\SeanDevLocal\\AITypingTrainer")

from db.database_manager import DatabaseManager
from models.ngram_analytics_service import (
    DecayingAverageCalculator,
    NGramAnalyticsService,
    NGramHeatmapData,
    NGramHistoricalData,
    NGramPerformanceData,
)
from models.ngram_manager import NGramManager

# Import fixtures and types from conftest
# Note: do not import unused test-only types from conftest; prior names
# (MockNGramSpeedData, MockSessionData, ngram_speed_test_data) no longer exist.
from tests.models.conftest import MockNGramSpeedData, MockSessionData

# Fixtures are now imported from conftest.py


class TestDecayingAverageCalculator:
    """Test the DecayingAverageCalculator class."""

    def test_calculate_decaying_average_basic(self) -> None:
        """Test objective: Verify basic decaying average calculation.

        Tests that the calculator properly computes a decaying average
        where more recent values have higher weights.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=20)

        # Test with simple values where recent should weigh more
        values = [100.0, 200.0, 300.0]  # Most recent is 300
        timestamps = [
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now(),
        ]
        print("values", values)

        result = calc.calculate_decaying_average(values, timestamps)

        # Most recent value should have highest influence
        # With decay_factor=0.9: 300*1.0 + 200*0.9 + 100*0.81 = 561
        # weight_sum = 1.0 + 0.9 + 0.81 = 2.71, result = 561/2.71 ≈ 207
        assert result > 200.0  # Should be higher than simple average (200)
        assert result < 220.0  # But not too much higher with decay_factor=0.9
        assert result == pytest.approx(207.01, abs=1.0)  # Should be close to calculated value

    def test_calculate_decaying_average_single_value(self) -> None:
        """Test objective: Verify decaying average with single value.

        Tests that a single value returns itself as the average.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=20)

        values = [150.0]
        timestamps = [datetime.now()]

        result = calc.calculate_decaying_average(values, timestamps)
        assert result == 150.0

    def test_calculate_decaying_average_empty_values(self) -> None:
        """Test objective: Verify decaying average with empty input.

        Tests that empty input returns 0.0.
        """
        calc = DecayingAverageCalculator(decay_factor=0.9, max_samples=20)

        result = calc.calculate_decaying_average([], [])
        assert result == 0.0

    def test_calculate_decaying_average_max_samples(self) -> None:
        """Test objective: Verify decaying average respects max_samples limit.

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
            datetime.now(),
        ]

        result = calc.calculate_decaying_average(values, timestamps)

        # Should only use the last 3 values (300, 400, 500)
        # and should be closer to 500 due to decay
        assert result > 400.0
        assert result < 500.0


class TestNGramAnalyticsService:
    """Test the NGramAnalyticsService class."""

    def test_init_with_valid_dependencies(self, db_with_tables: DatabaseManager) -> None:
        """Test objective: Verify NGramAnalyticsService initialization.

        Tests that the service initializes properly with valid dependencies.
        """
        ngram_manager = NGramManager()
        service = NGramAnalyticsService(db_with_tables, ngram_manager)

        assert service.db == db_with_tables
        assert service.ngram_manager == ngram_manager
        assert service.decaying_average_calculator is not None

    def test_init_with_none_dependencies(self) -> None:
        """Test objective: Verify NGramAnalyticsService handles None dependencies.

        Tests that the service handles None dependencies gracefully.
        """
        service = NGramAnalyticsService(None, None)

        assert service.db is None
        assert service.ngram_manager is None
        assert service.decaying_average_calculator is not None

    def test_refresh_speed_summaries_basic(
        self,
        ngram_speed_test_data: Tuple[DatabaseManager, NGramAnalyticsService, str, str, str],
    ) -> None:
        """Test objective: Verify speed summaries refresh functionality.

        Tests that speed summaries are properly calculated and stored
        in the summary table.
        """
        db, service, _session_id, user_id, keyboard_id = ngram_speed_test_data
        # Run refresh on preloaded mock data
        service.refresh_speed_summaries(user_id, keyboard_id)
        # Verify summary table has records for user/keyboard
        rows = db.fetchall(
            "SELECT * FROM ngram_speed_summary_curr WHERE user_id = ? AND keyboard_id = ?",
            (user_id, keyboard_id),
        )
        assert len(rows) > 0

    def test_dual_insert_creates_records_in_both_tables(
        self,
        temp_db: DatabaseManager,
        mock_sessions: List[MockSessionData],
        mock_ngram_data: List[MockNGramSpeedData],
    ) -> None:
        """Test objective: Verify dual-insert creates records in both current and history tables.

        Tests that when refresh_speed_summaries is called, records are created
        in both ngram_speed_summary_curr and ngram_speed_summary_hist tables.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)

        # Seed required FK rows
        user_id = "user_1"
        keyboard_id = "keyboard_1"
        # Seed required FK rows
        temp_db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", "user_1@example.com"),
        )
        temp_db.execute(
            (
                "INSERT INTO keyboards (keyboard_id, user_id, "
                "keyboard_name, target_ms_per_keystroke) VALUES (?, ?, ?, ?)"
            ),
            (keyboard_id, user_id, "Test Keyboard", 100),
        )
        temp_db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_1", "Test Category"),
        )
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("test_snippet_1", "cat_1", "Snippet 1"),
        )

        # Insert test session and keyboard data
        for session in mock_sessions:
            temp_db.execute(
                """
                INSERT INTO practice_sessions (
                    session_id,
                    user_id,
                    keyboard_id,
                    snippet_id,
                    snippet_index_start,
                    snippet_index_end,
                    content,
                    start_time,
                    end_time,
                    actual_chars,
                    errors,
                    ms_per_keystroke
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    session["session_id"],
                    session["user_id"],
                    session["keyboard_id"],
                    "test_snippet_1",
                    0,
                    10,
                    "test content",
                    session["start_time"],
                    session["start_time"],
                    "test",
                    0,
                    session["target_ms_per_keystroke"],
                ),
            )

        for ngram_data in mock_ngram_data:
            temp_db.execute(
                """
                INSERT INTO session_ngram_speed (
                    ngram_speed_id,
                    session_id,
                    ngram_size,
                    ngram_text,
                    ngram_time_ms,
                    ms_per_keystroke
                ) VALUES (
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    ngram_data["ngram_speed_id"],
                    ngram_data["session_id"],
                    ngram_data["ngram_size"],
                    ngram_data["ngram_text"],
                    ngram_data["ngram_time_ms"],
                    ngram_data["ms_per_keystroke"],
                ),
            )

        # keyboards pre-seeded above

        # Refresh speed summaries
        service.refresh_speed_summaries(user_id, keyboard_id)

        # Check record counts in both tables
        current_row = temp_db.fetchone("SELECT COUNT(*) AS cnt FROM ngram_speed_summary_curr")
        history_row = temp_db.fetchone("SELECT COUNT(*) AS cnt FROM ngram_speed_summary_hist")
        current_count = int(current_row["cnt"]) if current_row is not None else 0
        history_count = int(history_row["cnt"]) if history_row is not None else 0

        assert current_count > 0, "Current table should have records"
        assert history_count > 0, "History table should have records"
        assert current_count == history_count, "Both tables should have same number of records"

    def test_history_table_accumulates_all_records(
        self,
        temp_db: DatabaseManager,
        mock_sessions: List[MockSessionData],
        mock_ngram_data: List[MockNGramSpeedData],
    ) -> None:
        """Test objective: Verify history table contains all records over multiple refreshes.

        Tests that the history table accumulates all records from multiple
        refresh operations while current table only contains latest values.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)

        user_id = "user_1"
        keyboard_id = "keyboard_1"

        # Seed required FK rows for users, keyboards, categories, and snippets
        temp_db.execute(
            """
            INSERT INTO users (
                user_id,
                first_name,
                surname,
                email_address
            ) VALUES (
                ?, ?, ?, ?
            )
            """,
            (user_id, "Test", "User", "user_1@example.com"),
        )
        temp_db.execute(
            """
            INSERT INTO keyboards (
                keyboard_id,
                user_id,
                keyboard_name,
                target_ms_per_keystroke
            ) VALUES (
                ?, ?, ?, ?
            )
            """,
            (keyboard_id, user_id, "Test Keyboard", 100),
        )
        temp_db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_1", "Test Category"),
        )
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("test_snippet_1", "cat_1", "Snippet 1"),
        )

        # Set up initial test data
        for session in mock_sessions:
            temp_db.execute(
                """
                INSERT INTO practice_sessions (
                    session_id,
                    user_id,
                    keyboard_id,
                    snippet_id,
                    snippet_index_start,
                    snippet_index_end,
                    content,
                    start_time,
                    end_time,
                    actual_chars,
                    errors,
                    ms_per_keystroke
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    session["session_id"],
                    session["user_id"],
                    session["keyboard_id"],
                    "test_snippet_1",
                    0,
                    10,
                    "test content",
                    session["start_time"],
                    session["start_time"],
                    "test",
                    0,
                    session["target_ms_per_keystroke"],
                ),
            )

        for ngram_data in mock_ngram_data:
            temp_db.execute(
                """
                INSERT INTO session_ngram_speed (
                    ngram_speed_id,
                    session_id,
                    ngram_size,
                    ngram_text,
                    ngram_time_ms,
                    ms_per_keystroke
                ) VALUES (
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    ngram_data["ngram_speed_id"],
                    ngram_data["session_id"],
                    ngram_data["ngram_size"],
                    ngram_data["ngram_text"],
                    ngram_data["ngram_time_ms"],
                    ngram_data["ms_per_keystroke"],
                ),
            )

        # keyboards pre-seeded above

        # First refresh
        service.refresh_speed_summaries(user_id, keyboard_id)
        history_row_1 = temp_db.fetchone("SELECT COUNT(*) AS cnt FROM ngram_speed_summary_hist")
        history_count_1 = int(history_row_1["cnt"]) if history_row_1 is not None else 0

        # Add more data and refresh again (use a unique session ID not in mock_sessions)
        session_id_2 = "session_3"
        # Ensure referenced snippet exists before inserting practice session (for FKs)
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("test_snippet_2", "cat_1", "Snippet 2"),
        )
        temp_db.execute(
            """
            INSERT INTO practice_sessions (
                session_id,
                user_id,
                keyboard_id,
                snippet_id,
                snippet_index_start,
                snippet_index_end,
                content,
                start_time,
                end_time,
                actual_chars,
                errors,
                ms_per_keystroke
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                session_id_2,
                user_id,
                keyboard_id,
                "test_snippet_2",
                0,
                10,
                "test content 2",
                "2024-01-01 10:00:00",
                "2024-01-01 10:00:00",
                "test",
                0,
                150,
            ),
        )

        temp_db.execute(
            """
            INSERT INTO session_ngram_speed (
                ngram_speed_id,
                session_id,
                ngram_size,
                ngram_text,
                ngram_time_ms,
                ms_per_keystroke
            ) VALUES (
                ?, ?, ?, ?, ?, ?
            )
            """,
            ("new_ngram_1", session_id_2, 2, "ab", 200.0, 100.0),
        )

        # Second refresh
        service.refresh_speed_summaries(user_id, keyboard_id)
        history_row_2 = temp_db.fetchone("SELECT COUNT(*) AS cnt FROM ngram_speed_summary_hist")
        history_count_2 = int(history_row_2["cnt"]) if history_row_2 is not None else 0

        # History should accumulate all records
        assert history_count_2 > history_count_1, (
            "History should accumulate records from multiple refreshes"
        )

        # Current table should only have latest values
        current_row = temp_db.fetchone("SELECT COUNT(*) AS cnt FROM ngram_speed_summary_curr")
        current_count = int(current_row["cnt"]) if current_row is not None else 0
        assert current_count <= history_count_2, (
            "Current table should have same or fewer records than history"
        )

    def test_slowest_n_filters_can_eliminate_results(
        self,
        temp_db: DatabaseManager,
    ) -> None:
        """Test objective: Reproduce UI's "no n-grams" by filters and verify relaxing them returns data.

        This simulates the Dynamic Config UI behavior where:
        - included_keys defaults to "ueocdtsn" (which excludes 'h')
        - min_occurrences defaults to 5

        We seed valid n-gram data ('th', 'he') that exists in the DB, then show:
        1) With restrictive included_keys (missing 'h') and min_occurrences=1 -> excluded by key filter
        2) With inclusive keys (includes 'h') but min_occurrences=5 while only 2 occurrences exist -> excluded by HAVING
        3) With inclusive keys and min_occurrences=1 -> results returned
        """
        # Arrange minimal FK graph
        user_id = "user_filters"
        keyboard_id = "kb_filters"
        temp_db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", "filters@example.com"),
        )
        temp_db.execute(
            (
                "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name, target_ms_per_keystroke) "
                "VALUES (?, ?, ?, ?)"
            ),
            (keyboard_id, user_id, "KB", 120),
        )
        temp_db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_filters", "Cat"),
        )
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("sn_filters", "cat_filters", "Snippet"),
        )

        # One practice session
        session_id = "session_filters"
        temp_db.execute(
            """
            INSERT INTO practice_sessions (
                session_id, user_id, keyboard_id, snippet_id,
                snippet_index_start, snippet_index_end, content,
                start_time, end_time, actual_chars, errors, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                keyboard_id,
                "sn_filters",
                0,
                20,
                "some content",
                "2024-01-01 10:00:00",
                "2024-01-01 10:00:00",
                20,
                0,
                150,
            ),
        )

        # Seed n-gram speed data; both contain 'h' so key-filter "ueocdtsn" will exclude them
        # Create two occurrences each to be below min_occurrences=5 threshold
        rows: List[Tuple[str, int, str, float, float]] = [
            (session_id, 2, "th", 220.0, 110.0),
            (session_id, 2, "th", 240.0, 120.0),
            (session_id, 2, "he", 230.0, 115.0),
            (session_id, 2, "he", 210.0, 105.0),
        ]
        for i, (sid, size, text, t_ms, mpk) in enumerate(rows):
            temp_db.execute(
                """
                INSERT INTO session_ngram_speed (
                    ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (f"ng_filter_{i}", sid, size, text, t_ms, mpk),
            )

        service = NGramAnalyticsService(temp_db, NGramManager(temp_db))

        # Act/Assert 1: Restrictive included_keys excludes 'th'/'he' entirely
        restrictive_keys = list("ueocdtsn")  # From UI default in dynamic_config
        out1 = service.slowest_n(
            n=10,
            keyboard_id=keyboard_id,
            user_id=user_id,
            ngram_sizes=[2],
            included_keys=restrictive_keys,
            min_occurrences=1,
            focus_on_speed_target=False,
        )
        assert out1 == [], "Key filter should exclude n-grams containing 'h'"

        # Act/Assert 2: Include 'h' but require 5 occurrences (we only have 2 per n-gram)
        inclusive_keys = list("ueocdtsnh")
        out2 = service.slowest_n(
            n=10,
            keyboard_id=keyboard_id,
            user_id=user_id,
            ngram_sizes=[2],
            included_keys=inclusive_keys,
            min_occurrences=5,
            focus_on_speed_target=False,
        )
        assert out2 == [], "HAVING COUNT >= 5 should filter out n-grams with only 2 occurrences"

        # Act/Assert 3: Include 'h' and relax min_occurrences -> results appear
        out3 = service.slowest_n(
            n=10,
            keyboard_id=keyboard_id,
            user_id=user_id,
            ngram_sizes=[2],
            included_keys=inclusive_keys,
            min_occurrences=1,
            focus_on_speed_target=False,
        )
        assert len(out3) > 0, "Relaxing filters should return existing n-grams"

    def test_get_ngram_history_retrieval(
        self,
        temp_db: DatabaseManager,
        mock_sessions: List[MockSessionData],
        mock_ngram_data: List[MockNGramSpeedData],
    ) -> None:
        """Test objective: Verify history retrieval functionality.

        Tests that historical data can be retrieved properly with correct
        timestamps and performance metrics.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)

        user_id = "user_1"
        keyboard_id = "keyboard_1"

        # Seed required FK rows for users, keyboards, categories, and snippets
        temp_db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", "user_1@example.com"),
        )
        temp_db.execute(
            (
                "INSERT INTO keyboards (keyboard_id, user_id, "
                "keyboard_name, target_ms_per_keystroke) VALUES (?, ?, ?, ?)"
            ),
            (keyboard_id, user_id, "Test Keyboard", 100),
        )
        temp_db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_1", "Test Category"),
        )
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("test_snippet_1", "cat_1", "Snippet 1"),
        )

        # Set up test data and refresh
        for session in mock_sessions:
            temp_db.execute(
                """
                INSERT INTO practice_sessions (
                    session_id,
                    user_id,
                    keyboard_id,
                    snippet_id,
                    snippet_index_start,
                    snippet_index_end,
                    content,
                    start_time,
                    end_time,
                    actual_chars,
                    errors,
                    ms_per_keystroke
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    session["session_id"],
                    session["user_id"],
                    session["keyboard_id"],
                    "test_snippet_1",
                    0,
                    10,
                    "test content",
                    session["start_time"],
                    session["start_time"],
                    "test",
                    0,
                    session["target_ms_per_keystroke"],
                ),
            )

        for ngram_data in mock_ngram_data:
            temp_db.execute(
                """
                INSERT INTO session_ngram_speed 
                    (ngram_speed_id, 
                    session_id, 
                    ngram_size, 
                    ngram_text, 
                    ngram_time_ms, 
                    ms_per_keystroke
                    ) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    ngram_data["ngram_speed_id"],
                    ngram_data["session_id"],
                    ngram_data["ngram_size"],
                    ngram_data["ngram_text"],
                    ngram_data["ngram_time_ms"],
                    ngram_data["ms_per_keystroke"],
                ),
            )

        # keyboards pre-seeded above

        service.refresh_speed_summaries(user_id, keyboard_id)

        # Test the get_ngram_history method (to be implemented)
        history = service.get_ngram_history(user_id, keyboard_id, "th")

        assert len(history) > 0, "Should return history records"
        assert all(isinstance(record, NGramHistoricalData) for record in history), (
            "Should return NGramHistoricalData objects"
        )
        assert all(record.ngram_text == "th" for record in history), "Should filter by ngram_text"

    def test_summarize_session_ngrams_uses_rowcount_on_postgres(
        self,
        temp_db: DatabaseManager,
        mock_sessions: List[MockSessionData],
        mock_ngram_data: List[MockNGramSpeedData],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test objective: On Postgres, avoid SQLite-only SELECT changes() and use rowcount.

        Simulates a Postgres environment by setting `is_postgres=True` and ensures
        `summarize_session_ngrams()` does not execute `SELECT changes()`.
        """
        ngram_manager = NGramManager(temp_db)
        service = NGramAnalyticsService(temp_db, ngram_manager)

        # Seed minimal FK rows
        user_id = "user_pg"
        keyboard_id = "kb_pg"
        temp_db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", "pg@example.com"),
        )
        temp_db.execute(
            (
                "INSERT INTO keyboards (keyboard_id, user_id, "
                "keyboard_name, target_ms_per_keystroke) VALUES (?, ?, ?, ?)"
            ),
            (keyboard_id, user_id, "KB", 120),
        )
        temp_db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_pg", "Cat"),
        )
        temp_db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("sn_pg", "cat_pg", "Snippet"),
        )

        # One session
        sess = mock_sessions[0]
        temp_db.execute(
            """
            INSERT INTO practice_sessions (
                session_id, user_id, keyboard_id, snippet_id,
                snippet_index_start, snippet_index_end, content,
                start_time, end_time, actual_chars, errors, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sess["session_id"],
                user_id,
                keyboard_id,
                "sn_pg",
                0,
                10,
                "content",
                sess["start_time"],
                sess["start_time"],
                "abc",
                0,
                150,
            ),
        )

        # Some n-gram speed rows for that session
        temp_db.execute(
            """
            INSERT INTO session_ngram_speed (
                ngram_speed_id, session_id, ngram_size, ngram_text, ngram_time_ms, ms_per_keystroke
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("pg_speed_1", sess["session_id"], 2, "th", 200.0, 100.0),
        )

        # Simulate Postgres and assert no SELECT changes() is used
        temp_db.is_postgres = True

        original_fetchone = temp_db.fetchone

        def _fetchone_guard(query: str, params: tuple = ()) -> object | None:
            assert "changes()" not in query, "SELECT changes() must not be used on Postgres"
            return original_fetchone(query, params)

        monkeypatch.setattr(temp_db, "fetchone", _fetchone_guard, raising=True)

        inserted = service.summarize_session_ngrams()
        assert inserted >= 0

    def test_history_table_schema_compatibility(self, temp_db: DatabaseManager) -> None:
        """Test objective: Verify history table schema matches current table.

        Tests that the history table has the same essential columns as
        the current table plus additional history-specific fields.
        """
        # No service instantiation needed for schema checks; use direct PRAGMA queries

        # Verify table schemas are compatible
        current_schema = temp_db.fetchall("PRAGMA table_info(ngram_speed_summary_curr)")
        history_schema = temp_db.fetchall("PRAGMA table_info(ngram_speed_summary_hist)")

        assert len(current_schema) > 0, "Current table should exist"
        assert len(history_schema) > 0, "History table should exist"

        # Check that history table has all essential columns from current table
        current_columns = {str(col.get("name")) for col in current_schema}
        history_columns = {str(col.get("name")) for col in history_schema}

        essential_columns = {
            "user_id",
            "keyboard_id",
            "ngram_text",
            "ngram_size",
            "decaying_average_ms",
            "target_performance_pct",
            "sample_count",
        }

        assert essential_columns.issubset(current_columns), (
            "Current table missing essential columns"
        )
        assert essential_columns.issubset(history_columns), (
            "History table missing essential columns"
        )

        # History table should have additional history-specific columns
        assert "updated_dt" in history_columns, (
            "History table should have updated_dt timestamp column"
        )


class TestNGramPerformanceData:
    """Test the NGramPerformanceData model."""

    def test_valid_performance_data(self) -> None:
        """Test objective: Verify NGramPerformanceData model validation.

        Tests that the model properly validates correct performance data.
        """
        data = NGramPerformanceData(
            ngram_text="th",
            ngram_size=2,
            decaying_average_ms=150.0,
            target_performance_pct=75.0,
            sample_count=10,
            last_measured=datetime.now(),
            performance_category="amber",
        )

        assert data.ngram_text == "th"
        assert data.ngram_size == 2
        assert data.decaying_average_ms == 150.0
        assert data.target_performance_pct == 75.0
        assert data.sample_count == 10
        assert data.performance_category == "amber"

    def test_invalid_performance_data(self) -> None:
        """Test objective: Verify NGramPerformanceData model validation errors.

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
                performance_category="amber",
            )


class TestNGramHeatmapData:
    """Test the NGramHeatmapData model."""

    def test_valid_heatmap_data(self) -> None:
        """Test objective: Verify NGramHeatmapData model validation.

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
            color_code="#FFD700",
        )

        assert data.ngram_text == "th"
        assert data.color_code == "#FFD700"
        assert data.decaying_average_wpm == 60.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
