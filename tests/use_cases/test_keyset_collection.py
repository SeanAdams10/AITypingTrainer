"""Tests for KeysetCollection use case.

Tests business logic using in-memory repository fakes (no database needed).
These are pure unit tests that run fast and validate business rules.
"""

import uuid

import pytest

from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_repository_memory import InMemoryKeysetRepository
from use_cases.keyset_collection import KeysetCollection, KeysetValidationError

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def repo() -> InMemoryKeysetRepository:
    """Fixture providing a fresh in-memory repository."""
    return InMemoryKeysetRepository()


@pytest.fixture
def collection(repo: InMemoryKeysetRepository) -> KeysetCollection:
    """Fixture providing KeysetCollection with in-memory repository."""
    return KeysetCollection(repo)


@pytest.fixture
def keyboard_id() -> str:
    """Fixture providing a test keyboard UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_keyset(keyboard_id: str) -> Keyset:
    """Fixture providing a sample keyset."""
    return Keyset(
        keyboard_id=keyboard_id,
        keyset_name="Home Row",
        progression_order=1,
        keys=[
            KeysetKey(key_char="a", is_new_key=True),
            KeysetKey(key_char="s", is_new_key=True),
        ],
    )


# ============================================================================
# LIST_FOR_KEYBOARD TESTS
# ============================================================================


class TestListForKeyboard:
    """Test list_for_keyboard method."""

    def test_list_empty_keyboard(self, collection: KeysetCollection, keyboard_id: str) -> None:
        """Test listing keysets for keyboard with no keysets."""
        result = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert result == []

    def test_list_returns_keysets(
        self, collection: KeysetCollection, keyboard_id: str, sample_keyset: Keyset
    ) -> None:
        """Test listing returns keysets for keyboard."""
        collection.add_keyset(sample_keyset)
        result = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert len(result) == 1
        assert result[0].keyset_name == "Home Row"

    def test_list_orders_by_progression(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test listing returns keysets ordered by progression_order."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="Third", progression_order=3)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks3 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)
        collection.add_keyset(ks3)

        result = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert len(result) == 3
        assert result[0].keyset_name == "First"
        assert result[1].keyset_name == "Second"
        assert result[2].keyset_name == "Third"


# ============================================================================
# GET_BY_ID TESTS
# ============================================================================


class TestGetById:
    """Test get_by_id method."""

    def test_get_existing_keyset(self, collection: KeysetCollection, sample_keyset: Keyset) -> None:
        """Test retrieving existing keyset by ID."""
        collection.add_keyset(sample_keyset)
        result = collection.get_by_id(keyset_id=sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert result is not None
        assert result.keyset_name == "Home Row"

    def test_get_nonexistent_keyset(self, collection: KeysetCollection) -> None:
        """Test retrieving nonexistent keyset returns None."""
        result = collection.get_by_id(keyset_id=str(uuid.uuid4()))
        assert result is None


# ============================================================================
# ADD_KEYSET TESTS
# ============================================================================


class TestAddKeyset:
    """Test add_keyset method."""

    def test_add_valid_keyset(self, collection: KeysetCollection, sample_keyset: Keyset) -> None:
        """Test adding a valid keyset."""
        collection.add_keyset(sample_keyset)
        assert sample_keyset.in_db is True
        assert sample_keyset.is_dirty is False

    def test_add_keyset_with_audit_trail(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test adding keyset with updated_by parameter."""
        ks = Keyset(keyboard_id=keyboard_id, keyset_name="Test", progression_order=1)
        collection.add_keyset(ks, updated_by="user123")
        assert ks.in_db is True

    def test_add_keyset_validates_progression_order(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test add_keyset validates progression_order >= 1."""
        # Note: Pydantic already validates this at entity level, but use case reinforces it
        with pytest.raises(ValueError):
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="Test",
                progression_order=0,  # Invalid
            )


# ============================================================================
# UPDATE_KEYSET TESTS
# ============================================================================


class TestUpdateKeyset:
    """Test update_keyset method."""

    def test_update_existing_keyset(
        self, collection: KeysetCollection, sample_keyset: Keyset
    ) -> None:
        """Test updating an existing keyset."""
        collection.add_keyset(sample_keyset)
        sample_keyset.keyset_name = "Updated Name"
        sample_keyset.is_dirty = True
        collection.update_keyset(sample_keyset)

        # Verify update persisted
        result = collection.get_by_id(keyset_id=sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert result is not None
        assert result.keyset_name == "Updated Name"
        assert result.is_dirty is False

    def test_update_requires_in_db(self, collection: KeysetCollection, keyboard_id: str) -> None:
        """Test update_keyset requires keyset to be in database."""
        ks = Keyset(keyboard_id=keyboard_id, keyset_name="Test", progression_order=1)
        # Not saved yet, in_db=False
        with pytest.raises(ValueError, match="not found in database"):
            collection.update_keyset(ks)


# ============================================================================
# DELETE_KEYSET TESTS
# ============================================================================


class TestDeleteKeyset:
    """Test delete_keyset method."""

    def test_delete_existing_keyset(
        self, collection: KeysetCollection, sample_keyset: Keyset
    ) -> None:
        """Test deleting an existing keyset."""
        collection.add_keyset(sample_keyset)
        result = collection.delete_keyset(keyset_id=sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert result is True

        # Verify deleted
        assert collection.get_by_id(keyset_id=sample_keyset.keyset_id) is None  # type: ignore[arg-type]

    def test_delete_nonexistent_keyset(self, collection: KeysetCollection) -> None:
        """Test deleting nonexistent keyset returns False."""
        result = collection.delete_keyset(keyset_id=str(uuid.uuid4()))
        assert result is False


# ============================================================================
# BUSINESS RULE VALIDATION TESTS
# ============================================================================


class TestKeyProgressionUniqueness:
    """Test key progression uniqueness business rule."""

    def test_add_allows_first_progression_any_keys(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test first progression can have any keys."""
        ks = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="s", is_new_key=True),
            ],
        )
        # Should not raise
        collection.add_keyset(ks)

    def test_add_allows_new_keys_not_in_earlier_progressions(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test adding keys not in earlier progressions is allowed."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        collection.add_keyset(ks1)

        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P2",
            progression_order=2,
            keys=[KeysetKey(key_char="b", is_new_key=True)],  # Different key
        )
        # Should not raise
        collection.add_keyset(ks2)

    def test_add_rejects_keys_in_earlier_progressions(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test adding keys already in earlier progressions is rejected."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        collection.add_keyset(ks1)

        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P2",
            progression_order=2,
            keys=[KeysetKey(key_char="a", is_new_key=True)],  # Duplicate!
        )
        with pytest.raises(KeysetValidationError, match="already exist in earlier progressions"):
            collection.add_keyset(ks2)

    def test_add_allows_old_keys_from_earlier_progressions(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test adding keys marked as old (is_new_key=False) is allowed."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        collection.add_keyset(ks1)

        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P2",
            progression_order=2,
            keys=[
                KeysetKey(key_char="a", is_new_key=False),  # Old key, OK
                KeysetKey(key_char="b", is_new_key=True),  # New key, OK
            ],
        )
        # Should not raise
        collection.add_keyset(ks2)

    def test_update_excludes_self_from_validation(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test updating a keyset excludes itself from progression validation."""
        ks = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        collection.add_keyset(ks)

        # Update with same keys should not raise
        ks.keyset_name = "Updated"
        ks.is_dirty = True
        collection.update_keyset(ks)


# ============================================================================
# SAVE_ALL TESTS
# ============================================================================


class TestSaveAll:
    """Test save_all batch operation."""

    def test_save_all_valid_keysets(self, collection: KeysetCollection, keyboard_id: str) -> None:
        """Test saving multiple valid keysets in batch."""
        keysets = [
            Keyset(keyboard_id=keyboard_id, keyset_name="K1", progression_order=1),
            Keyset(keyboard_id=keyboard_id, keyset_name="K2", progression_order=2),
            Keyset(keyboard_id=keyboard_id, keyset_name="K3", progression_order=3),
        ]
        collection.save_all(keysets)

        result = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert len(result) == 3

    def test_save_all_validates_before_saving(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test save_all validates all keysets before saving any."""
        # Add first keyset
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        collection.add_keyset(ks1)

        # Try to save batch with invalid keyset
        keysets = [
            Keyset(keyboard_id=keyboard_id, keyset_name="K2", progression_order=2),
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="K3",
                progression_order=3,
                keys=[KeysetKey(key_char="a", is_new_key=True)],  # Duplicate!
            ),
        ]

        with pytest.raises(KeysetValidationError):
            collection.save_all(keysets)

        # Verify nothing was saved (transactional semantics)
        result = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert len(result) == 1  # Only ks1


