"""Comprehensive tests for the KeystrokeManager class.

This module provides extensive test coverage for the KeystrokeManager class,
including all methods, edge cases, error conditions, and integration scenarios.
Tests aim for >95% coverage and validate the manager's behavior under various conditions.
"""

import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Generator, List
from unittest.mock import Mock, patch

import pytest

from db.database_manager import DatabaseManager
from models.keystroke import Keystroke
from models.keystroke_manager import KeystrokeManager


class TestKeystrokeManagerInitialization:
    """Test KeystrokeManager initialization and setup."""

    def test_init_default_database_manager(self) -> None:
        """Test initialization with default database manager."""
        manager = KeystrokeManager()

        assert manager.db_manager is not None
        assert isinstance(manager.db_manager, DatabaseManager)
        assert isinstance(manager.keystroke_list, list)
        assert len(manager.keystroke_list) == 0

    def test_init_custom_database_manager(self) -> None:
        """Test initialization with custom database manager."""
        mock_db = Mock(spec=DatabaseManager)
        manager = KeystrokeManager(db_manager=mock_db)

        assert manager.db_manager is mock_db
        assert isinstance(manager.keystroke_list, list)
        assert len(manager.keystroke_list) == 0

    def test_init_none_database_manager(self) -> None:
        """Test initialization with None database manager creates default."""
        manager = KeystrokeManager(db_manager=None)

        assert manager.db_manager is not None
        assert isinstance(manager.db_manager, DatabaseManager)


class TestKeystrokeManagerAddKeystroke:
    """Test keystroke addition functionality."""

    @pytest.fixture
    def manager(self) -> KeystrokeManager:
        """Create a keystroke manager for testing."""
        return KeystrokeManager(db_manager=Mock(spec=DatabaseManager))

    @pytest.fixture
    def sample_keystroke(self) -> Keystroke:
        """Create a sample keystroke for testing."""
        import uuid

        return Keystroke(
            session_id="test-session-123",
            keystroke_id=str(uuid.uuid4()),
            keystroke_time=datetime.now(timezone.utc),
            keystroke_char="a",
            expected_char="a",
            is_error=False,
            time_since_previous=100,
        )

    def test_add_single_keystroke(
        self, manager: KeystrokeManager, sample_keystroke: Keystroke
    ) -> None:
        """Test adding a single keystroke to the manager."""
        initial_count = len(manager.keystroke_list)

        manager.add_keystroke(sample_keystroke)

        assert len(manager.keystroke_list) == initial_count + 1
        assert manager.keystroke_list[0] is sample_keystroke

    def test_add_multiple_keystrokes(self, manager: KeystrokeManager) -> None:
        """Test adding multiple keystrokes maintains order."""
        keystrokes = []
        for _i in range(5):
            keystroke = Keystroke(
                session_id=f"session-{_i}",
                keystroke_id=str(_i),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=chr(97 + _i),
                expected_char=chr(97 + _i),
                is_error=False,
                time_since_previous=100 + _i,
            )
            manager.add_keystroke(keystroke)
            keystrokes.append(keystroke)
        assert len(manager.keystroke_list) == 5
        for _i, keystroke in enumerate(keystrokes):
            assert manager.keystroke_list[_i] is keystroke

    def test_add_keystroke_with_error(self, manager: KeystrokeManager) -> None:
        """Test adding a keystroke with error flag."""
        import uuid

        error_keystroke = Keystroke(
            session_id="error-session",
            keystroke_id=str(uuid.uuid4()),
            keystroke_time=datetime.now(timezone.utc),
            keystroke_char="x",
            expected_char="a",
            is_error=True,
            time_since_previous=200,
        )
        manager.add_keystroke(error_keystroke)
        assert len(manager.keystroke_list) == 1
        assert manager.keystroke_list[0].is_error is True
        assert manager.keystroke_list[0].keystroke_char == "x"
        assert manager.keystroke_list[0].expected_char == "a"


