"""Integration tests for PostgresKeysetRepository with real PostgreSQL database.

Tests SCD-2 history tracking, checksum no-op detection, audit trail, and business rules.
Uses DatabaseManager for connection to Docker PostgreSQL.
"""

from uuid import uuid4

import pytest

from db.database_manager import DatabaseManager
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_repository_postgres import PostgresKeysetRepository


@pytest.fixture
def repo(db_with_tables: DatabaseManager) -> PostgresKeysetRepository:
    """Create PostgresKeysetRepository."""
    return PostgresKeysetRepository(db_with_tables)


@pytest.fixture
def keyboard_id(db_with_tables: DatabaseManager) -> str:
    """Create test keyboard ID with database record."""
    kbd_id = str(uuid4())
    user_id = str(uuid4())

    # Insert test user first
    db_with_tables.execute(
        query="""
            INSERT INTO users (user_id, first_name, surname, email_address)
            VALUES (%s, %s, %s, %s)
        """,
        params=(user_id, "Test", "User", "test@example.com"),
    )

    # Insert test keyboard record
    db_with_tables.execute(
        query="""
            INSERT INTO keyboards (keyboard_id, user_id, keyboard_name, target_ms_per_keystroke)
            VALUES (%s, %s, %s, %s)
        """,
        params=(kbd_id, user_id, "Test Keyboard", 600),
    )

    return kbd_id


@pytest.fixture
def clean_tables(db_with_tables: DatabaseManager) -> None:
    """Clean keyset tables before each test."""
    db_with_tables.execute(query="DELETE FROM keyset_keys_history", params=())
    db_with_tables.execute(query="DELETE FROM keyset_history", params=())
    db_with_tables.execute(query="DELETE FROM keyset_keys", params=())
    db_with_tables.execute(query="DELETE FROM keyset", params=())


class TestPostgresKeysetRepositoryBasicCRUD:
    """Test basic CRUD operations."""

    def test_save_new_keyset_inserts_record(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test saving new keyset inserts main record and history."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="b", is_new_key=True),
            ],
        )

        repo.save(keyset, updated_by=str(uuid4()))

        # Verify main record
        retrieved = repo.get_by_id(str(keyset.keyset_id))
        assert retrieved is not None
        assert retrieved.keyset_name == "Test Keyset"
        assert retrieved.progression_order == 1
        assert len(retrieved.keys) == 2

    def test_get_by_id_returns_none_for_nonexistent(
        self, repo: PostgresKeysetRepository, clean_tables: None
    ) -> None:
        """Test get_by_id returns None for non-existent ID."""
        result = repo.get_by_id(str(uuid4()))
        assert result is None

    def test_list_for_keyboard_returns_empty_for_no_keysets(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test list_for_keyboard returns empty list when no keysets exist."""
        result = repo.list_for_keyboard(keyboard_id)
        assert result == []

    def test_list_for_keyboard_orders_by_progression(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test list_for_keyboard returns keysets ordered by progression."""
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="c", is_new_key=True)],
        )
        keyset2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        repo.save(keyset1, updated_by=str(uuid4()))
        repo.save(keyset2, updated_by=str(uuid4()))

        result = repo.list_for_keyboard(keyboard_id)

        assert len(result) == 2
        assert result[0].keyset_name == "First"
        assert result[0].progression_order == 1
        assert result[1].keyset_name == "Second"
        assert result[1].progression_order == 2

    def test_delete_removes_keyset(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test delete removes keyset from main table."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete",
            progression_order=1,
            keys=[KeysetKey(key_char="x", is_new_key=True)],
        )
        repo.save(keyset, updated_by=str(uuid4()))

        success = repo.delete(str(keyset.keyset_id), deleted_by=str(uuid4()))

        assert success is True
        assert repo.get_by_id(str(keyset.keyset_id)) is None

    def test_delete_returns_false_for_nonexistent(
        self, repo: PostgresKeysetRepository, clean_tables: None
    ) -> None:
        """Test delete returns False for non-existent keyset."""
        result = repo.delete(str(uuid4()))
        assert result is False