# ============================================================================
# GET_MASTERED_AND_CURRENT_KEYS TESTS
# ============================================================================


class TestGetMasteredAndCurrentKeys:
    """Test get_mastered_and_current_keys method."""

    def test_get_keys_with_no_earlier_progressions(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test getting keys when there are no earlier progressions."""
        ks = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="s", is_new_key=True),
            ],
        )
        collection.add_keyset(ks)

        mastered, current = collection.get_mastered_and_current_keys(
            keyboard_id=keyboard_id,
            keyset_id=ks.keyset_id,  # type: ignore[arg-type]
        )
        assert mastered == []
        assert current == ["a", "s"]

    def test_get_keys_with_earlier_progressions(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test getting keys with earlier progressions."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="s", is_new_key=True),
            ],
        )
        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P2",
            progression_order=2,
            keys=[
                KeysetKey(key_char="a", is_new_key=False),  # Mastered
                KeysetKey(key_char="s", is_new_key=False),  # Mastered
                KeysetKey(key_char="d", is_new_key=True),  # New
                KeysetKey(key_char="f", is_new_key=True),  # New
            ],
        )
        collection.add_keyset(ks1)
        collection.add_keyset(ks2)

        mastered, current = collection.get_mastered_and_current_keys(
            keyboard_id=keyboard_id,
            keyset_id=ks2.keyset_id,  # type: ignore[arg-type]
        )
        assert mastered == ["a", "s"]
        assert current == ["a", "d", "f", "s"]

    def test_get_keys_deduplicates_mastered(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test mastered keys are deduplicated."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        ks2 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P2",
            progression_order=2,
            keys=[
                KeysetKey(key_char="a", is_new_key=False),  # Repeated
                KeysetKey(key_char="b", is_new_key=True),
            ],
        )
        ks3 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P3",
            progression_order=3,
            keys=[KeysetKey(key_char="c", is_new_key=True)],
        )
        collection.add_keyset(ks1)
        collection.add_keyset(ks2)
        collection.add_keyset(ks3)

        mastered, current = collection.get_mastered_and_current_keys(
            keyboard_id=keyboard_id,
            keyset_id=ks3.keyset_id,  # type: ignore[arg-type]
        )
        # 'a' and 'b' from earlier progressions, deduplicated
        assert mastered == ["a", "b"]
        assert current == ["c"]

    def test_get_keys_returns_empty_for_nonexistent_keyset(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test getting keys for nonexistent keyset returns empty lists."""
        mastered, current = collection.get_mastered_and_current_keys(
            keyboard_id=keyboard_id, keyset_id=str(uuid.uuid4())
        )
        assert mastered == []
        assert current == []

    def test_get_keys_validates_keyboard_match(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test getting keys validates keyboard_id matches keyset."""
        other_keyboard_id = str(uuid.uuid4())
        ks = Keyset(
            keyboard_id=other_keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        collection.add_keyset(ks)

        with pytest.raises(ValueError, match="does not belong to keyboard"):
            collection.get_mastered_and_current_keys(
                keyboard_id=keyboard_id,
                keyset_id=ks.keyset_id,  # type: ignore[arg-type]
            )


# ============================================================================
# PROMOTE_KEYSET TESTS
# ============================================================================


class TestPromoteKeyset:
    """Test promote_keyset method."""

    def test_promote_swaps_progression_orders(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test promoting a keyset swaps progression orders."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)
        ks3 = Keyset(keyboard_id=keyboard_id, keyset_name="Third", progression_order=3)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)
        collection.add_keyset(ks3)

        # Promote ks3 (should swap with ks2) - now returns tuple (success, swapped)
        success, _swapped = collection.promote_keyset(
            keyboard_id=keyboard_id, keyset_id=ks3.keyset_id  # type: ignore[arg-type]
        )
        assert success is True

        # Verify swap - ks3 moved to position 2, ks2 moved to position 3
        keysets = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert keysets[0].keyset_name == "First"
        assert keysets[0].progression_order == 1
        assert keysets[1].keyset_name == "Third"  # Was at position 3
        assert keysets[1].progression_order == 2
        assert keysets[2].keyset_name == "Second"  # Was at position 2
        assert keysets[2].progression_order == 3

    def test_promote_first_keyset_returns_false(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test promoting first keyset returns False (already at top)."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)

        # Try to promote first keyset (already at top)
        success, swapped = collection.promote_keyset(
            keyboard_id=keyboard_id, keyset_id=ks1.keyset_id  # type: ignore[arg-type]
        )
        assert success is False
        assert swapped is None

        # Verify no changes
        keysets = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert keysets[0].keyset_name == "First"
        assert keysets[1].keyset_name == "Second"

    def test_promote_nonexistent_keyset_returns_false(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test promoting nonexistent keyset returns False."""
        success, swapped = collection.promote_keyset(
            keyboard_id=keyboard_id, keyset_id=str(uuid.uuid4())
        )
        assert success is False
        assert swapped is None

    def test_promote_with_audit_trail(self, collection: KeysetCollection, keyboard_id: str) -> None:
        """Test promoting keyset with updated_by parameter."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)

        success, _swapped = collection.promote_keyset(
            keyboard_id=keyboard_id,
            keyset_id=str(ks2.keyset_id),  # Promote second keyset
            updated_by="user123",
        )
        assert success is True


# ============================================================================
# DEMOTE_KEYSET TESTS
# ============================================================================


class TestDemoteKeyset:
    """Test demote_keyset method."""

    def test_demote_swaps_progression_orders(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test demoting a keyset swaps progression orders."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)
        ks3 = Keyset(keyboard_id=keyboard_id, keyset_name="Third", progression_order=3)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)
        collection.add_keyset(ks3)

        # Demote ks1 (should swap with ks2) - now returns tuple (success, swapped)
        success, _swapped = collection.demote_keyset(
            keyboard_id=keyboard_id, keyset_id=ks1.keyset_id  # type: ignore[arg-type]
        )
        assert success is True

        # Verify swap - ks1 moved to position 2, ks2 moved to position 1
        keysets = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert keysets[0].keyset_name == "Second"  # Was at position 2
        assert keysets[0].progression_order == 1
        assert keysets[1].keyset_name == "First"  # Was at position 1
        assert keysets[1].progression_order == 2
        assert keysets[2].keyset_name == "Third"  # Unchanged
        assert keysets[2].progression_order == 3

    def test_demote_last_keyset_returns_false(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test demoting last keyset returns False (already at bottom)."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)

        # Try to demote last keyset (already at bottom)
        success, swapped = collection.demote_keyset(
            keyboard_id=keyboard_id, keyset_id=ks2.keyset_id  # type: ignore[arg-type]
        )
        assert success is False
        assert swapped is None

        # Verify no changes
        keysets = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert keysets[0].keyset_name == "First"
        assert keysets[1].keyset_name == "Second"

    def test_demote_nonexistent_keyset_returns_false(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test demoting nonexistent keyset returns False."""
        success, swapped = collection.demote_keyset(
            keyboard_id=keyboard_id, keyset_id=str(uuid.uuid4())
        )
        assert success is False
        assert swapped is None

    def test_demote_with_audit_trail(self, collection: KeysetCollection, keyboard_id: str) -> None:
        """Test demoting keyset with updated_by parameter."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)

        success, _swapped = collection.demote_keyset(
            keyboard_id=keyboard_id,
            keyset_id=str(ks1.keyset_id),  # Demote first keyset
            updated_by="user123",
        )
        assert success is True

    def test_demote_middle_keyset(
        self, collection: KeysetCollection, keyboard_id: str
    ) -> None:
        """Test demoting middle keyset swaps with next."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)
        ks3 = Keyset(keyboard_id=keyboard_id, keyset_name="Third", progression_order=3)

        collection.add_keyset(ks1)
        collection.add_keyset(ks2)
        collection.add_keyset(ks3)

        # Demote ks2 (should swap with ks3)
        success, _swapped = collection.demote_keyset(
            keyboard_id=keyboard_id, keyset_id=ks2.keyset_id  # type: ignore[arg-type]
        )
        assert success is True

        # Verify swap
        keysets = collection.list_for_keyboard(keyboard_id=keyboard_id)
        assert keysets[0].keyset_name == "First"  # Unchanged
        assert keysets[1].keyset_name == "Third"  # Was at position 3
        assert keysets[2].keyset_name == "Second"  # Was at position 2
