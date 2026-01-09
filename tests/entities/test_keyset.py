"""Comprehensive tests for Keyset entity.

Tests cover creation, serialization, validation, UUID generation, state tracking,
and edge cases as specified in Requirements/Keyset_req.md.

This tests the ENTITIES LAYER ONLY - pure unit tests with no database or mocks.
"""

import uuid
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from entities.keyset import Keyset
from entities.keyset_key import KeysetKey

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_keyboard_id() -> str:
    """Fixture providing a valid keyboard UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def valid_keyset_data(valid_keyboard_id: str) -> Dict[str, Any]:
    """Fixture providing valid keyset data for testing."""
    return {
        "keyboard_id": valid_keyboard_id,
        "keyset_name": "Home Row",
        "progression_order": 1,
        "keys": [],
    }


@pytest.fixture
def sample_keyset(valid_keyset_data: Dict[str, Any]) -> Keyset:
    """Fixture providing a sample Keyset instance."""
    return Keyset(**valid_keyset_data)


# ============================================================================
# KEYSET CREATION TESTS
# ============================================================================


class TestKeysetCreation:
    """Test Keyset entity creation and validation."""

    def test_keyset_creation_with_valid_data(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test creating a Keyset with valid data."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.keyboard_id == valid_keyset_data["keyboard_id"]
        assert keyset.keyset_name == valid_keyset_data["keyset_name"]
        assert keyset.progression_order == valid_keyset_data["progression_order"]
        assert keyset.keys == []
        assert keyset.in_db is False
        assert keyset.is_dirty is False

    def test_keyset_auto_generates_uuid(self, valid_keyset_data: Dict[str, Any]) -> None:
        """AC: UUID Generation - Keyset automatically generates UUID when not provided."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.keyset_id is not None
        assert isinstance(keyset.keyset_id, str)
        # Verify it's a valid UUID
        uuid.UUID(keyset.keyset_id)

    def test_keyset_accepts_provided_uuid(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test Keyset accepts a provided UUID."""
        provided_uuid = str(uuid.uuid4())
        data = {**valid_keyset_data, "keyset_id": provided_uuid}
        keyset = Keyset(**data)
        assert keyset.keyset_id == provided_uuid

    def test_keyset_with_keys(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test creating Keyset with keys."""
        keys = [
            KeysetKey(key_char="a", is_new_key=False),
            KeysetKey(key_char="b", is_new_key=True),
        ]
        data = {**valid_keyset_data, "keys": keys}
        keyset = Keyset(**data)
        assert len(keyset.keys) == 2
        assert keyset.keys[0].key_char == "a"
        assert keyset.keys[1].key_char == "b"
        assert keyset.keys[1].is_new_key is True


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestKeysetValidation:
    """Test Keyset validation rules."""

    def test_keyset_name_required(self, valid_keyboard_id: str) -> None:
        """Test keyset_name is required."""
        with pytest.raises(ValidationError):
            Keyset(
                keyboard_id=valid_keyboard_id,
                keyset_name="",
                progression_order=1,
            )

    def test_keyset_name_length_limits(self, valid_keyboard_id: str) -> None:
        """Test keyset_name must be 1-100 characters."""
        # Valid names
        Keyset(keyboard_id=valid_keyboard_id, keyset_name="A", progression_order=1)
        Keyset(keyboard_id=valid_keyboard_id, keyset_name="A" * 100, progression_order=1)

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            Keyset(keyboard_id=valid_keyboard_id, keyset_name="A" * 101, progression_order=1)
        assert "1..100 characters" in str(exc_info.value).lower()

    def test_keyset_name_strips_whitespace(self, valid_keyboard_id: str) -> None:
        """Test keyset_name strips leading/trailing whitespace."""
        keyset = Keyset(
            keyboard_id=valid_keyboard_id,
            keyset_name="  Home Row  ",
            progression_order=1,
        )
        assert keyset.keyset_name == "Home Row"

    def test_progression_order_must_be_positive(self, valid_keyboard_id: str) -> None:
        """Test progression_order must be >= 1."""
        # Valid
        Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=1)
        Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=999)

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=0)
        assert ">= 1" in str(exc_info.value).lower()

        with pytest.raises(ValidationError):
            Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=-1)

    def test_progression_order_rejects_boolean(self, valid_keyboard_id: str) -> None:
        """Test progression_order rejects boolean values."""
        with pytest.raises(ValidationError) as exc_info:
            Keyset(
                keyboard_id=valid_keyboard_id,
                keyset_name="Test",
                progression_order=True,  # type: ignore[arg-type]
            )
        assert "positive integer" in str(exc_info.value).lower()

    def test_progression_order_rejects_non_int_types(self, valid_keyboard_id: str) -> None:
        """Test progression_order rejects float, non-numeric strings, and None."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=1.5)
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order="abc")  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=None)  # type: ignore[arg-type]

    def test_keyboard_id_required(self) -> None:
        """Test keyboard_id is required."""
        with pytest.raises(ValidationError):
            Keyset(keyset_name="Test", progression_order=1)  # type: ignore[call-arg]

    def test_keyboard_id_must_be_non_empty(self) -> None:
        """Test keyboard_id must be non-empty."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id="", keyset_name="Test", progression_order=1)

    def test_keyboard_id_must_be_string_non_whitespace(self) -> None:
        """Test keyboard_id rejects whitespace-only and non-string values."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id="   ", keyset_name="Test", progression_order=1)
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=123, keyset_name="Test", progression_order=1)  # type: ignore[arg-type]

    def test_keyset_name_must_be_string(self, valid_keyboard_id: str) -> None:
        """Test keyset_name rejects non-string values."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=valid_keyboard_id, keyset_name=123, progression_order=1)  # type: ignore[arg-type]

    def test_keyset_id_cannot_be_empty_string(self, valid_keyboard_id: str) -> None:
        """Test keyset_id rejects empty string."""
        with pytest.raises(ValidationError):
            Keyset(
                keyboard_id=valid_keyboard_id, keyset_name="Test", progression_order=1, keyset_id=""
            )


