"""Integration-style tests for NGramAnalyticsService.process_end_of_session orchestrator.

Validates strict sequencing and DB side effects on the success path using real DB.
"""

import uuid
from datetime import datetime, timedelta

from models.keystroke import Keystroke
from models.keystroke_collection import KeystrokeCollection
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager
from models.session import Session


def _make_clean_keystrokes(session_id: str, text: str, start_time: datetime) -> list[Keystroke]:
    ks: list[Keystroke] = []
    t = start_time
    for i, ch in enumerate(text):
        ks.append(
            Keystroke(
                session_id=session_id,
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=t,
                keystroke_char=ch,
                expected_char=ch,
                is_error=False,
                time_since_previous=100 if i > 0 else None,
                text_index=i,
            )
        )
        t = t + timedelta(milliseconds=100)
    return ks


def test_process_end_of_session_success_path(db_with_tables, test_user, test_keyboard) -> None:
    # Arrange: create snippet (for FK completeness) and a new Session not yet in DB
    from tests.models.conftest import TestSessionMethodsFixtures

    category_id = TestSessionMethodsFixtures.create_category(db_with_tables)
    snippet_id = TestSessionMethodsFixtures.create_snippet(db_with_tables, category_id)

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(seconds=5)
    session = Session(
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=10,
        content="helloworld",  # expected text for n-gram analysis
        start_time=start_dt,
        end_time=end_dt,
        actual_chars=10,
        errors=0,
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )

    # Keystrokes matching expected text (clean input)
    keystrokes = _make_clean_keystrokes(session.session_id, session.content, start_dt)

    # Use a NGramManager bound to the same test DB to ensure persistence goes to this DB
    ngram_manager = NGramManager(db_with_tables)
    service = NGramAnalyticsService(db_with_tables, ngram_manager)

    # Act: create KeystrokeCollection from keystrokes
    keystroke_collection = KeystrokeCollection()
    for k in keystrokes:
        keystroke_collection.add_keystroke(keystroke=k)

    result = service.process_end_of_session(session, keystroke_collection, save_session_first=True)

    # Assert: returned flags and counts
    assert result["session_saved"] is True
    assert result["keystrokes_saved"] is True
    assert result["ngrams_saved"] is True
    assert int(result.get("ngram_count", 0)) >= 1
    assert int(result.get("session_summary_rows", 0)) >= 1
    assert int(result.get("curr_updated", 0)) >= 1
    assert int(result.get("hist_inserted", 0)) >= 1

    # Assert: DB side effects
    # practice_sessions
    row = db_with_tables.fetchone(
        "SELECT 1 as x FROM practice_sessions WHERE session_id = ?",
        (session.session_id,),
    )
    assert row is not None

    # session_keystrokes
    ks_count = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM session_keystrokes WHERE session_id = ?",
        (session.session_id,),
    )["c"]
    assert ks_count == len(keystrokes)

    # session n-grams
    spd_count = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM session_ngram_speed WHERE session_id = ?",
        (session.session_id,),
    )["c"]
    err_count = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM session_ngram_errors WHERE session_id = ?",
        (session.session_id,),
    )["c"]
    assert spd_count >= 1
    assert err_count >= 0

    # session_ngram_summary
    sum_count = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM session_ngram_summary WHERE session_id = ?",
        (session.session_id,),
    )["c"]
    assert sum_count >= 1

    # speed summaries current and hist
    curr_any = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM ngram_speed_summary_curr",
    )["c"]
    hist_any = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM ngram_speed_summary_hist",
    )["c"]
    assert curr_any >= 1
    assert hist_any >= 1


def test_process_end_of_session_session_save_failure(db_with_tables, test_user) -> None:
    """Fails at step 1: session save should raise due to FK violation (invalid keyboard_id)."""
    from tests.models.conftest import TestSessionMethodsFixtures

    # Valid snippet/category, but invalid keyboard_id to trigger FK failure on insert
    category_id = TestSessionMethodsFixtures.create_category(db_with_tables)
    snippet_id = TestSessionMethodsFixtures.create_snippet(db_with_tables, category_id)

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(seconds=2)
    bad_keyboard_id = str(uuid.uuid4())  # not created in DB
    session = Session(
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=2,
        content="hi",
        start_time=start_dt,
        end_time=end_dt,
        actual_chars=2,
        errors=0,
        user_id=str(test_user.user_id),
        keyboard_id=bad_keyboard_id,
    )

    keystrokes = _make_clean_keystrokes(session.session_id, session.content, start_dt)

    ngram_manager = NGramManager(db_with_tables)
    service = NGramAnalyticsService(db_with_tables, ngram_manager)

    # Create KeystrokeCollection from keystrokes
    keystroke_collection = KeystrokeCollection()
    for k in keystrokes:
        keystroke_collection.add_keystroke(keystroke=k)

    with __import__("pytest").raises(Exception):
        service.process_end_of_session(session, keystroke_collection, save_session_first=True)

    # Ensure nothing got persisted to keystrokes/ngrams because session failed first
    row = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM practice_sessions WHERE session_id = ?",
        (session.session_id,),
    )
    assert row["c"] == 0


