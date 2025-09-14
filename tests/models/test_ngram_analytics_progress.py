"""Tests for progress analytics helpers in NGramAnalyticsService.

These tests validate:
- Top/Bottom improvements between the two most recent sessions
- Counts of distinct n-grams not meeting target over the last N sessions
"""

from __future__ import annotations

import sys

import pytest

# Ensure project root is on path for direct module imports (consistent with other tests)
sys.path.insert(0, "d:\\SeanDevLocal\\AITypingTrainer")

from db.database_manager import DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


@pytest.mark.usefixtures("temp_db")
class TestProgressAnalytics:
    def _seed_min_graph(self, db: DatabaseManager, user_id: str, keyboard_id: str) -> None:
        """Create minimal FK graph: user, keyboard, category, snippet.

        Test objective: Ensure foreign keys exist for practice_sessions and downstream tables.
        """
        db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", f"{user_id}@example.com"),
        )
        db.execute(
            (
                "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name, "
                "target_ms_per_keystroke) VALUES (?, ?, ?, ?)"
            ),
            (keyboard_id, user_id, "KB", 200),  # target 200 ms per keystroke
        )
        db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            ("cat_p", "Cat"),
        )
        db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            ("sn_p", "cat_p", "Snippet"),
        )

    def _insert_session(
        self,
        db: DatabaseManager,
        session_id: str,
        user_id: str,
        keyboard_id: str,
        start_time: str,
        ms_per_keystroke: float = 250.0,
    ) -> None:
        """Insert a practice session row.

        Test objective: Provide two sessions with different timestamps to enable ordering.
        """
        db.execute(
            (
                "INSERT INTO practice_sessions (\n"
                "  session_id, user_id, keyboard_id, snippet_id,\n"
                "  snippet_index_start, snippet_index_end, content,\n"
                "  start_time, end_time, actual_chars, errors, ms_per_keystroke\n"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                session_id,
                user_id,
                keyboard_id,
                "sn_p",
                0,
                20,
                "content",
                start_time,
                start_time,
                20,
                0,
                ms_per_keystroke,
            ),
        )

    def _insert_speed(
        self,
        db: DatabaseManager,
        ngram_speed_id: str,
        session_id: str,
        size: int,
        text: str,
        t_ms: float,
        mpk: float,
    ) -> None:
        """Insert one row into session_ngram_speed."""
        db.execute(
            (
                "INSERT INTO session_ngram_speed (\n"
                "  ngram_speed_id, session_id, ngram_size, ngram_text, "
                "ngram_time_ms, ms_per_keystroke\n"
                ") VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (ngram_speed_id, session_id, size, text, t_ms, mpk),
        )

    def test_last_two_sessions_improvements_basic(self, temp_db: DatabaseManager) -> None:
        """Test objective: Verify top/bottom improvements between last two sessions.

        We seed two sessions with common n-grams 'ab' and 'cd':
        - For 'ab': previous slower (300 ms/ks), recent faster (200) -> positive improvement 100
        - For 'cd': previous faster (200), recent slower (250) -> negative improvement -50
        """
        db = temp_db
        svc = NGramAnalyticsService(db, NGramManager(db))

        user_id = "u_prog"
        keyboard_id = "kb_prog"
        self._seed_min_graph(db, user_id, keyboard_id)

        # Two sessions (prev older date, recent newer date)
        prev_sid = "s_prev"
        recent_sid = "s_recent"
        self._insert_session(db, prev_sid, user_id, keyboard_id, "2024-01-01 10:00:00", 260.0)
        self._insert_session(db, recent_sid, user_id, keyboard_id, "2024-01-02 10:00:00", 240.0)

        # N-gram speeds for both sessions (same ngrams present across both)
        # Previous session: 'ab' slower, 'cd' faster
        self._insert_speed(db, "spd1", prev_sid, 2, "ab", 300.0, 300.0)
        self._insert_speed(db, "spd2", prev_sid, 2, "cd", 200.0, 200.0)
        # Recent session: 'ab' faster, 'cd' slower
        self._insert_speed(db, "spd3", recent_sid, 2, "ab", 200.0, 200.0)
        self._insert_speed(db, "spd4", recent_sid, 2, "cd", 250.0, 250.0)

        # Build session summaries then populate speed summaries for hist
        svc.summarize_session_ngrams()
        svc.add_speed_summary_for_session(prev_sid)
        svc.add_speed_summary_for_session(recent_sid)

        # Use the newer get_session_performance_comparison method
        comparisons = svc.get_session_performance_comparison(
            keyboard_id=keyboard_id, keys="abcd", occurrences=1
        )

        # We should see both n-grams in the results
        ngram_texts = [comp.ngram_text for comp in comparisons]
        assert "ab" in ngram_texts, "'ab' should be present"
        assert "cd" in ngram_texts, "'cd' should be present"

        # Find the specific comparisons
        ab_comp = next((comp for comp in comparisons if comp.ngram_text == "ab"), None)
        cd_comp = next((comp for comp in comparisons if comp.ngram_text == "cd"), None)

        assert ab_comp is not None, "'ab' comparison should exist"
        assert cd_comp is not None, "'cd' comparison should exist"

        # 'ab' improved: prev=300, latest=200, so delta_perf should be positive (300-200=100)
        assert ab_comp.delta_perf > 0, f"'ab' should show improvement, got {ab_comp.delta_perf}"

        # 'cd' regressed: prev=200, latest=250, so delta_perf should be negative (200-250=-50)
        assert cd_comp.delta_perf < 0, f"'cd' should show regression, got {cd_comp.delta_perf}"

    def test_not_meeting_target_counts_last_n_sessions(self, temp_db: DatabaseManager) -> None:
        """Test objective: Verify counts of unique n-grams not meeting target over last N sessions.

        With target_ms_per_keystroke = 200 (seeded), we insert:
        - Session A: n-grams with ms_per_keystroke > 200 (should not meet target)
        - Session B: mixed speeds to create non-zero counts
        Verify the method returns two entries (oldest->newest) with integer counts.
        """
        db = temp_db
        svc = NGramAnalyticsService(db, NGramManager(db))

        user_id = "u_cnt"
        keyboard_id = "kb_cnt"
        self._seed_min_graph(db, user_id, keyboard_id)

        sid_a = "s_a"
        sid_b = "s_b"
        self._insert_session(db, sid_a, user_id, keyboard_id, "2024-02-01 09:00:00", 300.0)
        self._insert_session(db, sid_b, user_id, keyboard_id, "2024-02-02 09:00:00", 150.0)

        # Seed some ngram speeds
        # A: both slower than target
        self._insert_speed(db, "c1", sid_a, 2, "aa", 300.0, 300.0)
        self._insert_speed(db, "c2", sid_a, 3, "bbb", 280.0, 280.0)
        # B: one slower, one faster
        self._insert_speed(db, "c3", sid_b, 2, "cc", 220.0, 220.0)
        self._insert_speed(db, "c4", sid_b, 3, "ddd", 150.0, 150.0)

        # Build summaries and hist rows
        svc.summarize_session_ngrams()
        svc.add_speed_summary_for_session(sid_a)
        svc.add_speed_summary_for_session(sid_b)

        series = svc.get_not_meeting_target_counts_last_n_sessions(
            user_id=user_id, keyboard_id=keyboard_id, n_sessions=20
        )

        # Expect two sessions returned in chronological order (oldest first)
        assert len(series) >= 2
        assert series[0][0] <= series[1][0]

        # Counts are integers >= 0
        for _, cnt in series[-2:]:
            assert isinstance(cnt, int)
            assert cnt >= 0


if __name__ == "__main__":
    # Standalone execution support
    import sys as _sys

    _sys.exit(pytest.main([__file__]))
