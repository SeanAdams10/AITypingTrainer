"""Tests for InMemoryKeysetRepository.

Tests the repository implementation following the IKeysetRepository protocol.
These are pure unit tests that run fast without database dependencies.
"""

import uuid

import pytest

from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_repository_memory import InMemoryKeysetRepository

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def repo() -> InMemoryKeysetRepository:
    """Fixture providing a fresh in-memory repository."""
    return InMemoryKeysetRepository()


@pytest.fixture
def keyboard_id() -> str:
    """Fixture providing a test keyboard UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def user_id() -> str:
    """Fixture providing a test user UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_keyset(keyboard_id: str) -> Keyset:
    """Fixture providing a sample keyset with keys."""
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

    def test_list_empty_keyboard(self, repo: InMemoryKeysetRepository, keyboard_id: str) -> None:
        """Test listing keysets for keyboard with no keysets."""
        result = repo.list_for_keyboard(keyboard_id)
        assert result == []

    def test_list_returns_keysets_for_keyboard(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test listing returns keysets for specific keyboard."""
        repo.save(sample_keyset, updated_by=user_id)
        result = repo.list_for_keyboard(keyboard_id)
        assert len(result) == 1
        assert result[0].keyset_name == "Home Row"

    def test_list_orders_by_progression_order(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test listing returns keysets ordered by progression_order ASC."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="Third", progression_order=3)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="First", progression_order=1)
        ks3 = Keyset(keyboard_id=keyboard_id, keyset_name="Second", progression_order=2)

        repo.save(ks1, updated_by=user_id)
        repo.save(ks2, updated_by=user_id)
        repo.save(ks3, updated_by=user_id)

        result = repo.list_for_keyboard(keyboard_id)
        assert len(result) == 3
        assert result[0].keyset_name == "First"
        assert result[1].keyset_name == "Second"
        assert result[2].keyset_name == "Third"

    def test_list_excludes_deleted_keysets(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test listing excludes soft-deleted keysets."""
        repo.save(sample_keyset, updated_by=user_id)
        repo.delete(sample_keyset.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]

        result = repo.list_for_keyboard(keyboard_id)
        assert result == []

    def test_list_filters_by_keyboard_id(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test listing only returns keysets for specified keyboard."""
        other_keyboard_id = str(uuid.uuid4())

        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="KB1", progression_order=1)
        ks2 = Keyset(keyboard_id=other_keyboard_id, keyset_name="KB2", progression_order=1)

        repo.save(ks1, updated_by=user_id)
        repo.save(ks2, updated_by=user_id)

        result = repo.list_for_keyboard(keyboard_id)
        assert len(result) == 1
        assert result[0].keyset_name == "KB1"

    def test_list_validates_keyboard_id(self, repo: InMemoryKeysetRepository) -> None:
        """Test listing validates keyboard_id parameter."""
        with pytest.raises(ValueError, match="keyboard_id must be a non-empty string"):
            repo.list_for_keyboard("")

        with pytest.raises(ValueError, match="keyboard_id must be a non-empty string"):
            repo.list_for_keyboard(None)  # type: ignore[arg-type]


# ============================================================================
# GET_BY_ID TESTS
# ============================================================================


class TestGetById:
    """Test get_by_id method."""

    def test_get_existing_keyset(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test retrieving existing keyset by ID."""
        repo.save(sample_keyset, updated_by=user_id)
        result = repo.get_by_id(sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert result is not None
        assert result.keyset_name == "Home Row"
        assert len(result.keys) == 2

    def test_get_nonexistent_keyset(self, repo: InMemoryKeysetRepository) -> None:
        """Test retrieving nonexistent keyset returns None."""
        result = repo.get_by_id(str(uuid.uuid4()))
        assert result is None

    def test_get_deleted_keyset(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test retrieving deleted keyset returns None."""
        repo.save(sample_keyset, updated_by=user_id)
        repo.delete(sample_keyset.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]

        result = repo.get_by_id(sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert result is None

    def test_get_validates_keyset_id(self, repo: InMemoryKeysetRepository) -> None:
        """Test get_by_id validates keyset_id parameter."""
        with pytest.raises(ValueError, match="keyset_id must be a non-empty string"):
            repo.get_by_id("")

        with pytest.raises(ValueError, match="keyset_id must be a non-empty string"):
            repo.get_by_id(None)  # type: ignore[arg-type]


# ============================================================================
# SAVE TESTS
# ============================================================================


class TestSave:
    """Test save method."""

    def test_save_new_keyset_generates_id(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test saving new keyset generates ID if not provided."""
        ks = Keyset(
            keyset_id=None,
            keyboard_id=keyboard_id,
            keyset_name="Test",
            progression_order=1,
        )
        repo.save(ks, updated_by=user_id)
        assert ks.keyset_id is not None
        uuid.UUID(ks.keyset_id)  # Validates UUID format

    def test_save_sets_in_db_flag(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test save sets in_db=True flag."""
        assert sample_keyset.in_db is False
        repo.save(sample_keyset, updated_by=user_id)
        assert sample_keyset.in_db is True

    def test_save_clears_is_dirty_flag(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test save clears is_dirty flag."""
        sample_keyset.is_dirty = True
        repo.save(sample_keyset, updated_by=user_id)
        assert sample_keyset.is_dirty is False

    def test_save_stores_keyset_in_memory(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test save stores keyset in memory for retrieval."""
        repo.save(sample_keyset, updated_by=user_id)
        retrieved = repo.get_by_id(sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert retrieved is not None
        assert retrieved.keyset_name == sample_keyset.keyset_name

    def test_save_creates_deep_copy(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test save creates deep copy to prevent mutations."""
        repo.save(sample_keyset, updated_by=user_id)
        sample_keyset.keyset_name = "Modified"

        retrieved = repo.get_by_id(sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert retrieved is not None
        assert retrieved.keyset_name == "Home Row"  # Original name preserved

    def test_save_update_existing_keyset(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test updating existing keyset."""
        repo.save(sample_keyset, updated_by=user_id)
        sample_keyset.keyset_name = "Updated Name"
        repo.save(sample_keyset, updated_by=user_id)

        retrieved = repo.get_by_id(sample_keyset.keyset_id)  # type: ignore[arg-type]
        assert retrieved is not None
        assert retrieved.keyset_name == "Updated Name"

    def test_save_noncontiguous_order_raises(self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str) -> None:
        """Test saving with a gap in progression_order is rejected."""
        ks = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Gap",
            progression_order=2,
        )
        with pytest.raises(ValueError, match="progression_order must be contiguous"):
            repo.save(ks, updated_by=user_id)


# ============================================================================
# DELETE TESTS
# ============================================================================


class TestDelete:
    """Test delete method."""

    def test_delete_existing_keyset(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test deleting existing keyset returns True."""
        repo.save(sample_keyset, updated_by=user_id)
        result = repo.delete(sample_keyset.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]
        assert result is True

    def test_delete_nonexistent_keyset(
        self, repo: InMemoryKeysetRepository, user_id: str
    ) -> None:
        """Test deleting nonexistent keyset returns False."""
        result = repo.delete(str(uuid.uuid4()), deleted_by=user_id)
        assert result is False

    def test_delete_already_deleted_keyset(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test deleting already deleted keyset returns False."""
        repo.save(sample_keyset, updated_by=user_id)
        repo.delete(sample_keyset.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]
        result = repo.delete(sample_keyset.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]
        assert result is False

    def test_delete_is_soft_delete(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test delete is soft delete (data remains in storage)."""
        repo.save(sample_keyset, updated_by=user_id)
        keyset_id = sample_keyset.keyset_id
        repo.delete(keyset_id, deleted_by=user_id)  # type: ignore[arg-type]

        # Data still in storage but marked deleted
        assert keyset_id in repo._keysets
        assert keyset_id in repo._deleted_ids

    def test_delete_validates_keyset_id(
        self, repo: InMemoryKeysetRepository, user_id: str
    ) -> None:
        """Test delete validates keyset_id parameter."""
        with pytest.raises(ValueError, match="keyset_id must be a non-empty string"):
            repo.delete("", deleted_by=user_id)

        with pytest.raises(ValueError, match="keyset_id must be a non-empty string"):
            repo.delete(None, deleted_by=user_id)  # type: ignore[arg-type]


# ============================================================================
# VALIDATE_KEY_PROGRESSION_UNIQUENESS TESTS
# ============================================================================


class TestValidateKeyProgressionUniqueness:
    """Test validate_key_progression_uniqueness method."""

    def test_validate_allows_new_keys_in_first_progression(
        self, repo: InMemoryKeysetRepository, keyboard_id: str
    ) -> None:
        """Test validation allows any keys in first progression."""
        # Should not raise
        repo.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=1,
            keys=["a", "s", "d", "f"],
        )

    def test_validate_allows_keys_not_in_prior_progressions(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test validation allows keys not in prior progressions."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(ks1, updated_by=user_id)

        # Should not raise - 'b' not in progression 1
        repo.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=2,
            keys=["b"],
        )

    def test_validate_rejects_keys_in_prior_progressions(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test validation rejects keys already in prior progressions."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(ks1, updated_by=user_id)

        with pytest.raises(ValueError, match="already exist in earlier progressions"):
            repo.validate_key_progression_uniqueness(
                keyboard_id=keyboard_id,
                progression_order=2,
                keys=["a"],  # 'a' already in progression 1
            )

    def test_validate_checks_multiple_keys(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test validation checks all providing keys."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="s", is_new_key=True),
            ],
        )
        repo.save(ks1, updated_by=user_id)

        with pytest.raises(ValueError, match=r"\['a', 's'\].*already exist"):
            repo.validate_key_progression_uniqueness(
                keyboard_id=keyboard_id,
                progression_order=2,
                keys=["a", "s", "d"],  # 'a' and 's' conflict
            )

    def test_validate_excludes_self_for_updates(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test validation excludes keyset being updated."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(ks1, updated_by=user_id)

        # Should not raise - excluding self
        repo.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=1,
            keys=["a"],
            keyset_id=ks1.keyset_id,
        )

    def test_validate_ignores_deleted_keysets(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test validation ignores keys from deleted keysets."""
        ks1 = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="P1",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(ks1, updated_by=user_id)
        repo.delete(ks1.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]

        # Should not raise - deleted keyset ignored
        repo.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=2,
            keys=["a"],
        )

    def test_validate_filters_by_keyboard(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test validation only checks keysets for same keyboard."""
        other_keyboard_id = str(uuid.uuid4())
        ks1 = Keyset(
            keyboard_id=other_keyboard_id,
            keyset_name="Other KB",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True)],
        )
        repo.save(ks1, updated_by=user_id)

        # Should not raise - different keyboard
        repo.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=2,
            keys=["a"],
        )

    def test_validate_requires_valid_keyboard_id(self, repo: InMemoryKeysetRepository) -> None:
        """Test validation requires valid keyboard_id."""
        with pytest.raises(ValueError, match="keyboard_id must be a non-empty string"):
            repo.validate_key_progression_uniqueness(
                keyboard_id="",
                progression_order=1,
                keys=["a"],
            )

    def test_validate_requires_positive_progression_order(
        self, repo: InMemoryKeysetRepository, keyboard_id: str
    ) -> None:
        """Test validation requires progression_order >= 1."""
        with pytest.raises(ValueError, match="progression_order must be >= 1"):
            repo.validate_key_progression_uniqueness(
                keyboard_id=keyboard_id,
                progression_order=0,
                keys=["a"],
            )


# ============================================================================
# HELPER METHOD TESTS
# ============================================================================


class TestHelperMethods:
    """Test helper methods (clear, count)."""

    def test_clear_removes_all_data(
        self, repo: InMemoryKeysetRepository, sample_keyset: Keyset, user_id: str
    ) -> None:
        """Test clear removes all stored keysets."""
        repo.save(sample_keyset, updated_by=user_id)
        repo.clear()
        assert repo.count() == 0
        assert len(repo._keysets) == 0
        assert len(repo._deleted_ids) == 0

    def test_count_returns_active_keysets_only(
        self, repo: InMemoryKeysetRepository, keyboard_id: str, user_id: str
    ) -> None:
        """Test count returns only active (non-deleted) keysets."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="K1", progression_order=1)
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="K2", progression_order=2)

        repo.save(ks1, updated_by=user_id)
        repo.save(ks2, updated_by=user_id)
        assert repo.count() == 2

        repo.delete(ks1.keyset_id, deleted_by=user_id)  # type: ignore[arg-type]
        assert repo.count() == 1