def test_process_end_of_session_keystrokes_save_failure(
    db_with_tables, test_user, test_keyboard
) -> None:
    """Fails at step 2: keystrokes save should return False due to invalid keystroke session_id."""
    from tests.models.conftest import TestSessionMethodsFixtures

    category_id = TestSessionMethodsFixtures.create_category(db_with_tables)
    snippet_id = TestSessionMethodsFixtures.create_snippet(db_with_tables, category_id)

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(seconds=2)
    session = Session(
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=3,
        content="hey",
        start_time=start_dt,
        end_time=end_dt,
        actual_chars=3,
        errors=0,
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )

    # Build keystrokes but corrupt one to have session_id=None to cause DB NOT NULL error
    ks = _make_clean_keystrokes(session.session_id, session.content, start_dt)
    ks[0].session_id = None  # force invalid value for insert

    ngram_manager = NGramManager(db_with_tables)
    service = NGramAnalyticsService(db_with_tables, ngram_manager)

    # Create KeystrokeCollection from corrupted keystrokes
    keystroke_collection = KeystrokeCollection()
    for k in ks:
        keystroke_collection.add_keystroke(keystroke=k)

    with __import__("pytest").raises(Exception):
        service.process_end_of_session(session, keystroke_collection, save_session_first=True)

    # Session should have been saved before failure
    row = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM practice_sessions WHERE session_id = ?",
        (session.session_id,),
    )
    assert row["c"] == 1

    # But no keystrokes persisted successfully (entire batch aborted by per-row failure path)
    ksc = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM session_keystrokes WHERE session_id = ?",
        (session.session_id,),
    )["c"]
    assert ksc == 0


def test_process_end_of_session_summarization_failure(
    db_with_tables, test_user, test_keyboard
) -> None:
    """Fails at step 4: drop summary table to force summarization SQL to fail after n-grams."""
    from tests.models.conftest import TestSessionMethodsFixtures

    category_id = TestSessionMethodsFixtures.create_category(db_with_tables)
    snippet_id = TestSessionMethodsFixtures.create_snippet(db_with_tables, category_id)

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(seconds=3)
    session = Session(
        snippet_id=snippet_id,
        snippet_index_start=0,
        snippet_index_end=4,
        content="test",
        start_time=start_dt,
        end_time=end_dt,
        actual_chars=4,
        errors=0,
        user_id=str(test_user.user_id),
        keyboard_id=str(test_keyboard.keyboard_id),
    )

    keystrokes = _make_clean_keystrokes(session.session_id, session.content, start_dt)

    ngram_manager = NGramManager(db_with_tables)
    service = NGramAnalyticsService(db_with_tables, ngram_manager)

    # Remove session_ngram_summary to force failure on summarization step
    db_with_tables.execute("DROP TABLE session_ngram_summary")

    # Create KeystrokeCollection from keystrokes
    keystroke_collection = KeystrokeCollection()
    for k in keystrokes:
        keystroke_collection.add_keystroke(keystroke=k)

    with __import__("pytest").raises(Exception):
        service.process_end_of_session(session, keystroke_collection, save_session_first=True)

    # Verify that up to n-gram persistence succeeded
    spd_count = db_with_tables.fetchone(
        "SELECT COUNT(*) as c FROM session_ngram_speed WHERE session_id = ?",
        (session.session_id,),
    )["c"]
    assert spd_count >= 1

    # Speed summary tables remain unaffected due to failure before step 5 (may not exist rows)
    # Just ensure no exception querying counts
    db_with_tables.fetchone("SELECT COUNT(*) as c FROM ngram_speed_summary_curr")
    db_with_tables.fetchone("SELECT COUNT(*) as c FROM ngram_speed_summary_hist")
