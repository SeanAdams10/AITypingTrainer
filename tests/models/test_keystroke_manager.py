"""Comprehensive tests for the KeystrokeManager class.

This module provides extensive test coverage for the KeystrokeManager class,
including all methods, edge cases, error conditions, and integration scenarios.
Tests aim for >95% coverage and validate the manager's behavior under various conditions.
"""
# type: ignore
# ruff: noqa
# mypy: ignore-errors
# pylint: disable=all

import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import Mock, patch

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_collection import KeystrokeCollection
from models.keystroke_manager import KeystrokeManager


def _build_keystroke_collection(
    session_id: str, characters: tuple[str, ...], start_time: datetime
) -> KeystrokeCollection:
    """Create a KeystrokeCollection populated with the provided characters."""
    collection = KeystrokeCollection()
    for index, char in enumerate(characters):
        keystroke = Keystroke(
            session_id=session_id,
            keystroke_char=char,
            expected_char=char,
            keystroke_time=start_time + timedelta(milliseconds=120 * index),
            text_index=index,
            key_index=index,
        )
        collection.add_keystroke(keystroke)
    return collection


def _persist_collection(db_manager: DatabaseManager, collection: KeystrokeCollection) -> None:
    """Persist the provided collection using KeystrokeManager.save_keystrokes."""
    manager = KeystrokeManager(db_manager=db_manager)
    manager.keystrokes = collection
    assert manager.save_keystrokes() is True


class TestKeystrokeManagerInitialization:
    """Test KeystrokeManager initialization and setup."""

    def test_init_default_database_manager(self, db_with_tables: DatabaseManager) -> None:
        """Test initialization with default database manager."""
        manager = KeystrokeManager(db_manager=db_with_tables)

        assert isinstance(manager.db_manager, DatabaseManager)
        assert isinstance(manager.keystrokes, KeystrokeCollection)
        assert len(manager.keystrokes.raw_keystrokes) == 0
        assert len(manager.keystrokes.net_keystrokes) == 0

    def test_init_custom_database_manager(self) -> None:
        """Test initialization with custom database manager."""
        mock_db = Mock(spec=DatabaseManager)
        manager = KeystrokeManager(db_manager=mock_db)

        assert manager.db_manager is mock_db
        assert isinstance(manager.keystrokes, KeystrokeCollection)
        assert len(manager.keystrokes.raw_keystrokes) == 0
        assert len(manager.keystrokes.net_keystrokes) == 0