# ============================================================================
# STATE TRACKING TESTS
# ============================================================================


class TestKeysetStateTracking:
    """Test Keyset database state tracking."""

    def test_keyset_in_db_defaults_to_false(self, valid_keyset_data: Dict[str, Any]) -> None:
        """AC: Database State Tracking - New keysets created in UI marked with in_db=False."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.in_db is False

    def test_keyset_in_db_can_be_set_true(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test in_db can be set to True (after loading from DB)."""
        data = {**valid_keyset_data, "in_db": True}
        keyset = Keyset(**data)
        assert keyset.in_db is True

    def test_keyset_is_dirty_defaults_to_false(self, valid_keyset_data: Dict[str, Any]) -> None:
        """AC: Dirty Flag Lifecycle - Keysets loaded from DB have is_dirty=False."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.is_dirty is False

    def test_keyset_is_dirty_set_on_name_change(self, sample_keyset: Keyset) -> None:
        """AC: Dirty Flag Lifecycle - Keyset edited in UI (name) sets is_dirty=True."""
        assert sample_keyset.is_dirty is False
        sample_keyset.keyset_name = "New Name"
        assert sample_keyset.is_dirty is True

    def test_keyset_is_dirty_set_on_order_change(self, sample_keyset: Keyset) -> None:
        """AC: Dirty Flag Lifecycle - Keyset edited in UI (order) sets is_dirty=True."""
        assert sample_keyset.is_dirty is False
        sample_keyset.progression_order = 5
        assert sample_keyset.is_dirty is True

    def test_keyset_is_dirty_set_on_keys_change(self, sample_keyset: Keyset) -> None:
        """AC: Dirty Flag Lifecycle - Keyset edited in UI (keys) sets is_dirty=True."""
        assert sample_keyset.is_dirty is False
        sample_keyset.keys = [KeysetKey(key_char="a", is_new_key=False)]
        assert sample_keyset.is_dirty is True

    def test_keyset_is_dirty_not_set_on_id_change(self, sample_keyset: Keyset) -> None:
        """Test is_dirty is NOT set when ID fields are changed."""
        assert sample_keyset.is_dirty is False
        sample_keyset.keyset_id = str(uuid.uuid4())
        assert sample_keyset.is_dirty is False  # IDs don't make it dirty

    def test_keyset_is_dirty_not_set_on_in_db_change(self, sample_keyset: Keyset) -> None:
        """Test is_dirty is NOT set when in_db is changed."""
        assert sample_keyset.is_dirty is False
        sample_keyset.in_db = True
        assert sample_keyset.is_dirty is False

    def test_keyset_is_dirty_not_set_on_is_dirty_change(self, sample_keyset: Keyset) -> None:
        """Test is_dirty is NOT set when is_dirty itself is changed (no recursion)."""
        sample_keyset.keyset_name = "Changed"
        assert sample_keyset.is_dirty is True
        sample_keyset.is_dirty = False
        assert sample_keyset.is_dirty is False

    def test_keyset_add_remove_key_dirty_behavior(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test add_key/remove_key set dirty appropriately and missing remove does not dirty."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.is_dirty is False
        added = keyset.add_key(key_char="x", is_new_key=True)
        assert added.key_char == "x"
        assert keyset.is_dirty is True
        keyset.is_dirty = False
        assert keyset.remove_key(key_char="x") is True
        assert keyset.is_dirty is True
        keyset.is_dirty = False
        assert keyset.remove_key(key_char="missing") is False
        assert keyset.is_dirty is False


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================


class TestKeysetSerialization:
    """Test Keyset serialization methods."""

    def test_keyset_to_dict(self, sample_keyset: Keyset) -> None:
        """Test Keyset to_dict method."""
        result = sample_keyset.to_dict()
        assert isinstance(result, dict)
        assert result["keyboard_id"] == sample_keyset.keyboard_id
        assert result["keyset_name"] == sample_keyset.keyset_name
        assert result["progression_order"] == sample_keyset.progression_order
        assert result["in_db"] == sample_keyset.in_db
        assert result["is_dirty"] == sample_keyset.is_dirty
        assert result["keyset_id"] == sample_keyset.keyset_id
        assert isinstance(result["keys"], list)

    def test_keyset_to_dict_with_keys(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test Keyset to_dict with nested keys."""
        keys = [KeysetKey(key_char="a", is_new_key=False)]
        data = {**valid_keyset_data, "keys": keys}
        keyset = Keyset(**data)
        result = keyset.to_dict()
        assert len(result["keys"]) == 1
        assert result["keys"][0]["key_char"] == "a"

    def test_keyset_from_dict(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test Keyset from_dict method."""
        keyset_id = str(uuid.uuid4())
        data = {**valid_keyset_data, "keyset_id": keyset_id}
        keyset = Keyset.from_dict(data)
        assert keyset.keyboard_id == data["keyboard_id"]
        assert keyset.keyset_name == data["keyset_name"]
        assert keyset.progression_order == data["progression_order"]
        assert keyset.keyset_id == keyset_id

    def test_keyset_from_dict_with_keys(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test Keyset from_dict with nested keys."""
        key_data = {"key_char": "a", "is_new_key": False}
        data = {**valid_keyset_data, "keys": [key_data]}
        keyset = Keyset.from_dict(data)
        assert len(keyset.keys) == 1
        assert isinstance(keyset.keys[0], KeysetKey)
        assert keyset.keys[0].key_char == "a"

    def test_keyset_roundtrip_serialization(self, sample_keyset: Keyset) -> None:
        """Test to_dict -> from_dict roundtrip preserves all data."""
        # Add a key to test nested serialization
        sample_keyset.keys = [KeysetKey(key_char="x", is_new_key=True)]

        dict_data = sample_keyset.to_dict()
        restored = Keyset.from_dict(dict_data)

        assert restored.keyset_id == sample_keyset.keyset_id
        assert restored.keyboard_id == sample_keyset.keyboard_id
        assert restored.keyset_name == sample_keyset.keyset_name
        assert restored.progression_order == sample_keyset.progression_order
        assert restored.in_db == sample_keyset.in_db
        assert len(restored.keys) == len(sample_keyset.keys)
        assert restored.keys[0].key_char == sample_keyset.keys[0].key_char

    def test_keyset_roundtrip_with_non_ascii_key(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test roundtrip serialization preserves non-ASCII key characters."""
        keyset = Keyset(**{**valid_keyset_data, "keys": [KeysetKey(key_char="é", is_new_key=True)]})
        restored = Keyset.from_dict(keyset.to_dict())
        assert restored.keys[0].key_char == "é"


# ============================================================================
# EDGE CASES AND ERROR CONDITIONS
# ============================================================================


class TestKeysetEdgeCases:
    """Test edge cases and error conditions."""

    def test_keyset_forbids_extra_fields(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test Keyset forbids extra fields."""
        data = {**valid_keyset_data, "extra_field": "value"}
        with pytest.raises(ValidationError) as exc_info:
            Keyset(**data)
        assert "extra" in str(exc_info.value).lower()

    def test_keyset_handles_none_keyset_id(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test Keyset handles None keyset_id gracefully."""
        data = {**valid_keyset_data, "keyset_id": None}
        keyset = Keyset(**data)
        # Should auto-generate UUID
        assert keyset.keyset_id is not None
        uuid.UUID(keyset.keyset_id)

    def test_keyset_validates_on_assignment(self, sample_keyset: Keyset) -> None:
        """Test Keyset validates fields on assignment (validate_assignment=True)."""
        # Valid assignment
        sample_keyset.keyset_name = "New Name"
        assert sample_keyset.keyset_name == "New Name"

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            sample_keyset.keyset_name = ""  # Empty after strip

        with pytest.raises(ValidationError):
            sample_keyset.keyset_name = "A" * 101  # Too long

        with pytest.raises(ValidationError):
            sample_keyset.progression_order = 0  # Must be >= 1

        with pytest.raises(ValidationError):
            sample_keyset.keyset_id = ""  # Empty string not allowed

    def test_keyset_from_dict_rejects_extra_fields_in_nested_keys(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test from_dict rejects nested keys containing extra fields."""
        bad_key = {"key_char": "a", "is_new_key": False, "extra": "x"}
        data = {**valid_keyset_data, "keys": [bad_key]}
        with pytest.raises(ValidationError):
            Keyset.from_dict(data)
