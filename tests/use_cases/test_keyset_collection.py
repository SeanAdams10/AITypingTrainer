"""Tests for KeysetCollection use case.

Tests the Use Cases layer (Layer 2) — unit tests with InMemoryKeysetRepository.
No database, no mocks. All business rules from Requirements/Keyset_req.md Section 3.2.

Tests follow TDD delivery standard, testing_and_trustability rules, and
keyword_arguments standard.
"""

import sys
import uuid

import pytest

from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_repository_memory import InMemoryKeysetRepository
from use_cases.keyset_collection import KeysetCollection, KeysetValidationError

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
def collection(repo: InMemoryKeysetRepository, keyboard_id: str) -> KeysetCollection:
    """Provide a KeysetCollection bound to a keyboard."""
    return KeysetCollection(repo, keyboard_id=keyboard_id)


# ============================================================================
# CONSTRUCTOR
# ============================================================================


class TestKeysetCollectionConstruction:
    """Test KeysetCollection construction."""

    def test_constructor_sets_keyboard_id(
        self, repo: InMemoryKeysetRepository, keyboard_id: str
    ) -> None:
        """Test objective: Verify constructor stores keyboard_id."""
        col = KeysetCollection(repo, keyboard_id=keyboard_id)
        assert col._keyboard_id == keyboard_id

    def test_constructor_initialises_empty(
        self, repo: InMemoryKeysetRepository, keyboard_id: str
    ) -> None:
        """Test objective: Verify new collection has no keysets and is not dirty."""
        col = KeysetCollection(repo, keyboard_id=keyboard_id)
        assert col.get_keysets_ordered() == []
        assert col.is_dirty is False


# ============================================================================
# add_keyset
# ============================================================================


