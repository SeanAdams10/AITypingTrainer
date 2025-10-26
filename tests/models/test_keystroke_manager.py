"""Comprehensive tests for the KeystrokeManager class.

This module provides extensive test coverage for the KeystrokeManager class,
including all methods, edge cases, error conditions, and integration scenarios.
Tests aim for >95% coverage and validate the manager's behavior under various conditions.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List

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
        collection.add_keystroke(keystroke=keystroke)
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

    def test_init_with_different_database_manager(self, db_with_tables: DatabaseManager) -> None:
        """Test initialization with different database manager instances."""
        manager1 = KeystrokeManager(db_manager=db_with_tables)
        manager2 = KeystrokeManager(db_manager=db_with_tables)

        # Both managers should have the same database manager but different keystroke collections
        assert manager1.db_manager is manager2.db_manager
        assert manager1.keystrokes is not manager2.keystrokes
        assert isinstance(manager1.keystrokes, KeystrokeCollection)
        assert isinstance(manager2.keystrokes, KeystrokeCollection)
        assert len(manager1.keystrokes.raw_keystrokes) == 0
        assert len(manager2.keystrokes.raw_keystrokes) == 0


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
        loaded = manager.get_keystrokes_for_session(session_id=session_id)

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
        initial_loaded = initial_manager.require_keystrokes_for_session(session_id=session_id)
        assert len(initial_loaded) == 2
        assert [ks.keystroke_char for ks in initial_loaded] == ["a", "b"]

        assert initial_manager.delete_keystrokes_by_session(session_id=session_id) is True

        updated_collection = _build_keystroke_collection(
            session_id,
            ("m", "n", "o"),
            base_time + timedelta(seconds=5),
        )
        _persist_collection(db_with_tables, updated_collection)

        verification_manager = KeystrokeManager(db_manager=db_with_tables)
        reloaded = verification_manager.get_keystrokes_for_session(session_id=session_id)
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
            manager.require_keystrokes_for_session(session_id="non-existent-session")


class TestKeystrokeManagerSaveKeystrokes:
    """Test saving keystrokes to the database using real PostgreSQL container."""

    @pytest.fixture
    def keystroke_manager(self, db_with_tables: DatabaseManager) -> KeystrokeManager:
        """Create a keystroke manager with real database."""
        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER
        return KeystrokeManager(db_manager=db_with_tables)

    @pytest.fixture
    def setup_session_dependencies(self, db_with_tables: DatabaseManager) -> str:
        """Create all necessary FK dependencies and return a session_id."""
        session_id = str(uuid.uuid4())
        
        # Create category
        category_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            params=(category_id, f"test-category-{category_id[:8]}"),
        )
        
        # Create snippet
        snippet_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            params=(snippet_id, category_id, f"test-snippet-{snippet_id[:8]}"),
        )
        
        # Create user
        user_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
        )
        
        # Create keyboard
        keyboard_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )
        
        # Create practice session
        start = datetime.now(timezone.utc)
        db_with_tables.execute(
            query="INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, "
            "snippet_index_start, snippet_index_end, content, start_time, end_time, "
            "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=(
                session_id,
                snippet_id,
                user_id,
                keyboard_id,
                0,
                5,
                "abcde",
                start.isoformat(),
                (start + timedelta(minutes=1)).isoformat(),
                5,
                0,
                150.0,
            ),
        )
        
        return session_id

    def test_save_keystrokes_success(
        self, keystroke_manager: KeystrokeManager, setup_session_dependencies: str
    ) -> None:
        """Test successful saving of keystrokes to real database."""
        session_id = setup_session_dependencies
        
        # Create sample keystrokes
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
        
        keystroke_manager.keystrokes.raw_keystrokes = keystrokes

        result = keystroke_manager.save_keystrokes()

        assert result is True

        # Verify keystrokes were actually saved by counting them
        count = keystroke_manager.count_keystrokes_per_session(session_id=session_id)
        assert count == 3

        # Verify we can retrieve the saved keystrokes
        retrieved_keystrokes = keystroke_manager.get_keystrokes_for_session(session_id=session_id)
        assert len(retrieved_keystrokes) == 3
        
        # Verify the error keystroke is marked correctly
        error_keystrokes = [k for k in retrieved_keystrokes if k.is_error]
        assert len(error_keystrokes) == 1
        assert error_keystrokes[0].keystroke_char == "b"

    def test_save_keystrokes_empty_collection(self, keystroke_manager: KeystrokeManager) -> None:
        """Test saving when keystroke collection is empty."""
        result = keystroke_manager.save_keystrokes()

        assert result is True
        # Verify no keystrokes were saved
        count = keystroke_manager.count_keystrokes_per_session(session_id="empty-test-session")
        assert count == 0

    def test_save_keystrokes_with_special_characters(
        self, keystroke_manager: KeystrokeManager, setup_session_dependencies: str
    ) -> None:
        """Test saving keystrokes with special characters."""
        session_id = setup_session_dependencies
        special_chars = ["'", '"', "\\", "\n", "\t", "€", "😊"]
        keystrokes = []
        for i, char in enumerate(special_chars):
            keystroke = Keystroke(
                session_id=session_id,
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=char,
                expected_char=char,
                is_error=False,
                time_since_previous=100,
                text_index=i,
                key_index=i,
            )
            keystrokes.append(keystroke)
        
        keystroke_manager.keystrokes.raw_keystrokes = keystrokes
        result = keystroke_manager.save_keystrokes()
        assert result is True
        
        # Verify special characters were saved correctly
        count = keystroke_manager.count_keystrokes_per_session(session_id=session_id)
        assert count == len(special_chars)
        
        # Retrieve and verify the characters
        retrieved = keystroke_manager.get_keystrokes_for_session(session_id=session_id)
        retrieved_chars = [k.keystroke_char for k in retrieved]
        assert retrieved_chars == special_chars


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
        assert len(verifier.require_keystrokes_for_session(session_id=session_id)) == 2

        delete_manager = KeystrokeManager(db_manager=db_with_tables)
        assert delete_manager.delete_keystrokes_by_session(session_id=session_id) is True

        with pytest.raises(LookupError):
            delete_manager.require_keystrokes_for_session(session_id=session_id)

    def test_delete_nonexistent_session_keystrokes(
        self,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Deleting a session with no keystrokes should still succeed and raise on load."""

        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

        session_id = "non-exist"
        manager = KeystrokeManager(db_manager=db_with_tables)
        assert manager.delete_keystrokes_by_session(session_id=session_id) is True

        with pytest.raises(LookupError):
            manager.require_keystrokes_for_session(session_id=session_id)

        # Verify loading keystrokes for this session returns empty list
        loaded_keystrokes = manager.get_keystrokes_for_session(session_id=session_id)
        assert loaded_keystrokes == []


