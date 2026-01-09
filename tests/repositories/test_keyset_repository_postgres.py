"""Integration tests for PostgresKeysetRepository with real PostgreSQL database.

Tests SCD-2 history tracking, checksum no-op detection, audit trail, and business rules.
Uses DatabaseManager for connection to Docker PostgreSQL.
"""

from typing import Tuple
from uuid import uuid4

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_repository_postgres import PostgresKeysetRepository

# Well-known test user UUID (matches tests/conftest.py)
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def repo(db_with_tables: DatabaseManager) -> PostgresKeysetRepository:
    """Create PostgresKeysetRepository."""
    return PostgresKeysetRepository(db_with_tables)


@pytest.fixture
def keyboard_and_user(db_with_tables: DatabaseManager) -> Tuple[str, str]:
    """Create test keyboard ID with database record and return (keyboard_id, user_id)."""
    kbd_id = str(uuid4())
    user_id = TEST_USER_ID

    # Insert test user first (ON CONFLICT for idempotency)
    db_with_tables.execute(
        query="""
            INSERT INTO users (user_id, first_name, surname, email_address)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
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

    return (kbd_id, user_id)


@pytest.fixture
def keyboard_id(keyboard_and_user: Tuple[str, str]) -> str:
    """Return only the keyboard_id for backward compatibility."""
    return keyboard_and_user[0]


@pytest.fixture
def test_user(keyboard_and_user: Tuple[str, str]) -> str:
    """Return the test user_id for audit trail testing."""
    return keyboard_and_user[1]


@pytest.fixture
def clean_tables(db_with_tables: DatabaseManager) -> None:
    """Clean keyset tables before each test."""
    db_with_tables.execute(query="DELETE FROM keyset_keys_history", params=())
    db_with_tables.execute(query="DELETE FROM keyset_history", params=())
    db_with_tables.execute(query="DELETE FROM keyset_keys", params=())
    db_with_tables.execute(query="DELETE FROM keyset", params=())


@pytest.fixture(autouse=True)
def verify_docker_db(db_with_tables: DatabaseManager) -> None:
    """Test objective: Ensure keyset repository tests run against Docker PostgreSQL."""

    assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER


class TestPostgresKeysetRepositoryBasicCRUD:
    """Test basic CRUD operations."""

    def test_save_new_keyset_inserts_record(
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
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

        repo.save(keyset, updated_by=test_user)

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
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
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

        repo.save(keyset1, updated_by=test_user)
        repo.save(keyset2, updated_by=test_user)

        result = repo.list_for_keyboard(keyboard_id)

        assert len(result) == 2
        assert result[0].keyset_name == "First"
        assert result[0].progression_order == 1
        assert result[1].keyset_name == "Second"
        assert result[1].progression_order == 2

    def test_delete_removes_keyset(
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
    ) -> None:
        """Test delete removes keyset from main table."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete",
            progression_order=1,
            keys=[KeysetKey(key_char="x", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        success = repo.delete(str(keyset.keyset_id), deleted_by=test_user)

        assert success is True
        assert repo.get_by_id(str(keyset.keyset_id)) is None

    def test_delete_returns_false_for_nonexistent(
        self, repo: PostgresKeysetRepository, test_user: str, clean_tables: None
    ) -> None:
        """Test delete returns False for non-existent keyset."""
        result = repo.delete(str(uuid4()), deleted_by=test_user)
        assert result is False

    def test_list_for_keyboard_sets_in_db_true(
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
    ) -> None:
        """Test that keysets loaded via list_for_keyboard have in_db=True.

        This is critical for update operations to work correctly.
        """
        # Create and save a keyset
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="In DB Test",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        # Load via list_for_keyboard
        loaded = repo.list_for_keyboard(keyboard_id)

        assert len(loaded) == 1
        assert loaded[0].in_db is True, "Loaded keyset must have in_db=True"

    def test_get_by_id_sets_in_db_true(
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
    ) -> None:
        """Test that keyset loaded via get_by_id has in_db=True.

        This is critical for update operations to work correctly.
        """
        # Create and save a keyset
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="In DB Test",
            progression_order=1,
            keys=[],
        )
        repo.save(keyset, updated_by=test_user)

        # Load via get_by_id
        loaded = repo.get_by_id(str(keyset.keyset_id))

        assert loaded is not None
        assert loaded.in_db is True, "Loaded keyset must have in_db=True"


class TestPostgresKeysetRepositorySCD2History:
    """Test SCD-2 history tracking."""

    def test_save_new_creates_history_with_version_1(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
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

        repo.save(keyset, updated_by=test_user)

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
        test_user: str,
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
        repo.save(keyset, updated_by=test_user)

        # Update
        keyset.keyset_name = "Updated"
        repo.save(keyset, updated_by=test_user)

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
        test_user: str,
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
        repo.save(keyset, updated_by=test_user)

        # Update
        keyset.keyset_name = "Time Updated"
        repo.save(keyset, updated_by=test_user)

        # Query old history
        old_history = db_with_tables.fetchone(
            query="SELECT valid_to_dt FROM keyset_history WHERE keyset_id = %s AND version_no = 1",
            params=(str(keyset.keyset_id),),
        )

        assert old_history is not None
        assert old_history["valid_to_dt"] != "9999-12-31 23:59:59"

    def test_delete_creates_delete_history_record(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
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
        repo.save(keyset, updated_by=test_user)

        repo.delete(str(keyset.keyset_id), deleted_by=test_user)

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT version_no, action FROM keyset_history WHERE keyset_id = %s ORDER BY version_no",
            params=(str(keyset.keyset_id),),
        )

        assert len(history) == 2
        assert history[0]["action"] == "INSERT"
        assert history[1]["action"] == "DELETE"

    def test_key_history_closes_prior_versions_on_update(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test objective: Updating keys closes previous key history and adds new version."""

        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Key History",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        key_id = str(keyset.keys[0].key_id)
        keyset.keys = [
            KeysetKey(key_id=key_id, key_char="a", is_new_key=False),
            KeysetKey(key_char="b", is_new_key=True),
        ]
        repo.save(keyset, updated_by=test_user)

        history = db_with_tables.fetchall(
            query="""
                SELECT action, is_current, version_no, valid_to_dt
                FROM keyset_keys_history
                WHERE key_id = %s
                ORDER BY version_no
            """,
            params=(key_id,),
        )

        actions = [row["action"] for row in history]
        assert actions == ["INSERT", "UPDATE"]
        assert history[0]["is_current"] == 0
        assert str(history[0]["valid_to_dt"]) != "9999-12-31 23:59:59"
        assert history[1]["is_current"] == 1

    def test_key_history_records_delete_on_keyset_delete(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test objective: Deleting a keyset records DELETE action for each key with closed prior version."""

        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Delete Keys",
            progression_order=1,
            keys=[KeysetKey(key_char="z", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        key_id = str(keyset.keys[0].key_id)
        repo.delete(str(keyset.keyset_id), deleted_by=test_user)

        history = db_with_tables.fetchall(
            query="""
                SELECT action, is_current, version_no
                FROM keyset_keys_history
                WHERE key_id = %s
                ORDER BY version_no
            """,
            params=(key_id,),
        )

        assert [row["action"] for row in history] == ["INSERT", "DELETE"]
        assert history[0]["is_current"] == 0
        assert history[1]["is_current"] == 1


class TestPostgresKeysetRepositoryChecksumNoOp:
    """Test checksum no-op detection."""

    def test_save_with_no_changes_is_no_op(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
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
        repo.save(keyset, updated_by=test_user)

        # Save again without changes
        repo.save(keyset, updated_by=test_user)

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
        test_user: str,
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
        repo.save(keyset, updated_by=test_user)

        # Add key
        keyset.keys.append(KeysetKey(key_char="l", is_new_key=True))
        repo.save(keyset, updated_by=test_user)

        # Query history
        history = db_with_tables.fetchall(
            query="SELECT COUNT(*) as cnt FROM keyset_history WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )

        assert history[0]["cnt"] == 2  # INSERT + UPDATE


class TestPostgresKeysetRepositoryBusinessRules:
    """Test business rule validation."""

    def test_validate_key_progression_uniqueness_finds_violations(
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
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
        repo.save(keyset1, updated_by=test_user)

        # Validate progression 2 trying to use 'b', 'c' - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            repo.validate_key_progression_uniqueness(
                keyboard_id=keyboard_id,
                progression_order=2,
                keys=["b", "c"],
            )

        assert "b" in str(exc_info.value)

    def test_validate_key_progression_uniqueness_allows_new_keys(
        self, repo: PostgresKeysetRepository, keyboard_id: str, test_user: str, clean_tables: None
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
        repo.save(keyset1, updated_by=test_user)

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
        test_user: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test saving new keyset records created_user_id."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Audit Test",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        repo.save(keyset, updated_by=test_user)

        # Query main record
        record = db_with_tables.fetchone(
            query="SELECT created_user_id FROM keyset WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )

        assert record is not None
        assert str(record["created_user_id"]) == test_user

    def test_save_update_records_updated_user(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
        db_with_tables: DatabaseManager,
    ) -> None:
        """Test updating keyset records updated_user_id in history.

        Note: With FK constraints, we use the same test_user for both operations
        since creating multiple test users would require additional fixtures.
        """
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Update Audit",
            progression_order=1,
            keys=[KeysetKey(key_char="u", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        # Update with same user (verifying history is recorded)
        keyset.keyset_name = "Updated by Same User"
        repo.save(keyset, updated_by=test_user)

        # Query history - verify both versions have valid user_id
        history = db_with_tables.fetchall(
            query="SELECT version_no, updated_user_id FROM keyset_history WHERE keyset_id = %s ORDER BY version_no",
            params=(str(keyset.keyset_id),),
        )

        assert len(history) == 2
        assert str(history[0]["updated_user_id"]) == test_user
        assert str(history[1]["updated_user_id"]) == test_user


class TestPostgresKeysetRepositoryDestructiveValidation:
    """Destructive tests for bad data validation on keyset operations.

    These tests verify that the repository properly rejects invalid input
    and that FK constraints enforce referential integrity.
    """

    def test_save_fails_with_empty_updated_by(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test save raises ValueError when updated_by is empty string."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        with pytest.raises(ValueError, match="updated_by user ID is required"):
            repo.save(keyset, updated_by="")

    def test_save_fails_with_invalid_uuid_updated_by(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test save raises ValueError when updated_by is not a valid UUID."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        with pytest.raises(ValueError, match="updated_by must be a valid UUID"):
            repo.save(keyset, updated_by="not-a-uuid")

    def test_save_fails_with_system_string_updated_by(
        self, repo: PostgresKeysetRepository, keyboard_id: str, clean_tables: None
    ) -> None:
        """Test save raises ValueError when updated_by is 'system' (the old fallback)."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        with pytest.raises(ValueError, match="updated_by must be a valid UUID"):
            repo.save(keyset, updated_by="system")

    def test_delete_fails_with_empty_deleted_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test delete raises ValueError when deleted_by is empty string."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete",
            progression_order=1,
            keys=[KeysetKey(key_char="x", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        with pytest.raises(ValueError, match="deleted_by user ID is required"):
            repo.delete(str(keyset.keyset_id), deleted_by="")

    def test_delete_fails_with_invalid_uuid_deleted_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test delete raises ValueError when deleted_by is not a valid UUID."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete",
            progression_order=1,
            keys=[KeysetKey(key_char="x", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        with pytest.raises(ValueError, match="deleted_by must be a valid UUID"):
            repo.delete(str(keyset.keyset_id), deleted_by="invalid-uuid")

    def test_swap_progression_fails_with_empty_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test swap_progression_order raises ValueError when updated_by is empty."""
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        keyset2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],
        )
        repo.save(keyset1, updated_by=test_user)
        repo.save(keyset2, updated_by=test_user)

        # Swap progression orders
        keyset1.progression_order, keyset2.progression_order = 2, 1

        with pytest.raises(ValueError, match="updated_by user ID is required"):
            repo.swap_progression_order(keyset1, keyset2, updated_by="")

    def test_swap_progression_fails_with_invalid_uuid_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test swap_progression_order raises ValueError when updated_by is invalid UUID."""
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        keyset2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],
        )
        repo.save(keyset1, updated_by=test_user)
        repo.save(keyset2, updated_by=test_user)

        # Swap progression orders
        keyset1.progression_order, keyset2.progression_order = 2, 1

        with pytest.raises(ValueError, match="updated_by must be a valid UUID"):
            repo.swap_progression_order(keyset1, keyset2, updated_by="bad-uuid")

    def test_save_fails_with_nonexistent_user_fk_violation(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
    ) -> None:
        """Test save fails with FK violation when user_id doesn't exist in users table."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="FK Test",
            progression_order=1,
            keys=[KeysetKey(key_char="f", is_new_key=True)],
        )

        # Use a valid UUID that doesn't exist in the users table
        nonexistent_user = str(uuid4())

        # FK constraint should reject save with non-existent user
        from db.exceptions import ForeignKeyError

        with pytest.raises(ForeignKeyError):
            repo.save(keyset, updated_by=nonexistent_user)

    def test_save_fails_with_empty_keyset_name(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when keyset_name is empty."""
        with pytest.raises(ValueError):
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="",  # Empty name should fail validation
                progression_order=1,
                keys=[KeysetKey(key_char="a", is_new_key=True)],
            )

    def test_save_fails_with_zero_progression_order(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when progression_order is zero."""
        with pytest.raises(ValueError):
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="Zero Order",
                progression_order=0,  # Must be >= 1
                keys=[KeysetKey(key_char="a", is_new_key=True)],
            )

    def test_save_fails_with_negative_progression_order(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when progression_order is negative."""
        with pytest.raises(ValueError):
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="Negative Order",
                progression_order=-1,  # Must be >= 1
                keys=[KeysetKey(key_char="a", is_new_key=True)],
            )

    def test_save_fails_with_duplicate_keys_in_keyset(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test that duplicate keys within a keyset are handled.

        Note: Duplicate key validation may happen at entity level or DB level.
        This test verifies the behavior exists somewhere in the stack.
        """
        # If Keyset allows duplicates at construction, DB unique constraint will catch it
        try:
            keyset = Keyset(
                keyboard_id=keyboard_id,
                keyset_name="Duplicate Keys",
                progression_order=1,
                keys=[
                    KeysetKey(key_char="a", is_new_key=True),
                    KeysetKey(key_char="a", is_new_key=False),  # Duplicate key_char
                ],
            )
            # If construction succeeds, try saving - DB constraint should catch it
            from db.exceptions import ConstraintError

            with pytest.raises((ValueError, ConstraintError, Exception)):
                repo.save(keyset, updated_by=test_user)
        except ValueError:
            # Entity validation caught it - test passes
            pass

    def test_save_fails_with_empty_keyboard_id(
        self,
        repo: PostgresKeysetRepository,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when keyboard_id is empty."""
        with pytest.raises(ValueError):
            Keyset(
                keyboard_id="",  # Empty keyboard_id
                keyset_name="No Keyboard",
                progression_order=1,
                keys=[KeysetKey(key_char="a", is_new_key=True)],
            )

    def test_save_fails_with_invalid_keyboard_id_fk_violation(
        self,
        repo: PostgresKeysetRepository,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test save fails with FK violation when keyboard_id doesn't exist."""
        keyset = Keyset(
            keyboard_id=str(uuid4()),  # Non-existent keyboard
            keyset_name="FK Test",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        # FK constraint should reject save with non-existent keyboard
        from db.exceptions import ForeignKeyError

        with pytest.raises(ForeignKeyError):
            repo.save(keyset, updated_by=test_user)


class TestDestructiveUserIdValidation:
    """Destructive tests for required updated_by/deleted_by user ID validation.

    These tests verify that the repository properly rejects:
    - Missing user IDs
    - Empty user IDs
    - Invalid UUID format user IDs
    - Non-existent user IDs (FK constraint)
    """

    def test_save_fails_with_missing_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when updated_by is not provided."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="No User",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        # TypeError because updated_by is required positional argument
        with pytest.raises(TypeError):
            repo.save(keyset)  # type: ignore[call-arg]

    def test_save_fails_with_empty_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when updated_by is empty string."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Empty User",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        with pytest.raises(ValueError, match="updated_by user ID is required"):
            repo.save(keyset, updated_by="")

    def test_save_fails_with_invalid_uuid_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when updated_by is not a valid UUID."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Invalid UUID User",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        with pytest.raises(ValueError, match="updated_by must be a valid UUID"):
            repo.save(keyset, updated_by="not-a-uuid")

    def test_save_fails_with_system_string_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
    ) -> None:
        """Test save fails when updated_by is the old 'system' fallback value."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="System User",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        with pytest.raises(ValueError, match="updated_by must be a valid UUID"):
            repo.save(keyset, updated_by="system")

    def test_delete_fails_with_missing_deleted_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test delete fails when deleted_by is not provided."""
        # First create a keyset
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        # TypeError because deleted_by is required positional argument
        with pytest.raises(TypeError):
            repo.delete(str(keyset.keyset_id))  # type: ignore[call-arg]

    def test_delete_fails_with_empty_deleted_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test delete fails when deleted_by is empty string."""
        # First create a keyset
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete Empty",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        with pytest.raises(ValueError, match="deleted_by user ID is required"):
            repo.delete(str(keyset.keyset_id), deleted_by="")

    def test_delete_fails_with_invalid_uuid_deleted_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test delete fails when deleted_by is not a valid UUID."""
        # First create a keyset
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="To Delete Invalid",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(keyset, updated_by=test_user)

        with pytest.raises(ValueError, match="deleted_by must be a valid UUID"):
            repo.delete(str(keyset.keyset_id), deleted_by="invalid-uuid")

    def test_swap_progression_fails_with_empty_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test swap_progression_order fails when updated_by is empty."""
        # Create two keysets
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        keyset2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],
        )
        repo.save(keyset1, updated_by=test_user)
        repo.save(keyset2, updated_by=test_user)

        # Swap progression orders
        keyset1.progression_order, keyset2.progression_order = 2, 1

        with pytest.raises(ValueError, match="updated_by user ID is required"):
            repo.swap_progression_order(keyset1, keyset2, updated_by="")

    def test_swap_progression_fails_with_invalid_uuid_updated_by(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        test_user: str,
        clean_tables: None,
    ) -> None:
        """Test swap_progression_order fails when updated_by is not a valid UUID."""
        # Create two keysets
        keyset1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First Swap",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        keyset2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second Swap",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],
        )
        repo.save(keyset1, updated_by=test_user)
        repo.save(keyset2, updated_by=test_user)

        # Swap progression orders
        keyset1.progression_order, keyset2.progression_order = 2, 1

        with pytest.raises(ValueError, match="updated_by must be a valid UUID"):
            repo.swap_progression_order(keyset1, keyset2, updated_by="not-valid")

    def test_save_with_nonexistent_user_fk_violation(
        self,
        repo: PostgresKeysetRepository,
        keyboard_id: str,
        clean_tables: None,
    ) -> None:
        """Test save fails with FK violation when user_id doesn't exist in users table.

        Note: This test will only fail if FK constraints are enforced on user ID columns.
        The FK constraints were added to ensure data integrity.
        """
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Orphan User",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        # Use a valid UUID format but non-existent user
        non_existent_user = str(uuid4())

        # FK constraint should reject save with non-existent user
        from db.exceptions import ForeignKeyError

        with pytest.raises(ForeignKeyError):
            repo.save(keyset, updated_by=non_existent_user)