class TestPostgresKeysetRepositorySCD2History:
    """Test SCD-2 history tracking."""

    def test_save_new_creates_history_with_version_1(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test saving new keyset creates history record with version 1."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="History Test",
            progression_order=1,
            keys=[KeysetKey(key_char="h", is_new_key=True)],
        )

        repo.save(keyset, updated_by=str(uuid4()))

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT version_no, action, is_current FROM keyset_history WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )

        assert len(history) == 1
        assert history[0]["version_no"] == 1
        assert history[0]["action"] == "INSERT"
        assert history[0]["is_current"] == 1

    def test_save_update_increments_version(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test updating keyset increments version and closes old history."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Original",
            progression_order=1,
            keys=[KeysetKey(key_char="o", is_new_key=True)],
        )
        repo.save(keyset, updated_by=str(uuid4()))

        # Update
        keyset.keyset_name = "Updated"
        repo.save(keyset, updated_by=str(uuid4()))

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT version_no, action, is_current FROM keyset_history WHERE keyset_id = %s ORDER BY version_no",
            params=(str(keyset.keyset_id),),
        )

        assert len(history) == 2
        assert history[0]["version_no"] == 1
        assert history[0]["action"] == "INSERT"
        assert history[0]["is_current"] == 0  # Closed
        assert history[1]["version_no"] == 2
        assert history[1]["action"] == "UPDATE"
        assert history[1]["is_current"] == 1  # Current

    def test_save_update_closes_old_valid_to_dt(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test updating keyset sets valid_to_dt on old version."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Time Test",
            progression_order=1,
            keys=[KeysetKey(key_char="t", is_new_key=True)],
        )
        repo.save(keyset, updated_by=str(uuid4()))

        # Update
        keyset.keyset_name = "Time Updated"
        repo.save(keyset, updated_by=str(uuid4()))

        # Query old history
        old_history = db_with_tables.fetchone(
            query="SELECT valid_to_dt FROM keyset_history WHERE keyset_id = %s AND version_no = 1",
            params=(str(keyset.keyset_id),),
        )

        assert old_history["valid_to_dt"] != "9999-12-31 23:59:59"

    def test_delete_creates_delete_history_record(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test delete creates DELETE action in history."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete",
            progression_order=1,
            keys=[KeysetKey(key_char="d", is_new_key=True)],
        )
        repo.save(keyset, updated_by=str(uuid4()))

        repo.delete(str(keyset.keyset_id), deleted_by=str(uuid4()))

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT version_no, action FROM keyset_history WHERE keyset_id = %s ORDER BY version_no",
            params=(str(keyset.keyset_id),),
        )

        assert len(history) == 2
        assert history[0]["action"] == "INSERT"
        assert history[1]["action"] == "DELETE"


class TestPostgresKeysetRepositoryChecksumNoOp:
    """Test checksum no-op detection."""

    def test_save_with_no_changes_is_no_op(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test saving unchanged keyset skips history insert."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Unchanged",
            progression_order=1,
            keys=[KeysetKey(key_char="u", is_new_key=True)],
        )
        repo.save(keyset, updated_by=str(uuid4()))

        # Save again without changes
        repo.save(keyset, updated_by=str(uuid4()))

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT COUNT(*) as cnt FROM keyset_history WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )

        assert history[0]["cnt"] == 1  # Only INSERT, no UPDATE

    def test_save_with_key_changes_creates_history(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test saving with key changes creates new history."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Key Change",
            progression_order=1,
            keys=[KeysetKey(key_char="k", is_new_key=True)],
        )
        repo.save(keyset, updated_by=str(uuid4()))

        # Add key
        keyset.keys.append(KeysetKey(key_char="l", is_new_key=True))
        repo.save(keyset, updated_by=str(uuid4()))

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT COUNT(*) as cnt FROM keyset_history WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )

        assert history[0]["cnt"] == 2  # INSERT + UPDATE


class TestPostgresKeysetRepositoryBusinessRules:
    """Test business rule validation."""

    def test_validate_key_progression_uniqueness_finds_violations(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test validation finds keys in earlier progressions."""
        # Create progression 1 with 'a', 'b'
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Prog 1",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="b", is_new_key=True),
            ],
        )
        repo.save(keyset1, updated_by=str(uuid4()))

        # Validate progression 2 trying to use 'b', 'c' - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            repo.validate_key_progression_uniqueness(
                keyboard_id=keyboard_id,
                progression_order=2,
                keys=["b", "c"],
            )

        assert "b" in str(exc_info.value)

    def test_validate_key_progression_uniqueness_allows_new_keys(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test validation allows keys not in earlier progressions."""
        # Create progression 1 with 'a', 'b'
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Prog 1",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="b", is_new_key=True),
            ],
        )
        repo.save(keyset1, updated_by=str(uuid4()))

        # Validate progression 2 with 'c', 'd' - should NOT raise
        repo.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=2,
            keys=["c", "d"],
        )
        # If we get here, validation passed


class TestPostgresKeysetRepositoryAuditTrail:
    """Test audit trail (created_user_id, updated_user_id)."""

    def test_save_new_records_created_user(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test saving new keyset records created_user_id."""
        user_id = str(uuid4())
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Audit Test",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        repo.save(keyset, updated_by=user_id)

        # Query main record
        record = db_with_tables.fetchone(
            query="SELECT created_user_id FROM keyset WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )

        assert record["created_user_id"] == user_id

    def test_save_update_records_updated_user(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test updating keyset records updated_user_id."""
        user1 = str(uuid4())
        user2 = str(uuid4())

        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Update Audit",
            progression_order=1,
            keys=[KeysetKey(key_char="u", is_new_key=True)],
        )
        repo.save(keyset, updated_by=user1)

        # Update with different user
        keyset.keyset_name = "Updated by User 2"
        repo.save(keyset, updated_by=user2)

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT version_no, updated_user_id FROM keyset_history WHERE keyset_id = %s ORDER BY version_no",
            params=(str(keyset.keyset_id),),
        )

        assert history[0]["updated_user_id"] == user1
        assert history[1]["updated_user_id"] == user2