class TestKeystrokeManagerCountKeystrokes:
    """Test keystroke counting functionality using real PostgreSQL container."""

    @pytest.fixture
    def keystroke_manager(self, db_with_tables: DatabaseManager) -> KeystrokeManager:
        """Create a keystroke manager with real database."""
        assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER
        return KeystrokeManager(db_manager=db_with_tables)

    @pytest.fixture
    def setup_session_dependencies(self, db_with_tables: DatabaseManager) -> str:
        """Create all necessary FK dependencies and return a session_id."""
        session_id = str(uuid.uuid4())
        
        # Create category
        category_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            params=(category_id, f"test-category-{category_id[:8]}"),
        )
        
        # Create snippet
        snippet_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            params=(snippet_id, category_id, f"test-snippet-{snippet_id[:8]}"),
        )
        
        # Create user
        user_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
        )
        
        # Create keyboard
        keyboard_id = str(uuid.uuid4())
        db_with_tables.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )
        
        # Create practice session
        start = datetime.now(timezone.utc)
        db_with_tables.execute(
            query="INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, "
            "snippet_index_start, snippet_index_end, content, start_time, end_time, "
            "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=(
                session_id,
                snippet_id,
                user_id,
                keyboard_id,
                0,
                5,
                "abcde",
                start.isoformat(),
                (start + timedelta(minutes=1)).isoformat(),
                5,
                0,
                150.0,
            ),
        )
        
        return session_id

    def test_count_keystrokes_with_data(
        self, keystroke_manager: KeystrokeManager, setup_session_dependencies: str
    ) -> None:
        """Test counting keystrokes when session has data."""
        session_id = setup_session_dependencies
        
        # Create and save some keystrokes
        keystrokes = []
        for i in range(5):
            keystroke = Keystroke(
                session_id=session_id,
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=chr(97 + i),
                expected_char=chr(97 + i),
                is_error=False,
                time_since_previous=100,
                text_index=i,
                key_index=i,
            )
            keystrokes.append(keystroke)
        
        keystroke_manager.keystrokes.raw_keystrokes = keystrokes
        assert keystroke_manager.save_keystrokes() is True

        # Test counting
        result = keystroke_manager.count_keystrokes_per_session(session_id=session_id)
        assert result == 5

    def test_count_keystrokes_empty_session(self, keystroke_manager: KeystrokeManager) -> None:
        """Test counting when session has no keystrokes."""
        session_id = "empty-count-session"
        result = keystroke_manager.count_keystrokes_per_session(session_id=session_id)
        assert result == 0

    def test_count_keystrokes_nonexistent_session(self, keystroke_manager: KeystrokeManager) -> None:
        """Test counting when session doesn't exist."""
        session_id = str(uuid.uuid4())  # Random UUID that doesn't exist
        result = keystroke_manager.count_keystrokes_per_session(session_id=session_id)
        assert result == 0

    def test_count_keystrokes_after_deletion(
        self, keystroke_manager: KeystrokeManager, setup_session_dependencies: str
    ) -> None:
        """Test counting after keystrokes have been deleted."""
        session_id = setup_session_dependencies
        
        # Create and save keystrokes
        keystroke = Keystroke(
            session_id=session_id,
            keystroke_id=str(uuid.uuid4()),
            keystroke_time=datetime.now(timezone.utc),
            keystroke_char="x",
            expected_char="x",
            is_error=False,
            time_since_previous=100,
            text_index=0,
            key_index=0,
        )
        keystroke_manager.keystrokes.raw_keystrokes = [keystroke]
        assert keystroke_manager.save_keystrokes() is True
        
        # Verify count before deletion
        assert keystroke_manager.count_keystrokes_per_session(session_id=session_id) == 1
        
        # Delete and verify count is zero
        assert keystroke_manager.delete_keystrokes_by_session(session_id=session_id) is True
        assert keystroke_manager.count_keystrokes_per_session(session_id=session_id) == 0


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
            query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
            params=(category_id, f"integration-category-{category_id[:8]}"),
        )

        snippet_id = str(uuid.uuid4())
        db.execute(
            query="INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
            params=(snippet_id, category_id, f"integration-snippet-{snippet_id[:8]}"),
        )

        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())
        db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
        )
        db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )

        start = datetime.now(timezone.utc)
        db.execute(
            query="INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, "
            "snippet_index_start, snippet_index_end, content, start_time, end_time, "
            "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=(
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
            integration_manager.keystrokes.add_keystroke(keystroke=keystroke)

        assert len(integration_manager.keystrokes.raw_keystrokes) == 5

        save_result = integration_manager.save_keystrokes()
        assert save_result is True

        count = integration_manager.count_keystrokes_per_session(session_id=session_id)
        assert count == 5

        integration_manager.keystrokes.raw_keystrokes = []
        retrieved = integration_manager.get_keystrokes_for_session(session_id=session_id)
        assert len(retrieved) == 5

        delete_result = integration_manager.delete_keystrokes_by_session(session_id=session_id)
        assert delete_result is True

        count_after_delete = integration_manager.count_keystrokes_per_session(session_id=session_id)
        assert count_after_delete == 0

    def test_concurrent_session_handling(self, integration_manager: KeystrokeManager) -> None:
        """Test handling multiple sessions concurrently."""

        db = integration_manager.db_manager
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())

        db.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
        )
        db.execute(
            query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            params=(keyboard_id, user_id, "Test Keyboard"),
        )

        sessions = ["session-1", "session-2", "session-3"]
        for session_id in sessions:
            snippet_id = str(uuid.uuid4())
            category_id = str(uuid.uuid4())
            db.execute(
                query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                params=(category_id, f"TestCat_{session_id}"),
            )
            db.execute(
                query="INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
                params=(snippet_id, category_id, f"TestSnippet_{session_id}"),
            )

            now = datetime.now(timezone.utc)
            db.execute(
                query="INSERT INTO practice_sessions (session_id, user_id, keyboard_id, snippet_id, "
                "snippet_index_start, snippet_index_end, content, start_time, end_time, "
                "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                params=(
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
                integration_manager.keystrokes.add_keystroke(keystroke=keystroke)

        save_result = integration_manager.save_keystrokes()
        assert save_result is True

        for session_id in sessions:
            count = integration_manager.count_keystrokes_per_session(session_id=session_id)
            assert count == 3

        delete_result = integration_manager.delete_keystrokes_by_session(session_id=sessions[0])
        assert delete_result is True

        assert integration_manager.count_keystrokes_per_session(session_id=sessions[0]) == 0
        assert integration_manager.count_keystrokes_per_session(session_id=sessions[1]) == 3
        assert integration_manager.count_keystrokes_per_session(session_id=sessions[2]) == 3


@pytest.fixture()
def test_session(db_with_tables: DatabaseManager) -> str:
    """Create a fully-related practice session in the Postgres test database."""

    db = db_with_tables

    user_id = str(uuid.uuid4())
    db.execute(
        query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        params=(user_id, "Test", "User", f"testuser_{user_id[:8]}@example.com"),
    )

    keyboard_id = str(uuid.uuid4())
    db.execute(
        query="INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
        params=(keyboard_id, user_id, "Test Keyboard"),
    )

    category_id = str(uuid.uuid4())
    db.execute(
        query="INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        params=(category_id, f"TestCat-{category_id[:8]}"),
    )

    snippet_id = str(uuid.uuid4())
    db.execute(
        query="INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        params=(snippet_id, category_id, f"TestSnippet-{snippet_id[:8]}"),
    )

    session_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    db.execute(
        query="INSERT INTO practice_sessions (session_id, snippet_id, user_id, keyboard_id, "
        "snippet_index_start, snippet_index_end, content, start_time, end_time, "
        "actual_chars, errors, ms_per_keystroke) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        params=(
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