class TestKeystrokeManagerGetKeystrokesForSession:
    """Test retrieving keystrokes for a specific session."""

    @pytest.fixture
    def manager(self) -> KeystrokeManager:
        """Create a keystroke manager for testing."""
        return KeystrokeManager(db_manager=Mock(spec=DatabaseManager))

    @patch("models.keystroke.Keystroke.get_for_session")
    def test_get_keystrokes_for_session_success(
        self, mock_get_for_session: Mock, manager: KeystrokeManager
    ) -> None:
        """Test successful retrieval of keystrokes for a session."""
        session_id = "test-session-456"
        mock_keystrokes = [Mock(spec=Keystroke), Mock(spec=Keystroke), Mock(spec=Keystroke)]
        mock_get_for_session.return_value = mock_keystrokes

        result = manager.get_keystrokes_for_session(session_id)

        mock_get_for_session.assert_called_once_with(session_id)
        assert result == mock_keystrokes
        assert manager.keystroke_list == mock_keystrokes

    @patch("models.keystroke.Keystroke.get_for_session")
    def test_get_keystrokes_for_session_empty(
        self, mock_get_for_session: Mock, manager: KeystrokeManager
    ) -> None:
        """Test retrieval when no keystrokes exist for session."""
        session_id = "empty-session"
        mock_get_for_session.return_value = []

        result = manager.get_keystrokes_for_session(session_id)

        mock_get_for_session.assert_called_once_with(session_id)
        assert result == []
        assert manager.keystroke_list == []

    @patch("models.keystroke.Keystroke.get_for_session")
    def test_get_keystrokes_replaces_existing_list(
        self, mock_get_for_session: Mock, manager: KeystrokeManager
    ) -> None:
        """Test that getting keystrokes replaces the existing list."""
        # Add some keystrokes first
        manager.keystroke_list = [Mock(spec=Keystroke), Mock(spec=Keystroke)]

        session_id = "replacement-session"
        mock_keystrokes = [Mock(spec=Keystroke)]
        mock_get_for_session.return_value = mock_keystrokes

        result = manager.get_keystrokes_for_session(session_id)

        assert len(manager.keystroke_list) == 1
        assert manager.keystroke_list == mock_keystrokes
        assert result == mock_keystrokes

    @patch("models.keystroke.Keystroke.get_for_session")
    def test_get_keystrokes_with_uuid_session_id(
        self, mock_get_for_session: Mock, manager: KeystrokeManager
    ) -> None:
        """Test retrieval with UUID formatted session ID."""
        session_id = str(uuid.uuid4())
        mock_keystrokes = [Mock(spec=Keystroke)]
        mock_get_for_session.return_value = mock_keystrokes

        result = manager.get_keystrokes_for_session(session_id)

        mock_get_for_session.assert_called_once_with(session_id)
        assert result == mock_keystrokes


