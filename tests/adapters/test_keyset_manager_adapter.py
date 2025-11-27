"""Integration tests for KeysetManagerAdapter with PostgreSQL.

Tests that the adapter properly handles UUID objects end-to-end with PostgreSQL,
verifying that psycopg2 UUID adapter registration works correctly.
"""

import uuid

import pytest

from adapters.keyset_manager_adapter import KeysetManagerAdapter
from db.database_manager import DatabaseManager
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from helpers.debug_util import DebugUtil


@pytest.fixture
def keyboard_id(db_with_tables: DatabaseManager) -> str:
    """Fixture providing test keyboard UUID with keyboard record in database."""
    kbd_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Insert test user first (keyboards has FK to users)
    db_with_tables.execute(
        query="""
            INSERT INTO users (user_id, first_name, surname, email_address)
            VALUES (%s, %s, %s, %s)
        """,
        params=(user_id, "Test", "User", "test@example.com"),
    )

    # Insert test keyboard record to satisfy foreign key constraint
    db_with_tables.execute(
        query="""
            INSERT INTO keyboards (keyboard_id, user_id, keyboard_name, target_ms_per_keystroke)
            VALUES (%s, %s, %s, %s)
        """,
        params=(kbd_id, user_id, "Test Keyboard", 600),
    )

    return kbd_id


@pytest.fixture
def adapter(db_with_tables: DatabaseManager, debug_util: DebugUtil) -> KeysetManagerAdapter:
    """Fixture providing KeysetManagerAdapter instance."""
    return KeysetManagerAdapter(db=db_with_tables, debug_util=debug_util)


@pytest.fixture
def debug_util() -> DebugUtil:
    """Fixture providing DebugUtil instance."""
    return DebugUtil()


@pytest.fixture
def test_keyset(keyboard_id: str) -> Keyset:
    """Fixture providing a test keyset with UUID strings."""
    return Keyset(
        keyboard_id=keyboard_id,
        keyset_name="Home Row",
        progression_order=1,
        keys=[
            KeysetKey(key_char="a", is_new_key=True),
            KeysetKey(key_char="s", is_new_key=True),
            KeysetKey(key_char="d", is_new_key=True),
        ],
    )


# ============================================================================
# UUID ADAPTER INTEGRATION TESTS
# ============================================================================


class TestUUIDAdapterIntegration:
    """Test that UUID objects work correctly with PostgreSQL adapter registration."""

    def test_uuid_objects_work_with_postgres_adapter(
        self,
        adapter: KeysetManagerAdapter,
        keyboard_id: str,
        test_keyset: Keyset,
    ) -> None:
        """Test that UUID objects can be used throughout the stack without conversion.

        This test verifies that:
        1. psycopg2.extras.register_uuid() was called in DatabaseManager
        2. UUID objects can be passed to repository methods (adapter converts strings to UUIDs)
        3. UUID objects are properly adapted to PostgreSQL UUID type
        4. Round-trip save/load works with UUID strings in entities

        This is a regression test for the "can't adapt type 'UUID'" error.
        """
        # Save keyset using keyword args
        saved = adapter.save_keyset(keyset=test_keyset, updated_by=str(uuid.uuid4()))

        # Verify save succeeded and returned string UUIDs (entities use strings)
        assert isinstance(saved.keyset_id, str)
        assert isinstance(saved.keyboard_id, str)
        assert saved.keyset_name == "Home Row"

        # Preload using keyword arg
        adapter.preload_keysets_for_keyboard(keyboard_id=keyboard_id)

        # Verify cached keysets use string UUIDs
        cached = adapter.get_cached_keysets()
        assert len(cached) == 1
        assert isinstance(cached[0].keyset_id, str)
        assert isinstance(cached[0].keyboard_id, str)

        # Verify get_by_id works with keyword arg
        retrieved = adapter.get_keyset_by_id(keyset_id=str(saved.keyset_id))
        assert retrieved is not None
        assert isinstance(retrieved.keyset_id, str)
        assert retrieved.keyset_name == "Home Row"

    def test_list_keysets_for_keyboard_with_uuid_objects(
        self,
        adapter: KeysetManagerAdapter,
        keyboard_id: str,
        test_keyset: Keyset,
    ) -> None:
        """Test that list_keysets_for_keyboard handles UUID objects correctly.

        Verifies the adapter method that keysets_dialog.py calls.
        """
        # Save test keyset
        adapter.save_keyset(keyset=test_keyset, updated_by=str(uuid.uuid4()))

        # List keysets using keyword arg
        keysets = adapter.list_keysets_for_keyboard(keyboard_id=keyboard_id)

        # Verify result (entities use string UUIDs)
        assert len(keysets) == 1
        assert isinstance(keysets[0].keyset_id, str)
        assert isinstance(keysets[0].keyboard_id, str)
        assert keysets[0].keyset_name == "Home Row"

    def test_promote_keyset_with_uuid_objects(
        self,
        adapter: KeysetManagerAdapter,
        keyboard_id: str,
    ) -> None:
        """Test that promote_keyset works with UUID objects in progression order swaps."""
        # Create two keysets
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],
        )

        user_id = str(uuid.uuid4())
        saved1 = adapter.save_keyset(keyset=ks1, updated_by=user_id)
        saved2 = adapter.save_keyset(keyset=ks2, updated_by=user_id)

        # Promote second keyset (should swap with first) - returns bool now
        success = adapter.promote_keyset(keyset_id=str(saved2.keyset_id), updated_by=user_id)

        # Verify promotion worked
        assert success is True

        # Verify the keysets swapped by checking cache
        keysets = adapter.list_keysets_for_keyboard(keyboard_id=keyboard_id)
        keyset_by_name = {ks.keyset_name: ks for ks in keysets}

        assert keyset_by_name["Second"].progression_order == 1
        assert keyset_by_name["First"].progression_order == 2

    def test_get_mastered_and_current_keys_with_uuid_keyboard(
        self,
        adapter: KeysetManagerAdapter,
        keyboard_id: str,
    ) -> None:
        """Test that get_mastered_and_current_keys handles UUID keyboard_id."""
        # Create two keysets
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],
        )

        user_id = str(uuid.uuid4())
        adapter.save_keyset(keyset=ks1, updated_by=user_id)
        saved2 = adapter.save_keyset(keyset=ks2, updated_by=user_id)

        # Get mastered and current keys using keyset_id (not progression_order)
        mastered, current = adapter.get_mastered_and_current_keys(
            keyboard_id=keyboard_id, keyset_id=str(saved2.keyset_id)
        )

        # Verify results - returns sorted lists, not sets
        assert mastered == ["a"]  # From first keyset
        assert current == ["b"]  # From second keyset

    def test_validate_key_progression_uniqueness_with_uuid_keyboard(
        self,
        adapter: KeysetManagerAdapter,
        keyboard_id: str,
    ) -> None:
        """Test that validate_key_progression_uniqueness handles UUID keyboard_id."""
        # Create keyset with key 'a'
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )

        user_id = str(uuid.uuid4())
        adapter.save_keyset(keyset=ks1, updated_by=user_id)

        # Try to add 'a' to later progression (should raise ValueError)
        with pytest.raises(ValueError) as exc_info:
            adapter.validate_key_progression_uniqueness(
                keyboard_id=keyboard_id, progression_order=2, new_keys=["a", "b"]
            )

        # Verify violation detected
        assert "a" in str(exc_info.value)