class TestAddKeyset:
    """Test add_keyset(*, keyset_name, keys)."""

    def test_assigns_progression_order_1_for_first(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify first keyset gets progression_order=1."""
        ks = collection.add_keyset(keyset_name="First")
        assert ks.progression_order == 1

    def test_assigns_next_progression_order(self, collection: KeysetCollection) -> None:
        """Test objective: Verify second keyset gets progression_order=2."""
        collection.add_keyset(keyset_name="First")
        ks2 = collection.add_keyset(keyset_name="Second")
        assert ks2.progression_order == 2

    def test_marks_collection_dirty(self, collection: KeysetCollection) -> None:
        """Test objective: Verify add_keyset marks collection as dirty."""
        collection.add_keyset(keyset_name="Test")
        assert collection.is_dirty is True

    def test_creates_keys_from_string_list(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify keys are created from provided char list."""
        ks = collection.add_keyset(keyset_name="HomeRow", keys=["a", "s", "d"])
        assert len(ks.keys) == 3
        chars = {k.key_char for k in ks.keys}
        assert chars == {"a", "s", "d"}

    def test_creates_keyset_with_no_keys_by_default(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify keyset created with empty keys when none given."""
        ks = collection.add_keyset(keyset_name="Empty")
        assert ks.keys == []

    def test_auto_generates_keyset_id(self, collection: KeysetCollection) -> None:
        """Test objective: Verify add_keyset auto-generates UUID keyset_id."""
        ks = collection.add_keyset(keyset_name="Test")
        assert ks.keyset_id is not None
        uuid.UUID(_id(ks))

    def test_sets_keyboard_id_on_keyset(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test objective: Verify keyset inherits collection's keyboard_id."""
        ks = collection.add_keyset(keyset_name="Test")
        assert ks.keyboard_id == keyboard_id

    def test_keyset_starts_not_in_db(self, collection: KeysetCollection) -> None:
        """Test objective: Verify newly added keyset has in_db=False."""
        ks = collection.add_keyset(keyset_name="Test")
        assert ks.in_db is False

    def test_requires_keyset_name(self, collection: KeysetCollection) -> None:
        """Test objective: Verify add_keyset raises when keyset_name is None."""
        with pytest.raises(ValueError, match="keyset_name"):
            collection.add_keyset(keyset_name=None)


# ============================================================================
# insert_keyset_before
# ============================================================================


class TestInsertKeysetBefore:
    """Test insert_keyset_before(*, keyset_name, before_keyset_id, keys)."""

    def test_inserts_before_first(self, collection: KeysetCollection) -> None:
        """Test objective: Verify inserting before first keyset puts new one at order 1."""
        ks1 = collection.add_keyset(keyset_name="First")
        collection.insert_keyset_before(
            keyset_name="Before First",
            before_keyset_id=_id(ks1),
        )
        ordered = collection.get_keysets_ordered()
        assert ordered[0].keyset_name == "Before First"
        assert ordered[1].keyset_name == "First"

    def test_inserts_before_middle(self, collection: KeysetCollection) -> None:
        """Test objective: Verify inserting before middle keyset renumbers to 1..N."""
        collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        collection.add_keyset(keyset_name="Three")
        collection.insert_keyset_before(
            keyset_name="New",
            before_keyset_id=_id(ks2),
        )
        ordered = collection.get_keysets_ordered()
        names = [ks.keyset_name for ks in ordered]
        assert names == ["One", "New", "Two", "Three"]
        orders = [ks.progression_order for ks in ordered]
        assert orders == [1, 2, 3, 4]

    def test_appends_when_before_keyset_id_is_none(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify None before_keyset_id appends at end."""
        collection.add_keyset(keyset_name="First")
        collection.insert_keyset_before(
            keyset_name="Last",
            before_keyset_id=None,
        )
        ordered = collection.get_keysets_ordered()
        assert ordered[-1].keyset_name == "Last"

    def test_rejects_invalid_before_keyset_id(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify invalid before_keyset_id raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            collection.insert_keyset_before(
                keyset_name="X",
                before_keyset_id="nonexistent",
            )

    def test_insert_with_keys(self, collection: KeysetCollection) -> None:
        """Test objective: Verify insert_keyset_before accepts keys parameter."""
        ks1 = collection.add_keyset(keyset_name="First")
        ks_new = collection.insert_keyset_before(
            keyset_name="WithKeys",
            before_keyset_id=_id(ks1),
            keys=["x", "y"],
        )
        assert len(ks_new.keys) == 2

    def test_contiguous_orders_after_insert(self, collection: KeysetCollection) -> None:
        """Test objective: Verify orders are contiguous 1..N after insert (AC-10)."""
        for name in ["A", "B", "C"]:
            collection.add_keyset(keyset_name=name)
        ordered = collection.get_keysets_ordered()
        collection.insert_keyset_before(
            keyset_name="NEW",
            before_keyset_id=_id(ordered[1]),
        )
        orders = [ks.progression_order for ks in collection.get_keysets_ordered()]
        assert orders == [1, 2, 3, 4]


# ============================================================================
# delete_keyset
# ============================================================================


class TestDeleteKeyset:
    """Test delete_keyset(*, keyset_id)."""

    def test_delete_existing_returns_true(self, collection: KeysetCollection) -> None:
        """Test objective: Verify deleting an existing keyset returns True."""
        ks = collection.add_keyset(keyset_name="ToDelete")
        assert collection.delete_keyset(keyset_id=_id(ks)) is True

    def test_delete_nonexistent_returns_false(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify deleting a non-existent keyset returns False."""
        assert collection.delete_keyset(keyset_id="nonexistent") is False

    def test_delete_renumbers_contiguously(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify remaining orders are contiguous 1..N after delete (AC-10)."""
        collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        collection.add_keyset(keyset_name="Three")
        collection.delete_keyset(keyset_id=_id(ks2))
        orders = [ks.progression_order for ks in collection.get_keysets_ordered()]
        assert orders == [1, 2]
        names = [ks.keyset_name for ks in collection.get_keysets_ordered()]
        assert names == ["One", "Three"]

    def test_delete_marks_dirty(self, collection: KeysetCollection) -> None:
        """Test objective: Verify delete_keyset marks collection dirty."""
        ks = collection.add_keyset(keyset_name="Test")
        collection.is_dirty = False
        collection.delete_keyset(keyset_id=_id(ks))
        assert collection.is_dirty is True


# ============================================================================
# rename_keyset
# ============================================================================


class TestRenameKeyset:
    """Test rename_keyset(*, keyset_id, new_name)."""

    def test_rename_existing_returns_true(self, collection: KeysetCollection) -> None:
        """Test objective: Verify renaming an existing keyset returns True."""
        ks = collection.add_keyset(keyset_name="Old")
        assert collection.rename_keyset(keyset_id=_id(ks), new_name="New") is True

    def test_rename_updates_name(self, collection: KeysetCollection) -> None:
        """Test objective: Verify the keyset name is actually changed."""
        ks = collection.add_keyset(keyset_name="Old")
        collection.rename_keyset(keyset_id=_id(ks), new_name="New")
        assert ks.keyset_name == "New"

    def test_rename_nonexistent_returns_false(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify renaming non-existent keyset returns False."""
        assert collection.rename_keyset(keyset_id="noexist", new_name="X") is False

    def test_rename_marks_dirty(self, collection: KeysetCollection) -> None:
        """Test objective: Verify rename marks collection and keyset dirty."""
        ks = collection.add_keyset(keyset_name="Old")
        collection.is_dirty = False
        collection.rename_keyset(keyset_id=_id(ks), new_name="New")
        assert collection.is_dirty is True
        assert ks.is_dirty is True


# ============================================================================
# promote_keyset / demote_keyset
# ============================================================================


class TestPromoteKeyset:
    """Test promote_keyset(*, keyset_id) — AC-11."""

    def test_promote_swaps_with_previous(self, collection: KeysetCollection) -> None:
        """Test objective: Verify promote swaps with previous keyset."""
        ks1 = collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        success, swapped = collection.promote_keyset(keyset_id=_id(ks2))
        assert success is True
        assert swapped is ks1
        names = [ks.keyset_name for ks in collection.get_keysets_ordered()]
        assert names == ["Two", "One"]

    def test_promote_first_is_noop(self, collection: KeysetCollection) -> None:
        """Test objective: Verify promote on first keyset is no-op (AC-11)."""
        ks1 = collection.add_keyset(keyset_name="Only")
        success, swapped = collection.promote_keyset(keyset_id=_id(ks1))
        assert success is False
        assert swapped is None

    def test_promote_maintains_contiguous_orders(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify orders remain contiguous 1..N after promote."""
        collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        collection.add_keyset(keyset_name="Three")
        collection.promote_keyset(keyset_id=_id(ks2))
        orders = [ks.progression_order for ks in collection.get_keysets_ordered()]
        assert orders == [1, 2, 3]

    def test_promote_nonexistent_returns_false(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify promote on invalid id returns (False, None)."""
        success, swapped = collection.promote_keyset(keyset_id="bad-id")
        assert success is False
        assert swapped is None


class TestDemoteKeyset:
    """Test demote_keyset(*, keyset_id) — AC-11."""

    def test_demote_swaps_with_next(self, collection: KeysetCollection) -> None:
        """Test objective: Verify demote swaps with next keyset."""
        ks1 = collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        success, swapped = collection.demote_keyset(keyset_id=_id(ks1))
        assert success is True
        assert swapped is ks2
        names = [ks.keyset_name for ks in collection.get_keysets_ordered()]
        assert names == ["Two", "One"]

    def test_demote_last_is_noop(self, collection: KeysetCollection) -> None:
        """Test objective: Verify demote on last keyset is no-op (AC-11)."""
        ks1 = collection.add_keyset(keyset_name="Only")
        success, swapped = collection.demote_keyset(keyset_id=_id(ks1))
        assert success is False
        assert swapped is None

    def test_demote_maintains_contiguous_orders(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify orders remain contiguous 1..N after demote."""
        ks1 = collection.add_keyset(keyset_name="One")
        collection.add_keyset(keyset_name="Two")
        collection.add_keyset(keyset_name="Three")
        collection.demote_keyset(keyset_id=_id(ks1))
        orders = [ks.progression_order for ks in collection.get_keysets_ordered()]
        assert orders == [1, 2, 3]

    def test_demote_nonexistent_returns_false(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify demote on invalid id returns (False, None)."""
        success, swapped = collection.demote_keyset(keyset_id="bad-id")
        assert success is False
        assert swapped is None


# ============================================================================
# add_key_to_keyset — cross-keyset uniqueness (AC-9)
# ============================================================================


class TestAddKeyToKeyset:
    """Test add_key_to_keyset(*, keyset_id, key_char, is_new_key)."""

    def test_add_key_returns_keyset_key(self, collection: KeysetCollection) -> None:
        """Test objective: Verify add_key_to_keyset returns a KeysetKey."""
        ks = collection.add_keyset(keyset_name="P1")
        key = collection.add_key_to_keyset(
            keyset_id=_id(ks), key_char="a", is_new_key=True
        )
        assert isinstance(key, KeysetKey)
        assert key.key_char == "a"

    def test_rejects_key_in_earlier_progression(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify adding key that exists in earlier keyset raises (AC-9)."""
        ks1 = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="a", is_new_key=True
        )
        ks2 = collection.add_keyset(keyset_name="P2")
        with pytest.raises(KeysetValidationError, match="earlier progression"):
            collection.add_key_to_keyset(
                keyset_id=_id(ks2), key_char="a", is_new_key=True
            )

    def test_moves_key_from_later_keyset(self, collection: KeysetCollection) -> None:
        """Test objective: Verify key in later keyset is moved to target (AC-9)."""
        ks1 = collection.add_keyset(keyset_name="P1")
        ks2 = collection.add_keyset(keyset_name="P2")
        collection.add_key_to_keyset(
            keyset_id=_id(ks2), key_char="b", is_new_key=True
        )
        # Now add 'b' to earlier keyset — should move it from P2
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="b", is_new_key=True
        )
        assert ks1.has_key(key_char="b") is True
        assert ks2.has_key(key_char="b") is False

    def test_rejects_invalid_keyset_id(self, collection: KeysetCollection) -> None:
        """Test objective: Verify invalid keyset_id raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            collection.add_key_to_keyset(
                keyset_id="bad-id", key_char="a", is_new_key=True
            )

    def test_marks_collection_dirty(self, collection: KeysetCollection) -> None:
        """Test objective: Verify adding key marks collection dirty."""
        ks = collection.add_keyset(keyset_name="P1")
        collection.is_dirty = False
        collection.add_key_to_keyset(
            keyset_id=_id(ks), key_char="x", is_new_key=True
        )
        assert collection.is_dirty is True


# ============================================================================
# remove_key_from_keyset
# ============================================================================


class TestRemoveKeyFromKeyset:
    """Test remove_key_from_keyset(*, keyset_id, key_char)."""

    def test_remove_existing_returns_true(self, collection: KeysetCollection) -> None:
        """Test objective: Verify removing an existing key returns True."""
        ks = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks), key_char="a", is_new_key=True
        )
        assert collection.remove_key_from_keyset(
            keyset_id=_id(ks), key_char="a"
        ) is True

    def test_remove_nonexistent_key_returns_false(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify removing non-existent key returns False."""
        ks = collection.add_keyset(keyset_name="P1")
        assert collection.remove_key_from_keyset(
            keyset_id=_id(ks), key_char="z"
        ) is False

    def test_remove_from_nonexistent_keyset_returns_false(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify removing from invalid keyset returns False."""
        assert collection.remove_key_from_keyset(
            keyset_id="bad-id", key_char="a"
        ) is False

    def test_remove_marks_dirty(self, collection: KeysetCollection) -> None:
        """Test objective: Verify removing key marks collection dirty."""
        ks = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks), key_char="a", is_new_key=True
        )
        collection.is_dirty = False
        collection.remove_key_from_keyset(keyset_id=_id(ks), key_char="a")
        assert collection.is_dirty is True


# ============================================================================
# get_keyset / get_keysets_ordered
# ============================================================================


class TestQueryMethods:
    """Test get_keyset and get_keysets_ordered."""

    def test_get_keyset_returns_keyset_by_id(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify get_keyset returns the correct keyset."""
        ks = collection.add_keyset(keyset_name="Target")
        found = collection.get_keyset(keyset_id=_id(ks))
        assert found is ks

    def test_get_keyset_returns_none_for_missing(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify get_keyset returns None for invalid id."""
        assert collection.get_keyset(keyset_id="nonexistent") is None

    def test_get_keysets_ordered_returns_sorted_list(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify keysets are returned sorted by progression_order."""
        collection.add_keyset(keyset_name="Third")
        collection.add_keyset(keyset_name="First")
        collection.add_keyset(keyset_name="Second")
        ordered = collection.get_keysets_ordered()
        names = [ks.keyset_name for ks in ordered]
        assert names == ["Third", "First", "Second"]
        orders = [ks.progression_order for ks in ordered]
        assert orders == [1, 2, 3]

    def test_get_keysets_ordered_empty(self, collection: KeysetCollection) -> None:
        """Test objective: Verify empty collection returns empty list."""
        assert collection.get_keysets_ordered() == []


# ============================================================================
# key_exists_in_collection
# ============================================================================


class TestKeyExistsInCollection:
    """Test key_exists_in_collection(*, key_char)."""

    def test_returns_keyset_id_when_found(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify returns keyset_id containing the key."""
        ks = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks), key_char="a", is_new_key=True
        )
        result = collection.key_exists_in_collection(key_char="a")
        assert result == _id(ks)

    def test_returns_none_when_not_found(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify returns None when key not in any keyset."""
        collection.add_keyset(keyset_name="P1")
        assert collection.key_exists_in_collection(key_char="z") is None


# ============================================================================
# get_mastered_and_current_keys
# ============================================================================


class TestGetMasteredAndCurrentKeys:
    """Test get_mastered_and_current_keys(*, keyset_id)."""

    def test_returns_mastered_and_current(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify correct mastered/current key partitioning."""
        ks1 = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="a", is_new_key=True
        )
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="s", is_new_key=True
        )
        ks2 = collection.add_keyset(keyset_name="P2")
        collection.add_key_to_keyset(
            keyset_id=_id(ks2), key_char="d", is_new_key=True
        )
        mastered, current = collection.get_mastered_and_current_keys(
            keyset_id=_id(ks2)
        )
        assert mastered == ["a", "s"]  # sorted
        assert current == ["d"]

    def test_first_keyset_has_empty_mastered(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify first keyset has no mastered keys."""
        ks1 = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="a", is_new_key=True
        )
        mastered, current = collection.get_mastered_and_current_keys(
            keyset_id=_id(ks1)
        )
        assert mastered == []
        assert current == ["a"]

    def test_nonexistent_keyset_returns_empty(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify nonexistent keyset returns empty tuples."""
        mastered, current = collection.get_mastered_and_current_keys(
            keyset_id="nonexistent"
        )
        assert mastered == []
        assert current == []

    def test_mastered_keys_are_unique_and_sorted(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify mastered keys are unique and sorted alphabetically."""
        ks1 = collection.add_keyset(keyset_name="P1")
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="c", is_new_key=True
        )
        collection.add_key_to_keyset(
            keyset_id=_id(ks1), key_char="a", is_new_key=True
        )
        ks2 = collection.add_keyset(keyset_name="P2")
        collection.add_key_to_keyset(
            keyset_id=_id(ks2), key_char="b", is_new_key=True
        )
        ks3 = collection.add_keyset(keyset_name="P3")
        collection.add_key_to_keyset(
            keyset_id=_id(ks3), key_char="z", is_new_key=True
        )
        mastered, _ = collection.get_mastered_and_current_keys(
            keyset_id=_id(ks3)
        )
        assert mastered == ["a", "b", "c"]


# ============================================================================
# save_all
# ============================================================================


class TestSaveAll:
    """Test save_all(*, updated_by)."""

    def test_save_all_clears_dirty_flags(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify save_all clears is_dirty on collection and keysets."""
        ks = collection.add_keyset(keyset_name="Persist")
        collection.add_key_to_keyset(
            keyset_id=_id(ks), key_char="x", is_new_key=True
        )
        collection.save_all(updated_by=TEST_USER_ID)
        assert collection.is_dirty is False
        assert ks.is_dirty is False

    def test_save_all_sets_in_db_true(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify save_all sets in_db=True on all keysets."""
        ks = collection.add_keyset(keyset_name="New")
        assert ks.in_db is False
        collection.save_all(updated_by=TEST_USER_ID)
        assert ks.in_db is True

    def test_save_all_detects_duplicate_names(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify save_all raises on duplicate keyset names."""
        collection.add_keyset(keyset_name="Dup")
        collection.add_keyset(keyset_name="dup")
        with pytest.raises(KeysetValidationError, match="[Dd]uplicate"):
            collection.save_all(updated_by=TEST_USER_ID)

    def test_save_all_validates_progressive_uniqueness(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify save_all catches key in earlier progression."""
        ks1 = collection.add_keyset(keyset_name="P1")
        ks2 = collection.add_keyset(keyset_name="P2")
        # Manually inject same key in both — bypass business logic
        ks1.keys.append(KeysetKey(key_char="a", is_new_key=True))
        ks2.keys.append(KeysetKey(key_char="a", is_new_key=True))
        with pytest.raises(KeysetValidationError, match="earlier progression"):
            collection.save_all(updated_by=TEST_USER_ID)

    def test_save_all_persists_deletions(
        self, collection: KeysetCollection, repo: InMemoryKeysetRepository
    ) -> None:
        """Test objective: Verify save_all persists pending deletions to repo."""
        ks = collection.add_keyset(keyset_name="ToDelete")
        collection.save_all(updated_by=TEST_USER_ID)
        # Delete and save again
        collection.delete_keyset(keyset_id=_id(ks))
        collection.save_all(updated_by=TEST_USER_ID)
        # Verify deleted from repo
        assert repo.get_by_id(_id(ks)) is None


# ============================================================================
# is_dirty PROPERTY
# ============================================================================


class TestIsDirtyProperty:
    """Test is_dirty property on the collection."""

    def test_clean_on_init(self, collection: KeysetCollection) -> None:
        """Test objective: Verify new collection is not dirty."""
        assert collection.is_dirty is False

    def test_dirty_after_add(self, collection: KeysetCollection) -> None:
        """Test objective: Verify collection is dirty after adding a keyset."""
        collection.add_keyset(keyset_name="Test")
        assert collection.is_dirty is True

    def test_clean_after_save(self, collection: KeysetCollection) -> None:
        """Test objective: Verify collection is clean after save_all."""
        collection.add_keyset(keyset_name="Test")
        collection.save_all(updated_by=TEST_USER_ID)
        assert collection.is_dirty is False


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_collection_save_is_noop(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify save_all on empty collection works without error."""
        collection.save_all(updated_by=TEST_USER_ID)
        assert collection.is_dirty is False

    def test_single_keyset_promote_noop(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify promote on single keyset is no-op."""
        ks = collection.add_keyset(keyset_name="Only")
        success, _ = collection.promote_keyset(keyset_id=_id(ks))
        assert success is False

    def test_single_keyset_demote_noop(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify demote on single keyset is no-op."""
        ks = collection.add_keyset(keyset_name="Only")
        success, _ = collection.demote_keyset(keyset_id=_id(ks))
        assert success is False

    def test_load_one_add_one_save_both(
        self, collection: KeysetCollection, repo: InMemoryKeysetRepository,
        keyboard_id: str
    ) -> None:
        """Test objective: Verify mixed load + create persists both (AC-15)."""
        # Save one keyset via repo directly (simulating load)
        ks_db = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="FromDB",
            progression_order=1,
        )
        repo.save(ks_db, updated_by=TEST_USER_ID)
        # Load into collection
        collection.load_for_keyboard(keyboard_id=keyboard_id)
        # Add another
        collection.add_keyset(keyset_name="NewOne")
        collection.save_all(updated_by=TEST_USER_ID)
        # Both should be in repo
        all_keysets = repo.list_for_keyboard(keyboard_id)
        assert len(all_keysets) == 2

    def test_delete_all_keysets_leaves_empty(
        self, collection: KeysetCollection
    ) -> None:
        """Test objective: Verify deleting all keysets leaves collection empty."""
        ks1 = collection.add_keyset(keyset_name="One")
        ks2 = collection.add_keyset(keyset_name="Two")
        collection.delete_keyset(keyset_id=_id(ks1))
        collection.delete_keyset(keyset_id=_id(ks2))
        assert collection.get_keysets_ordered() == []


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