class TestKeystrokeManagerSaveKeystrokes:
    """Test saving keystrokes to the database."""

    @pytest.fixture
    def manager_with_mock_db(self) -> KeystrokeManager:
        """Create a keystroke manager with a mock database."""
        mock_db = Mock(spec=DatabaseManager)
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
            )
            keystrokes.append(keystroke)
        return keystrokes

    def test_save_keystrokes_success(
        self, manager_with_mock_db: KeystrokeManager, sample_keystrokes: List[Keystroke]
    ) -> None:
        """Test successful saving of keystrokes."""
        manager_with_mock_db.keystroke_list = sample_keystrokes

        result = manager_with_mock_db.save_keystrokes()

        assert result is True
        assert manager_with_mock_db.db_manager.execute.call_count == 3

        # Verify the SQL and parameters for each call
        calls = manager_with_mock_db.db_manager.execute.call_args_list
        expected_sql = (
            "INSERT INTO session_keystrokes "
            "(session_id, keystroke_id, keystroke_time, "
            "keystroke_char, expected_char, is_error, time_since_previous) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )

        for i, call_args in enumerate(calls):
            sql, params = call_args[0]
            assert sql == expected_sql
            assert params[0] == sample_keystrokes[i].session_id
            assert params[1] == sample_keystrokes[i].keystroke_id
            assert params[2] == sample_keystrokes[i].keystroke_time.isoformat()
            assert params[3] == sample_keystrokes[i].keystroke_char
            assert params[4] == sample_keystrokes[i].expected_char
            assert params[5] == int(sample_keystrokes[i].is_error)
            assert params[6] == sample_keystrokes[i].time_since_previous

    def test_save_keystrokes_empty_list(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test saving when keystroke list is empty."""
        manager_with_mock_db.keystroke_list = []

        result = manager_with_mock_db.save_keystrokes()

        assert result is True
        manager_with_mock_db.db_manager.execute.assert_not_called()

    def test_save_keystrokes_database_error(
        self, manager_with_mock_db: KeystrokeManager, sample_keystrokes: List[Keystroke]
    ) -> None:
        """Test handling of database errors during save."""
        manager_with_mock_db.keystroke_list = sample_keystrokes
        manager_with_mock_db.db_manager.execute.side_effect = Exception(
            "Database connection failed"
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
        manager_with_mock_db.keystroke_list = keystrokes
        result = manager_with_mock_db.save_keystrokes()
        assert result is True
        assert manager_with_mock_db.db_manager.execute.call_count == len(special_chars)

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
        manager_with_mock_db.keystroke_list = [keystroke]
        result = manager_with_mock_db.save_keystrokes()
        assert result is True
        call_args = manager_with_mock_db.db_manager.execute.call_args
        params = call_args[0][1]
        assert params[5] == 1  # True converted to 1


class TestKeystrokeManagerDeleteKeystrokes:
    """Test keystroke deletion functionality."""

    @pytest.fixture
    def manager_with_mock_db(self) -> KeystrokeManager:
        """Create a keystroke manager with a mock database."""
        mock_db = Mock(spec=DatabaseManager)
        return KeystrokeManager(db_manager=mock_db)

    def test_delete_keystrokes_by_session_success(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test successful deletion of keystrokes by session ID."""
        session_id = "delete-test-session"

        result = manager_with_mock_db.delete_keystrokes_by_session(session_id)

        assert result is True
        manager_with_mock_db.db_manager.execute.assert_called_once_with(
            "DELETE FROM session_keystrokes WHERE session_id = ?", (session_id,)
        )

    def test_delete_keystrokes_by_session_database_error(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test handling of database errors during deletion."""
        session_id = "error-session"
        manager_with_mock_db.db_manager.execute.side_effect = Exception("Delete failed")

        with patch("sys.stderr"), patch("traceback.print_exc"):
            result = manager_with_mock_db.delete_keystrokes_by_session(session_id)

        assert result is False

    def test_delete_keystrokes_by_session_uuid(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test deletion with UUID session ID."""
        session_id = str(uuid.uuid4())

        result = manager_with_mock_db.delete_keystrokes_by_session(session_id)

        assert result is True
        manager_with_mock_db.db_manager.execute.assert_called_once_with(
            "DELETE FROM session_keystrokes WHERE session_id = ?", (session_id,)
        )

    def test_delete_all_keystrokes_success(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test successful deletion of all keystrokes."""
        result = manager_with_mock_db.delete_all_keystrokes()

        assert result is True
        manager_with_mock_db.db_manager.execute.assert_called_once_with(
            "DELETE FROM session_keystrokes"
        )

    def test_delete_all_keystrokes_database_error(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test handling of database errors during delete all."""
        manager_with_mock_db.db_manager.execute.side_effect = Exception("Delete all failed")

        with patch("builtins.print"):
            result = manager_with_mock_db.delete_all_keystrokes()

        assert result is False

    def test_delete_keystrokes_empty_session_id(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test deletion with empty session ID."""
        result = manager_with_mock_db.delete_keystrokes_by_session("")

        assert result is True
        manager_with_mock_db.db_manager.execute.assert_called_once_with(
            "DELETE FROM session_keystrokes WHERE session_id = ?", ("",)
        )


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
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result

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
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result
        result = manager_with_mock_db.count_keystrokes_per_session(session_id)
        assert result == 15

    def test_count_keystrokes_zero_result(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting when result is zero."""
        session_id = "zero-session"
        mock_result = {"count": 0}
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_none_result(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test counting when database returns None."""
        session_id = "none-session"
        manager_with_mock_db.db_manager.fetchone.return_value = None

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_none_count_value(
        self, manager_with_mock_db: KeystrokeManager
    ) -> None:
        """Test counting when count value is None."""
        session_id = "none-count-session"
        mock_result = {"count": None}
        manager_with_mock_db.db_manager.fetchone.return_value = mock_result

        result = manager_with_mock_db.count_keystrokes_per_session(session_id)

        assert result == 0

    def test_count_keystrokes_database_error(self, manager_with_mock_db: KeystrokeManager) -> None:
        """Test handling of database errors during count."""
        session_id = "error-session"
        manager_with_mock_db.db_manager.fetchone.side_effect = Exception("Count failed")

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
            return tuple(obj)

        manager_with_mock_db.db_manager.fetchone.return_value = mock_result

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
    def test_db_path(self) -> Generator[str, None, None]:
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)

        # Setup database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE session_keystrokes (
                session_id TEXT NOT NULL,
                keystroke_id INTEGER NOT NULL,
                keystroke_time DATETIME NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_error BOOLEAN NOT NULL,
                time_since_previous INTEGER,
                PRIMARY KEY (session_id, keystroke_id)
            )
        """)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        os.unlink(db_path)

    @pytest.fixture
    def integration_manager(self) -> KeystrokeManager:
        db = DatabaseManager(":memory:")
        db.init_tables()
        return KeystrokeManager(db_manager=db)

    def test_full_keystroke_workflow(self, integration_manager: KeystrokeManager) -> None:
        """Test complete workflow: add, save, count, retrieve, delete."""
        import uuid

        session_id = str(uuid.uuid4())
        # Insert a matching session into the database
        db = integration_manager.db_manager
        db.init_tables()
        # Ensure session_keystrokes table is correct for UUID keystroke_id
        db.execute("DROP TABLE IF EXISTS session_keystrokes")
        db.execute(
            """
            CREATE TABLE session_keystrokes (
                keystroke_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                keystroke_time TEXT NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_error INTEGER NOT NULL,
                time_since_previous INTEGER,
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE
            )
            """
        )
        category_id = str(uuid.uuid4())
        # Insert a matching category into the database
        db.execute(
            """
            INSERT INTO categories (category_id, category_name) VALUES (?, ?)
            """,
            (category_id, "integration-category"),
        )
        snippet_id = str(uuid.uuid4())
        # Insert a matching snippet into the database
        db.execute(
            """
            INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)
            """,
            (snippet_id, category_id, "integration-snippet"),
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
                "2025-06-10T12:00:00",
                "2025-06-10T12:01:00",
                5,
                0,
                100.0,
            ),
        )
        # Create test keystrokes
        keystrokes = []
        for i in range(5):
            keystroke = Keystroke(
                session_id=session_id,
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=chr(97 + i),
                expected_char=chr(97 + i),
                is_error=i == 2,  # Make one an error
                time_since_previous=100 + i * 10,  # Always integer
            )
            keystrokes.append(keystroke)
            integration_manager.add_keystroke(keystroke)
        # Verify keystrokes are in memory
        assert len(integration_manager.keystroke_list) == 5
        # Save to database
        save_result = integration_manager.save_keystrokes()
        assert save_result is True
        # Count keystrokes
        count = integration_manager.count_keystrokes_per_session(session_id)
        assert count == 5
        # Clear in-memory list and retrieve from database
        integration_manager.keystroke_list = []
        with patch.object(Keystroke, "get_for_session", return_value=keystrokes):
            retrieved = integration_manager.get_keystrokes_for_session(session_id)
            assert len(retrieved) == 5
        # Delete keystrokes
        delete_result = integration_manager.delete_keystrokes_by_session(session_id)
        assert delete_result is True
        # Verify deletion
        count_after_delete = integration_manager.count_keystrokes_per_session(session_id)
        assert count_after_delete == 0

    def test_concurrent_session_handling(self, integration_manager: KeystrokeManager) -> None:
        """Test handling multiple sessions concurrently."""
        db = integration_manager.db_manager
        import uuid
        from datetime import datetime, timezone

        # Create a user and keyboard
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
        # Create sessions in practice_sessions
        sessions = ["session-1", "session-2", "session-3"]
        for session_id in sessions:
            snippet_id = str(uuid.uuid4())
            # Insert category and snippet for this snippet_id
            category_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
                (category_id, f"TestCat_{session_id}"),
            )
            db.execute(
                "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
                (snippet_id, category_id, f"TestSnippet_{session_id}"),
            )
            db.execute(
                "INSERT INTO practice_sessions (session_id, user_id, keyboard_id, snippet_id, "
                "snippet_index_start, snippet_index_end, content, start_time, end_time, "
                "actual_chars, errors, ms_per_keystroke) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    user_id,
                    keyboard_id,
                    snippet_id,
                    0,
                    10,
                    "abcde",
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    5,
                    0,
                    100.0,
                ),
            )
        # Add keystrokes for multiple sessions
        for session_id in sessions:
            for _ in range(3):
                keystroke = Keystroke(
                    session_id=session_id,
                    keystroke_id=None,  # Let DB autoincrement
                    keystroke_time=datetime.now(timezone.utc),
                    keystroke_char="a",
                    expected_char="a",
                    is_error=False,
                    time_since_previous=100,
                )
                integration_manager.add_keystroke(keystroke)
        # Save all keystrokes
        save_result = integration_manager.save_keystrokes()
        assert save_result is True

        # Verify counts for each session
        for session_id in sessions:
            count = integration_manager.count_keystrokes_per_session(session_id)
            assert count == 3

        # Delete one session
        delete_result = integration_manager.delete_keystrokes_by_session(sessions[0])
        assert delete_result is True

        # Verify selective deletion
        assert integration_manager.count_keystrokes_per_session(sessions[0]) == 0
        assert integration_manager.count_keystrokes_per_session(sessions[1]) == 3
        assert integration_manager.count_keystrokes_per_session(sessions[2]) == 3


class TestKeystrokeManagerEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def manager(self) -> KeystrokeManager:
        """Create a keystroke manager for testing."""
        return KeystrokeManager(db_manager=Mock(spec=DatabaseManager))

    def test_extreme_session_id_values(self, manager: KeystrokeManager) -> None:
        """Test with extreme session ID values."""
        extreme_ids = [
            "",  # Empty string
            "a" * 1000,  # Very long string
            "special-chars-!@#$%^&*()",  # Special characters
            "unicode-测试",  # Unicode characters
            str(uuid.uuid4()),  # Standard UUID
        ]

        for session_id in extreme_ids:
            # Test counting
            manager.db_manager.fetchone.return_value = {"count": 1}
            count = manager.count_keystrokes_per_session(session_id)
            assert count == 1

            # Test deletion
            manager.db_manager.execute.return_value = None
            result = manager.delete_keystrokes_by_session(session_id)
            assert result is True

    def test_extreme_keystroke_values(self, manager: KeystrokeManager) -> None:
        """Test with extreme keystroke values."""
        extreme_keystrokes = [
            Keystroke(
                session_id="extreme-test",
                keystroke_id=str(999999999),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char="a",
                expected_char="a",
                is_error=False,
                time_since_previous=999999,
            ),
            Keystroke(
                session_id="extreme-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char="b",
                expected_char="b",
                is_error=False,
                time_since_previous=0,
            ),
            Keystroke(
                session_id="extreme-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char="c",
                expected_char="c",
                is_error=False,
                time_since_previous=-1,
            ),
        ]
        for k in extreme_keystrokes:
            manager.add_keystroke(k)
        assert len(manager.keystroke_list) == 3
        # Test saving extreme values
        result = manager.save_keystrokes()
        assert result is True

    def test_unicode_and_special_characters(self, manager: KeystrokeManager) -> None:
        """Test handling of Unicode and special characters in keystrokes."""
        import uuid

        special_chars = [
            "🙂",
            "测试",
            "café",
            "Ω",
            "\n",
            "\t",
            "\\",
            "'",
            '"',
            "\0",
        ]
        for _i, char in enumerate(special_chars):
            keystroke = Keystroke(
                session_id="unicode-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=char,
                expected_char=char,
                is_error=False,
                time_since_previous=100,  # Always integer
            )
            manager.add_keystroke(keystroke)
        assert len(manager.keystroke_list) == len(special_chars)
        result = manager.save_keystrokes()
        assert result is True
        assert manager.db_manager.execute.call_count == len(special_chars)

    def test_memory_management_large_list(self, manager: KeystrokeManager) -> None:
        """Test memory management with large keystroke lists."""
        import uuid

        # Add a large number of keystrokes
        large_count = 10000
        for _i in range(large_count):
            keystroke = Keystroke(
                session_id="memory-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char="a",
                expected_char="a",
                is_error=False,
                time_since_previous=100,  # Always integer
            )
            manager.add_keystroke(keystroke)
        assert len(manager.keystroke_list) == large_count
        # Test that list replacement works with large lists
        with patch("models.keystroke.Keystroke.get_for_session", return_value=[]):
            manager.keystroke_list = []


class TestKeystrokeManagerErrorHandling:
    """Test error handling and recovery scenarios."""

    @pytest.fixture
    def manager(self) -> KeystrokeManager:
        """Create a keystroke manager for testing."""
        return KeystrokeManager(db_manager=Mock(spec=DatabaseManager))

    def test_database_connection_failure(self, manager: KeystrokeManager) -> None:
        """Test handling of database connection failures."""
        import uuid

        manager.db_manager.execute.side_effect = Exception("Connection lost")
        keystroke = Keystroke(
            session_id="error-test",
            keystroke_id=str(uuid.uuid4()),
            keystroke_time=datetime.now(timezone.utc),
            keystroke_char="a",
            expected_char="a",
            is_error=False,
            time_since_previous=100,
        )
        manager.add_keystroke(keystroke)
        result = manager.save_keystrokes()
        assert result is False

    def test_invalid_keystroke_data(self, manager: KeystrokeManager) -> None:
        """Test handling of invalid keystroke data during save."""
        # Create a keystroke with invalid datetime
        keystroke = Mock(spec=Keystroke)
        keystroke.session_id = "invalid-test"
        keystroke.keystroke_id = 1
        keystroke.keystroke_time = Mock()
        keystroke.keystroke_time.isoformat.side_effect = Exception("Invalid datetime")
        keystroke.keystroke_char = "a"
        keystroke.expected_char = "a"
        keystroke.is_error = False
        keystroke.time_since_previous = 100

        manager.keystroke_list = [keystroke]

        with patch("sys.stderr"), patch("traceback.print_exc"):
            result = manager.save_keystrokes()

        assert result is False

    def test_partial_save_failure(self, manager: KeystrokeManager) -> None:
        """Test handling when some keystrokes save successfully and others fail."""
        import uuid

        keystrokes = []
        for i in range(3):
            keystroke = Keystroke(
                session_id="partial-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=chr(97 + i),
                expected_char=chr(97 + i),
                is_error=False,
                time_since_previous=100,
            )
            keystrokes.append(keystroke)
        manager.keystroke_list = keystrokes
        manager.db_manager.execute.side_effect = [None, Exception("Save failed"), None]
        result = manager.save_keystrokes()
        assert result is False

    def test_network_timeout_simulation(self, manager: KeystrokeManager) -> None:
        """Test handling of network timeout-like errors."""
        import time
        import uuid

        def slow_execute(*args: object, **kwargs: object) -> object:
            time.sleep(0.1)  # Simulate slow operation
            raise TimeoutError("Database timeout")

        manager.db_manager.execute.side_effect = slow_execute
        keystroke = Keystroke(
            session_id="timeout-test",
            keystroke_id=str(uuid.uuid4()),
            keystroke_time=datetime.now(timezone.utc),
            keystroke_char="a",
            expected_char="a",
            is_error=False,
            time_since_previous=100,
        )
        manager.add_keystroke(keystroke)
        result = manager.save_keystrokes()
        assert result is False


class TestKeystrokeManagerCompatibility:
    """Test compatibility with different data types and interfaces."""

    @pytest.fixture
    def manager(self) -> KeystrokeManager:
        """Create a keystroke manager for testing."""
        return KeystrokeManager(db_manager=Mock(spec=DatabaseManager))

    def test_different_datetime_formats(self, manager: KeystrokeManager) -> None:
        """Test handling of different datetime formats."""
        import uuid
        from datetime import datetime, timezone

        datetime_variants = [
            datetime.now(),  # Naive datetime
            datetime.now(timezone.utc),  # UTC datetime
            datetime(2023, 1, 1, 12, 0, 0),  # Specific datetime
            datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc),  # Unix epoch
        ]
        for i, dt in enumerate(datetime_variants):
            keystroke = Keystroke(
                session_id=f"datetime-test-{i}",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=dt,
                keystroke_char="a",
                expected_char="a",
                is_error=False,
                time_since_previous=100,
            )
            manager.add_keystroke(keystroke)
        assert len(manager.keystroke_list) == len(datetime_variants)

    def test_boolean_variations(self, manager: KeystrokeManager) -> None:
        """Test handling of different boolean representations."""
        import uuid

        boolean_variants = [False, True]  # Ensure order: False, then True
        for _i, is_error in enumerate(boolean_variants):
            keystroke = Keystroke(
                session_id="bool-test",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char="a",
                expected_char="b" if is_error else "a",
                is_error=is_error,
                time_since_previous=100,
            )
            manager.add_keystroke(keystroke)
        assert len(manager.keystroke_list) == len(boolean_variants)

    def test_numeric_edge_cases(self, manager: KeystrokeManager) -> None:
        """Test handling of numeric edge cases."""
        numeric_cases = [
            (0, 0),  # Zero values
            (1, 1),  # Minimum positive
            (999999, 999999),  # Large values
            (-1, 0),  # Negative keystroke_id (unusual but possible)
        ]
        for _i, (keystroke_id, time_since_previous) in enumerate(numeric_cases):
            keystroke = Keystroke(
                session_id="numeric-test",
                keystroke_id=str(keystroke_id),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char="a",
                expected_char="a",
                is_error=False,
                time_since_previous=time_since_previous,
            )
            manager.add_keystroke(keystroke)
        assert len(manager.keystroke_list) == len(numeric_cases)

    def test_string_encoding_variants(self, manager: KeystrokeManager) -> None:
        """Test handling of various string encodings and formats."""
        import uuid

        string_variants = [
            ("ASCII", "a", "a"),  # Standard ASCII
            ("UTF-8", "café", "café"),  # UTF-8 with accents
            ("Unicode", "🎯", "🎯"),  # Unicode emoji
            ("Escape", "\n", "\n"),  # Escaped characters
            ("Mixed", "a🎯b", "a🎯b"),  # Mixed encoding
        ]
        for _i, (desc, keystroke_char, expected_char) in enumerate(string_variants):
            keystroke = Keystroke(
                session_id=f"encoding-test-{desc}",
                keystroke_id=str(uuid.uuid4()),
                keystroke_time=datetime.now(timezone.utc),
                keystroke_char=keystroke_char,
                expected_char=expected_char,
                is_error=False,
                time_since_previous=100,
            )
            manager.add_keystroke(keystroke)
        assert len(manager.keystroke_list) == len(string_variants)


@pytest.fixture(scope="module")
def test_user(request: pytest.FixtureRequest) -> str:
    db: DatabaseManager = getattr(request, "db", None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        (user_id, f"user_{user_id}", f"user_{user_id}@example.com"),
    )
    return user_id


@pytest.fixture(scope="module")
def test_keyboard(request: pytest.FixtureRequest, test_user: str) -> str:
    db: DatabaseManager = getattr(request, "db", None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    keyboard_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
        (keyboard_id, test_user, "Test Keyboard"),
    )
    return keyboard_id


@pytest.fixture(scope="module")
def test_session(request: pytest.FixtureRequest, test_user: str, test_keyboard: str) -> str:
    db: DatabaseManager = getattr(request, "db", None)
    if db is None:
        db = DatabaseManager(":memory:")
        db.init_tables()
    session_id = str(uuid.uuid4())
    snippet_id = str(uuid.uuid4())  # Use a new snippet_id for each test session
    # Insert a dummy snippet for foreign key constraint
    db.execute(
        "INSERT INTO snippets (snippet_id, category_id, snippet_name) VALUES (?, ?, ?)",
        (snippet_id, str(uuid.uuid4()), "Test Snippet"),
    )
    db.execute(
        """
        INSERT INTO practice_sessions (
            session_id, snippet_id, user_id, keyboard_id,
            snippet_index_start, snippet_index_end, content,
            start_time, end_time, actual_chars, errors, ms_per_keystroke
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            snippet_id,
            test_user,
            test_keyboard,
            0,
            10,
            "abcdefghij",
            "2025-06-10T12:00:00",
            "2025-06-10T12:01:00",
            10,
            0,
            100.0,
        ),
    )
    return session_id


@pytest.fixture
def manager(test_db_path: str) -> KeystrokeManager:
    db = DatabaseManager(test_db_path)
    return KeystrokeManager(db_manager=db)