class TestKeystrokeManagerGetKeystrokesForSession:
    """Integration-style tests for retrieving keystrokes from the database."""

    def test_get_keystrokes_for_existing_session(
        self,
        db_with_tables: DatabaseManager,
        test_session: str,
    ) -> None:
        """Persist keystrokes and ensure they can be retrieved exactly."""

        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        session_id = test_session
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        collection = _build_keystroke_collection(session_id, ("a", "b"), base_time)
        _persist_collection(db_with_tables, collection)

        manager = KeystrokeManager(db_manager=db_with_tables)
        loaded = manager.get_keystrokes_for_session(session_id)

        assert len(loaded) == 2
        assert manager.keystrokes.get_raw_count() == 2
        assert [ks.keystroke_char for ks in loaded] == ["a", "b"]
        assert [ks.keystroke_time for ks in loaded] == [
            ks.keystroke_time for ks in collection.raw_keystrokes
        ]

    def test_overwrite_session_keystrokes(
        self,
        db_with_tables: DatabaseManager,
        test_session: str,
    ) -> None:
        """Ensure overwriting an existing session replaces stored keystrokes."""

        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        session_id = test_session
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        initial_collection = _build_keystroke_collection(session_id, ("a", "b"), base_time)
        _persist_collection(db_with_tables, initial_collection)

        initial_manager = KeystrokeManager(db_manager=db_with_tables)
        initial_loaded = initial_manager.require_keystrokes_for_session(session_id)
        assert len(initial_loaded) == 2
        assert [ks.keystroke_char for ks in initial_loaded] == ["a", "b"]

        assert initial_manager.delete_keystrokes_by_session(session_id) is True

        updated_collection = _build_keystroke_collection(
            session_id,
            ("m", "n", "o"),
            base_time + timedelta(seconds=5),
        )
        _persist_collection(db_with_tables, updated_collection)

        verification_manager = KeystrokeManager(db_manager=db_with_tables)
        reloaded = verification_manager.get_keystrokes_for_session(session_id)
        assert len(reloaded) == 3
        assert [ks.keystroke_char for ks in reloaded] == ["m", "n", "o"]
        assert verification_manager.keystrokes.get_raw_count() == 3

    def test_get_keystrokes_missing_session_raises(
        self,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Ensure requesting keystrokes for an unknown session raises an error."""

        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        manager = KeystrokeManager(db_manager=db_with_tables)
        with pytest.raises(LookupError):
            manager.require_keystrokes_for_session("non-existent-session")


class TestKeystrokeManagerSaveKeystrokes:
    """Test saving keystrokes to the database."""

    @pytest.fixture
    def manager_with_mock_db(self) -> KeystrokeManager:
        """Create a keystroke manager with a mock database."""
        mock_db = Mock(spec=DatabaseManager)
        mock_db.execute_many_supported = True
        return KeystrokeManager(db_manager=mock_db)

    @pytest.fixture
    def sample_keystrokes(self) -> List[Keystroke]:
        """Create sample keystrokes for testing."""
        import uuid

        session_id = "save-test-session"
        keystrokes = []
        for i in range(3):
            keystroke = Keystroke(
                session_id=session_id,
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=chr(97 + i),
                expected_char=chr(97 + i),
                is_error=i == 1,  # Make the second one an error
                time_since_previous=100 + i * 10,
                text_index=i,
                key_index=i,
            )
            keystrokes.append(keystroke)
        return keystrokes

    def test_save_keystrokes_success(
        self, manager_with_mock_db: KeystrokeManager, sample_keystrokes: List[Keystroke]
    ) -> None:
        """Test successful saving of keystrokes."""
        manager_with_mock_db.keystrokes.raw_keystrokes = sample_keystrokes

        result = manager_with_mock_db.save_keystrokes()

        assert result is True

        execute_many_mock = manager_with_mock_db.db_manager.execute_many
        execute_many_mock.assert_called_once()

        expected_sql = (
            "INSERT INTO session_keystrokes "
            "(session_id, keystroke_id, keystroke_time, "
            "keystroke_char, expected_char, is_error, time_since_previous, "
            "text_index, key_index) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )

        called_query, called_params = execute_many_mock.call_args[0]
        assert called_query == expected_sql
        assert len(called_params) == len(sample_keystrokes)

        for i, params in enumerate(called_params):
            assert params[0] == sample_keystrokes[i].session_id
            assert params[1] == sample_keystrokes[i].keystroke_id
            assert params[2] == sample_keystrokes[i].keystroke_time.isoformat()
            assert params[3] == sample_keystrokes[i].keystroke_char
            assert params[4] == sample_keystrokes[i].expected_char
            assert params[5] == int(sample_keystrokes[i].is_error)
            assert params[6] == sample_keystrokes[i].time_since_previous
            assert params[7] == sample_keystrokes[i].text_index
            assert params[8] == sample_keystrokes[i].key_index

    def test_save_keystrokes_empty_list(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test saving when keystroke list is empty."""
        manager_with_mock_db.keystrokes.raw_keystrokes = []

        result = manager_with_mock_db.save_keystrokes()

        assert result is True
        manager_with_mock_db.db_manager.execute_many.assert_not_called()

    def test_save_keystrokes_database_error(
        self, manager_with_mock_db: KeystrokeManager, sample_keystrokes: List[Keystroke]
    ) -> None:
        """Test handling of database errors during save."""
        manager_with_mock_db.keystrokes.raw_keystrokes = sample_keystrokes
        manager_with_mock_db.db_manager.execute_many.side_effect = Exception(  # type: ignore
            "Database connection failed"
        )
        manager_with_mock_db.db_manager.execute.side_effect = Exception(  # type: ignore
            "Fallback execution failed"
        )

        with patch("sys.stderr"), patch("traceback.print_exc"):
            result = manager_with_mock_db.save_keystrokes()

        assert result is False

    def test_save_keystrokes_with_special_characters(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test saving keystrokes with special characters."""
        import uuid

        special_chars = ["'", '"', "\\", "\n", "\t", "€", "😊"]
        keystrokes = []
        for _i, char in enumerate(special_chars):
            keystroke = Keystroke(
                session_id="special-char-session",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=char,
                expected_char=char,
                is_error=False,
                time_since_previous=100,
            )
            keystrokes.append(keystroke)
        manager_with_mock_db.keystrokes.raw_keystrokes = keystrokes
        result = manager_with_mock_db.save_keystrokes()
        assert result is True
        execute_many_mock = manager_with_mock_db.db_manager.execute_many
        execute_many_mock.assert_called_once()
        called_params = execute_many_mock.call_args[0][1]
        assert len(called_params) == len(special_chars)

    def test_save_keystrokes_boolean_conversion(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test that boolean is_error is properly converted to int."""
        import uuid

        keystroke = Keystroke(
            session_id="bool-test",
            keystroke_id=str(uuid.uuid4()),
            keystroke_time=datetime.now(timezone.utc),
            keystroke_char="a",
            expected_char="b",
            is_error=True,
            time_since_previous=50,
        )
        manager_with_mock_db.keystrokes.raw_keystrokes = [keystroke]
        result = manager_with_mock_db.save_keystrokes()
        assert result is True
        params_list = manager_with_mock_db.db_manager.execute_many.call_args[0][1]
        assert params_list[0][5] == 1  # True converted to 1


class TestKeystrokeManagerDeleteKeystrokes:
    """Tests for deleting keystrokes using real database fixtures."""

    def test_delete_existing_session_keystrokes(
        self,
        db_with_tables: DatabaseManager,
        test_session: str,
    ) -> None:
        """Persist keystrokes, delete them, and ensure subsequent loads fail."""

        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        session_id = test_session
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        collection = _build_keystroke_collection(session_id, ("a", "b"), base_time)
        _persist_collection(db_with_tables, collection)

        verifier = KeystrokeManager(db_manager=db_with_tables)
        assert len(verifier.require_keystrokes_for_session(session_id)) == 2

        delete_manager = KeystrokeManager(db_manager=db_with_tables)
        assert delete_manager.delete_keystrokes_by_session(session_id) is True

        with pytest.raises(LookupError):
            delete_manager.require_keystrokes_for_session(session_id)

    def test_delete_nonexistent_session_keystrokes(
        self,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Deleting a session with no keystrokes should still succeed and raise on load."""

        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        session_id = "non-exist"
        manager = KeystrokeManager(db_manager=db_with_tables)
        assert manager.delete_keystrokes_by_session(session_id) is True

        with pytest.raises(LookupError):
            manager.require_keystrokes_for_session(session_id)

        # Verify loading keystrokes for this session returns empty list
        loaded_keystrokes = manager.get_keystrokes_for_session(session_id)
        assert loaded_keystrokes == []


class TestKeystrokeManagerCountKeystrokes:
    """Test keystroke counting functionality."""

    @pytest.fixture
    def manager_with_mock_db(self) -> KeystrokeManager:
        """Create a keystroke manager with a mock database."""
        mock_db = Mock(spec=DatabaseManager)
        return KeystrokeManager(db_manager=mock_db)

    def test_count_keystrokes_dict_result(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting with dict-like result (Row object)."""
        session_id = "count-test-session"
        mock_result = {"count": 42}
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result  # type: ignore

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 42
        manager_with_mock_db.db_manager.fetchone.assert_called_once_with(
            """
                SELECT COUNT(*) as count
                FROM session_keystrokes
                WHERE session_id = ?
                """,
            (session_id,),
        )

    def test_count_keystrokes_tuple_result(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting with tuple result."""
        session_id = "tuple-test-session"
        mock_result = (15,)  # Tuple result
        # Patch fetchone to return a tuple directly
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result  # type: ignore
        result = manager_with_mock_db.count_keystrokes_per_session(session_id)
        assert result == 15

    def test_count_keystrokes_zero_result(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting when result is zero."""
        session_id = "zero-session"
        mock_result = {"count": 0}
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result  # type: ignore

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_none_result(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting when database returns None."""
        session_id = "none-session"
        manager_with_mock_db.db_manager.fetchone.return_value = None  # type: ignore

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_none_count_value(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test counting when count value is None."""
        session_id = "none-count-session"
        mock_result = {"count": None}
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result  # type: ignore

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_database_error(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test handling of database errors during count."""
        session_id = "error-session"
        manager_with_mock_db.db_manager.fetchone.side_effect = Exception("Count failed")  # type: ignore

        with patch("builtins.print"):
            result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_result_conversion_error(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test handling of result conversion errors."""
        session_id = "conversion-error-session"
        mock_result = Mock()
        mock_result.keys = Mock(side_effect=AttributeError())

        def failing_tuple_conversion(obj: object) -> object:
            if obj is mock_result:
                raise Exception("Conversion failed")
            return tuple(obj)  # type: ignore

        manager_with_mock_db.db_manager.fetchone.return_value = mock_result  # type: ignore

        with patch("builtins.tuple", side_effect=failing_tuple_conversion):
            result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_uuid_session_id(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting with UUID session ID."""
        session_id = str(uuid.uuid4())
        mock_result = {"count": 123}
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 123


class TestKeystrokeManagerIntegration:
    """Integration tests for KeystrokeManager with real database operations."""

    @pytest.fixture
    def integration_manager(self, db_with_tables: DatabaseManager) -> KeystrokeManager:
        """Provide a keystroke manager backed by the Postgres test database."""

        return KeystrokeManager(db_manager=db_with_tables)

    def test_full_keystroke_workflow(self, integration_manager: KeystrokeManager) -> None:
        """Test complete workflow: add, save, count, retrieve, delete."""

        session_id = str(uuid.uuid4())
        db = integration_manager.db_manager

        category_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            (category_id, f"integration-category-{category_id[:8]}"),
        )

        snippet_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            (snippet_id, category_id, f"integration-snippet-{snippet_id[:8]}"),
        )

        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
        )
        db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id, user_id, "Test Keyboard"),
        )

        start = datetime.now(timezone.utc)
        db.execute(
            "INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, "
            "snippet_index_start, snippet_index_end, content, start_time, end_time, "
            "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                snippet_id,
                user_id,
                keyboard_id,
                0,
                10,
                "abcde",
                start.isoformat(),
                (start + timedelta(minutes=1)).isoformat(),
                5,
                0,
                100.0,
            ),
        )

        keystrokes: List[Keystroke] = []
        for i in range(5):
            keystroke = Keystroke(
                session_id=session_id,
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=chr(97 + i),
                expected_char=chr(97 + i),
                is_error=i == 2,
                time_since_previous=100 + i * 10,
                text_index=i,
                key_index=i,
            )
            keystrokes.append(keystroke)
            integration_manager.keystrokes.add_keystroke(keystroke)

        assert len(integration_manager.keystrokes.raw_keystrokes) == 5

        save_result = integration_manager.save_keystrokes()
        assert save_result is True

        count = integration_manager.count_keystrokes_per_session(session_id)
        assert count == 5

        integration_manager.keystrokes.raw_keystrokes = []
        retrieved = integration_manager.get_keystrokes_for_session(session_id)
        assert len(retrieved) == 5

        delete_result = integration_manager.delete_keystrokes_by_session(session_id)
        assert delete_result is True

        count_after_delete = integration_manager.count_keystrokes_per_session(session_id)
        assert count_after_delete == 0

    def test_concurrent_session_handling(self, integration_manager: KeystrokeManager) -> None:
        """Test handling multiple sessions concurrently."""

        db = integration_manager.db_manager
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())

        db.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
        )
        db.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard_id, user_id, "Test Keyboard"),
        )

        sessions = ["session-1", "session-2", "session-3"]
        for session_id in sessions:
            snippet_id = str(uuid.uuid4())
            category_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                (category_id, f"TestCat_{session_id}"),
            )
            db.execute(
                "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
                (snippet_id, category_id, f"TestSnippet_{session_id}"),
            )

            now = datetime.now(timezone.utc)
            db.execute(
                "INSERT INTO practice_sessions (session_id, user_id, keyboard_id, snippet_id, "
                "snippet_index_start, snippet_index_end, content, start_time, end_time, "
                "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    user_id,
                    keyboard_id,
                    snippet_id,
                    0,
                    10,
                    "abcde",
                    now.isoformat(),
                    (now + timedelta(seconds=30)).isoformat(),
                    5,
                    0,
                    100.0,
                ),
            )

        for session_id in sessions:
            for idx in range(3):
                keystroke = Keystroke(
                    session_id=session_id,
                    keystroke_id=str(uuid.uuid4()),
                    keystroke_time=datetime.now(timezone.utc),
                    keystroke_char="a",
                    expected_char="a",
                    is_error=False,
                    time_since_previous=100,
                    text_index=idx,
                    key_index=idx,
                )
                integration_manager.keystrokes.add_keystroke(keystroke)

        save_result = integration_manager.save_keystrokes()
        assert save_result is True

        for session_id in sessions:
            count = integration_manager.count_keystrokes_per_session(session_id)
            assert count == 3

        delete_result = integration_manager.delete_keystrokes_by_session(sessions[0])
        assert delete_result is True

        assert integration_manager.count_keystrokes_per_session(sessions[0]) == 0
        assert integration_manager.count_keystrokes_per_session(sessions[1]) == 3
        assert integration_manager.count_keystrokes_per_session(sessions[2]) == 3


@pytest.fixture()
def test_session(db_with_tables: DatabaseManager) -> str:
    """Create a fully-related practice session in the Postgres test database."""

    db = db_with_tables

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        (user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
    )

    keyboard_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
        (keyboard_id, user_id, "Test Keyboard"),
    )

    category_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        (category_id, f"TestCat-{category_id[:8]}"),
    )

    snippet_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snippet_id, category_id, f"TestSnippet-{snippet_id[:8]}"),
    )

    session_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    db.execute(
        "INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, "
        "snippet_index_start, snippet_index_end, content, start_time, end_time, "
        "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            snippet_id,
            user_id,
            keyboard_id,
            0,
            10,
            "abcdefghij",
            start_time.isoformat(),
            (start_time + timedelta(minutes=1)).isoformat(),
            10,
            0,
            100.0,
        ),
    )

    return session_id
