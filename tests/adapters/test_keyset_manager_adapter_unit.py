"""Unit tests for KeysetManagerAdapter — verifies adapter delegates to KeysetCollection API.

Tests the Interface Adapters layer (Layer 3) — unit tests with InMemoryKeysetRepository.
No database, no Docker. Verifies the adapter uses the CURRENT KeysetCollection public API
(not removed/renamed methods), which prevents regression of the save defect where the
adapter silently failed because it called methods that no longer existed.

Tests follow TDD delivery standard, testing_and_trustability rules, and
keyword_arguments standard.
"""

import sys
import uuid
from unittest.mock import MagicMock

import pytest

from adapters.keyset_manager_adapter import KeysetManagerAdapter
from db.database_manager import DatabaseManager
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from helpers.debug_util import DebugUtil
from repositories.keyset_repository_memory import InMemoryKeysetRepository
from use_cases.keyset_collection import KeysetCollection

# ============================================================================
# CONSTANTS
# ============================================================================

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _id(ks: Keyset) -> str:
    """Extract keyset_id, asserting it is not None (test convenience)."""
    assert ks.keyset_id is not None
    return ks.keyset_id


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def keyboard_id() -> str:
    """Provide a test keyboard UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def repo() -> InMemoryKeysetRepository:
    """Provide a fresh in-memory repository."""
    return InMemoryKeysetRepository()


@pytest.fixture
def debug_util() -> DebugUtil:
    """Provide a DebugUtil instance."""
    return DebugUtil()


@pytest.fixture
def collection(repo: InMemoryKeysetRepository, keyboard_id: str) -> KeysetCollection:
    """Provide a KeysetCollection bound to a keyboard."""
    return KeysetCollection(repo, keyboard_id=keyboard_id)


@pytest.fixture
def adapter(
    repo: InMemoryKeysetRepository, debug_util: DebugUtil, keyboard_id: str
) -> KeysetManagerAdapter:
    """Provide a KeysetManagerAdapter wired to InMemoryKeysetRepository.

    Bypasses the normal PostgresKeysetRepository construction by injecting
    the in-memory repo and collection directly. The mock DB returns None for
    fetchone/fetchall so the "last resort" fallback in get_keyset_by_id exits
    cleanly without hitting a real database.
    """
    # Create adapter without real DB - use mock for DatabaseManager
    mock_db = MagicMock(spec=DatabaseManager)
    mock_db.fetchone.return_value = None
    mock_db.fetchall.return_value = []
    adapter = KeysetManagerAdapter(db=mock_db, debug_util=debug_util)

    # Replace the internal collection with one using in-memory repo
    adapter._collection = KeysetCollection(repo, keyboard_id=keyboard_id)
    adapter._keyboard_id = uuid.UUID(keyboard_id)

    return adapter


def _make_keyset(*, keyboard_id: str, name: str, order: int, keys: str = "") -> Keyset:
    """Build a Keyset entity with optional keys from a string of characters."""
    ks = Keyset(
        keyboard_id=keyboard_id,
        keyset_name=name,
        progression_order=order,
        keys=[KeysetKey(key_char=c, is_new_key=True) for c in keys],
    )
    return ks


# ============================================================================
# ADAPTER USES CURRENT KeysetCollection API
# ============================================================================


class TestAdapterUsesGetKeyset:
    """Verify adapter lookup uses get_keyset (not the removed get_by_id)."""

    def test_get_keyset_by_id_delegates_to_collection_get_keyset(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify get_keyset_by_id calls collection.get_keyset."""
        ks = _make_keyset(keyboard_id=keyboard_id, name="Alpha", order=1, keys="ab")
        adapter._collection._keysets[_id(ks)] = ks
        adapter._sync_cache()

        result = adapter.get_keyset_by_id(keyset_id=_id(ks))
        assert result is not None
        assert result.keyset_name == "Alpha"

    def test_get_keyset_alias_delegates(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify get_keyset alias returns same result as get_keyset_by_id."""
        ks = _make_keyset(keyboard_id=keyboard_id, name="Beta", order=1)
        adapter._collection._keysets[_id(ks)] = ks
        adapter._sync_cache()

        result = adapter.get_keyset(keyset_id=_id(ks))
        assert result is not None
        assert result.keyset_name == "Beta"

    def test_get_keyset_by_id_returns_none_for_missing(
        self, adapter: KeysetManagerAdapter
    ) -> None:
        """Test objective: Verify None returned for nonexistent keyset_id."""
        result = adapter.get_keyset_by_id(keyset_id=str(uuid.uuid4()))
        assert result is None


# ============================================================================
# SAVE KEYSET
# ============================================================================


class TestSaveKeyset:
    """Verify save_keyset stages and saves via current API."""

    def test_save_new_keyset_stages_into_collection(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify new keyset is staged and persisted through save_all."""
        ks = _make_keyset(keyboard_id=keyboard_id, name="New", order=1, keys="ab")

        saved = adapter.save_keyset(keyset=ks, updated_by=TEST_USER_ID)

        assert saved.keyset_name == "New"
        assert saved.in_db is True
        assert saved.is_dirty is False

    def test_save_existing_keyset_updates_in_place(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify existing keyset is updated in-place (no update_keyset call)."""
        ks = _make_keyset(keyboard_id=keyboard_id, name="Original", order=1, keys="a")
        adapter._stage_keyset_into_collection(ks)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        # Modify and re-save
        updated = _make_keyset(keyboard_id=keyboard_id, name="Renamed", order=1, keys="ab")
        updated.keyset_id = ks.keyset_id  # Same ID = existing

        saved = adapter.save_keyset(keyset=updated, updated_by=TEST_USER_ID)

        assert saved.keyset_name == "Renamed"
        assert len(saved.keys) == 2


# ============================================================================
# SAVE ALL KEYSETS
# ============================================================================


class TestSaveAllKeysets:
    """Verify save_all_keysets delegates correctly to current API."""

    def test_save_all_new_keysets_returns_true(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify save_all returns True when staging new keysets."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="First", order=1, keys="a")
        ks2 = _make_keyset(keyboard_id=keyboard_id, name="Second", order=2, keys="b")

        result = adapter.save_all_keysets(keysets=[ks1, ks2], updated_by=TEST_USER_ID)

        assert result is True
        cached = adapter.get_cached_keysets()
        assert len(cached) == 2

    def test_save_all_mixed_new_and_existing(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify save_all handles mix of new + existing keysets."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="Existing", order=1, keys="a")
        adapter._stage_keyset_into_collection(ks1)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        # Now save with ks1 updated + ks2 new
        ks1_updated = _make_keyset(keyboard_id=keyboard_id, name="Updated", order=1, keys="ab")
        ks1_updated.keyset_id = ks1.keyset_id
        ks2 = _make_keyset(keyboard_id=keyboard_id, name="Brand New", order=2, keys="c")

        result = adapter.save_all_keysets(
            keysets=[ks1_updated, ks2], updated_by=TEST_USER_ID
        )

        assert result is True
        cached = adapter.get_cached_keysets()
        assert len(cached) == 2
        names = {ks.keyset_name for ks in cached}
        assert "Updated" in names
        assert "Brand New" in names

    def test_save_all_logs_error_on_failure(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify save_all logs errors instead of silently swallowing."""
        # Force an exception by using invalid updated_by
        ks = _make_keyset(keyboard_id=keyboard_id, name="Test", order=1)

        # Save with empty updated_by to trigger a ValueError
        result = adapter.save_all_keysets(keysets=[ks], updated_by="")

        # Even on failure, should return False (not raise)
        assert result is False

    def test_save_all_empty_list_returns_true(
        self, adapter: KeysetManagerAdapter
    ) -> None:
        """Test objective: Verify save_all with empty list succeeds."""
        result = adapter.save_all_keysets(keysets=[], updated_by=TEST_USER_ID)
        assert result is True


# ============================================================================
# DELETE KEYSET
# ============================================================================


class TestDeleteKeyset:
    """Verify delete_keyset uses current API (no deleted_by forwarded to collection)."""

    def test_delete_existing_keyset_returns_true(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify deleting existing keyset succeeds."""
        ks = _make_keyset(keyboard_id=keyboard_id, name="ToDelete", order=1, keys="x")
        adapter._stage_keyset_into_collection(ks)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        result = adapter.delete_keyset(keyset_id=_id(ks), deleted_by=TEST_USER_ID)

        assert result is True
        assert adapter.get_keyset_by_id(keyset_id=_id(ks)) is None

    def test_delete_nonexistent_keyset_returns_false(
        self, adapter: KeysetManagerAdapter
    ) -> None:
        """Test objective: Verify deleting nonexistent keyset returns False."""
        result = adapter.delete_keyset(
            keyset_id=str(uuid.uuid4()), deleted_by=TEST_USER_ID
        )
        assert result is False


# ============================================================================
# PROMOTE / DEMOTE
# ============================================================================


class TestPromoteKeyset:
    """Verify promote_keyset uses current API (no keyboard_id/updated_by forwarded)."""

    def test_promote_second_keyset_returns_true(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify promoting second keyset swaps with first."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="First", order=1, keys="a")
        ks2 = _make_keyset(keyboard_id=keyboard_id, name="Second", order=2, keys="b")
        adapter._stage_keyset_into_collection(ks1)
        adapter._stage_keyset_into_collection(ks2)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        result = adapter.promote_keyset(
            keyboard_id=keyboard_id, keyset_id=_id(ks2), updated_by=TEST_USER_ID
        )

        assert result is True
        cached = adapter.get_cached_keysets()
        assert cached[0].keyset_name == "Second"
        assert cached[1].keyset_name == "First"

    def test_promote_first_keyset_returns_false(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify promoting first keyset is a no-op."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="Only", order=1, keys="a")
        adapter._stage_keyset_into_collection(ks1)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        result = adapter.promote_keyset(
            keyboard_id=keyboard_id, keyset_id=_id(ks1), updated_by=TEST_USER_ID
        )

        assert result is False


class TestDemoteKeyset:
    """Verify demote_keyset uses current API (no keyboard_id/updated_by forwarded)."""

    def test_demote_first_keyset_returns_true(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify demoting first keyset swaps with second."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="First", order=1, keys="a")
        ks2 = _make_keyset(keyboard_id=keyboard_id, name="Second", order=2, keys="b")
        adapter._stage_keyset_into_collection(ks1)
        adapter._stage_keyset_into_collection(ks2)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        result = adapter.demote_keyset(
            keyboard_id=keyboard_id, keyset_id=_id(ks1), updated_by=TEST_USER_ID
        )

        assert result is True
        cached = adapter.get_cached_keysets()
        assert cached[0].keyset_name == "Second"
        assert cached[1].keyset_name == "First"

    def test_demote_last_keyset_returns_false(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify demoting last keyset is a no-op."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="Only", order=1, keys="a")
        adapter._stage_keyset_into_collection(ks1)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        result = adapter.demote_keyset(
            keyboard_id=keyboard_id, keyset_id=_id(ks1), updated_by=TEST_USER_ID
        )

        assert result is False


# ============================================================================
# GET MASTERED AND CURRENT KEYS
# ============================================================================


class TestGetMasteredAndCurrentKeys:
    """Verify get_mastered_and_current_keys uses current API (no keyboard_id forwarded)."""

    def test_returns_mastered_and_current_keys(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify mastered keys from earlier and current keys returned."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="First", order=1, keys="ab")
        ks2 = _make_keyset(keyboard_id=keyboard_id, name="Second", order=2, keys="cd")
        adapter._stage_keyset_into_collection(ks1)
        adapter._stage_keyset_into_collection(ks2)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        mastered, current = adapter.get_mastered_and_current_keys(
            keyboard_id=keyboard_id, keyset_id=_id(ks2)
        )

        assert sorted(mastered) == ["a", "b"]
        assert sorted(current) == ["c", "d"]


# ============================================================================
# LIST AND CACHE
# ============================================================================


class TestListAndCache:
    """Verify list and cache operations work correctly."""

    def test_get_cached_keysets_sorted_by_progression(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify cached keysets returned in progression order."""
        ks1 = _make_keyset(keyboard_id=keyboard_id, name="First", order=1, keys="a")
        ks2 = _make_keyset(keyboard_id=keyboard_id, name="Second", order=2, keys="b")
        adapter._stage_keyset_into_collection(ks2)  # Insert out of order
        adapter._stage_keyset_into_collection(ks1)
        adapter._collection.save_all(updated_by=TEST_USER_ID)
        adapter._sync_cache()

        cached = adapter.get_cached_keysets()

        assert len(cached) == 2
        assert cached[0].progression_order <= cached[1].progression_order

    def test_get_keys_for_keyset_returns_tuples(
        self, adapter: KeysetManagerAdapter, keyboard_id: str
    ) -> None:
        """Test objective: Verify get_keys_for_keyset returns (char, is_new_key) tuples."""
        ks = _make_keyset(keyboard_id=keyboard_id, name="Keys", order=1, keys="ab")
        adapter._stage_keyset_into_collection(ks)
        adapter._sync_cache()

        result = adapter.get_keys_for_keyset(keyset_id=_id(ks))

        assert len(result) == 2
        chars = {t[0] for t in result}
        assert chars == {"a", "b"}
        assert all(isinstance(t[1], bool) for t in result)

    def test_get_keys_for_nonexistent_keyset_returns_empty(
        self, adapter: KeysetManagerAdapter
    ) -> None:
        """Test objective: Verify empty list for nonexistent keyset."""
        result = adapter.get_keys_for_keyset(keyset_id=str(uuid.uuid4()))
        assert result == []


# ============================================================================
# DEBUG MESSAGING
# ============================================================================


class TestDebugMessaging:
    """Verify adapter emits debug messages for observability."""

    def test_save_all_logs_on_success(
        self, repo: InMemoryKeysetRepository, keyboard_id: str
    ) -> None:
        """Test objective: Verify save_all emits debugMessage on success."""
        mock_debug = MagicMock(spec=DebugUtil)
        mock_db = MagicMock(spec=DatabaseManager)
        adapter = KeysetManagerAdapter(db=mock_db, debug_util=mock_debug)
        adapter._collection = KeysetCollection(repo, keyboard_id=keyboard_id)
        adapter._keyboard_id = uuid.UUID(keyboard_id)

        result = adapter.save_all_keysets(keysets=[], updated_by=TEST_USER_ID)

        assert result is True
        # Check that debugMessage was called at least once
        assert mock_debug.debugMessage.called

    def test_save_all_logs_on_failure(
        self, repo: InMemoryKeysetRepository, keyboard_id: str
    ) -> None:
        """Test objective: Verify save_all emits debugMessage with error details on failure."""
        mock_debug = MagicMock(spec=DebugUtil)
        mock_db = MagicMock(spec=DatabaseManager)
        adapter = KeysetManagerAdapter(db=mock_db, debug_util=mock_debug)
        adapter._collection = KeysetCollection(repo, keyboard_id=keyboard_id)
        adapter._keyboard_id = uuid.UUID(keyboard_id)

        ks = _make_keyset(keyboard_id=keyboard_id, name="Bad", order=1)
        # Force failure with empty updated_by
        result = adapter.save_all_keysets(keysets=[ks], updated_by="")

        assert result is False
        # Verify error was logged (find call containing "FAILED")
        calls = [str(c) for c in mock_debug.debugMessage.call_args_list]
        error_calls = [c for c in calls if "FAILED" in c]
        assert len(error_calls) > 0, "Expected at least one error log with 'FAILED'"

    def test_init_logs_initialization(
        self, repo: InMemoryKeysetRepository
    ) -> None:
        """Test objective: Verify adapter logs initialization message."""
        mock_debug = MagicMock(spec=DebugUtil)
        mock_db = MagicMock(spec=DatabaseManager)
        _ = KeysetManagerAdapter(db=mock_db, debug_util=mock_debug)

        calls = [str(c) for c in mock_debug.debugMessage.call_args_list]
        init_calls = [c for c in calls if "initialized" in c]
        assert len(init_calls) > 0


# ============================================================================
# API CONTRACT REGRESSION GUARDS
# ============================================================================


class TestCollectionApiContract:
    """Regression tests ensuring adapter calls only EXISTING KeysetCollection methods.

    These tests verify that the specific method names and parameter signatures
    used by the adapter match the current KeysetCollection public API.
    Prevents recurrence of the silent save failure caused by calling removed methods.
    """

    def test_collection_has_get_keyset_method(self) -> None:
        """Test objective: Verify KeysetCollection has get_keyset (not get_by_id)."""
        assert hasattr(KeysetCollection, "get_keyset")

    def test_collection_get_keyset_accepts_keyset_id_keyword(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify get_keyset accepts keyset_id as keyword arg."""
        result = collection.get_keyset(keyset_id=str(uuid.uuid4()))
        assert result is None  # No error, just not found

    def test_collection_has_no_get_by_id_method(self) -> None:
        """Test objective: Verify get_by_id was removed from KeysetCollection."""
        assert not hasattr(KeysetCollection, "get_by_id")

    def test_collection_has_no_update_keyset_method(self) -> None:
        """Test objective: Verify update_keyset was removed from KeysetCollection."""
        assert not hasattr(KeysetCollection, "update_keyset")

    def test_collection_delete_keyset_takes_only_keyset_id(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test objective: Verify delete_keyset signature has no deleted_by parameter."""
        import inspect

        sig = inspect.signature(collection.delete_keyset)
        params = list(sig.parameters.keys())
        assert "keyset_id" in params
        assert "deleted_by" not in params

    def test_collection_promote_keyset_takes_only_keyset_id(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify promote_keyset has no keyboard_id or updated_by params."""
        import inspect

        sig = inspect.signature(collection.promote_keyset)
        params = list(sig.parameters.keys())
        assert "keyset_id" in params
        assert "keyboard_id" not in params
        assert "updated_by" not in params

    def test_collection_demote_keyset_takes_only_keyset_id(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify demote_keyset has no keyboard_id or updated_by params."""
        import inspect

        sig = inspect.signature(collection.demote_keyset)
        params = list(sig.parameters.keys())
        assert "keyset_id" in params
        assert "keyboard_id" not in params
        assert "updated_by" not in params

    def test_collection_get_mastered_and_current_keys_takes_only_keyset_id(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify get_mastered_and_current_keys has no keyboard_id param."""
        import inspect

        sig = inspect.signature(collection.get_mastered_and_current_keys)
        params = list(sig.parameters.keys())
        assert "keyset_id" in params
        assert "keyboard_id" not in params

    def test_collection_add_keyset_takes_keyset_name_not_keyset_entity(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify add_keyset accepts keyset_name, not keyset entity."""
        import inspect

        sig = inspect.signature(collection.add_keyset)
        params = list(sig.parameters.keys())
        assert "keyset_name" in params
        assert "keyset" not in params


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
