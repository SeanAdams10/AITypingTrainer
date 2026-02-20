"""Tests for Keyset entity.

Tests the Entities layer (Layer 1) — pure unit tests with no database, no mocks.
All validation rules defined in Requirements/Keyset_req.md Section 3.1.

Tests follow TDD delivery standard, testing_and_trustability rules, and
keyword_arguments standard.
"""

import sys
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
def keyboard_id() -> str:
    """Provide a valid keyboard UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def valid_keyset_data(keyboard_id: str) -> Dict[str, Any]:
    """Provide minimal valid data for Keyset construction."""
    return {
        "keyboard_id": keyboard_id,
        "keyset_name": "Home Row",
        "progression_order": 1,
    }


@pytest.fixture
def sample_keyset(valid_keyset_data: Dict[str, Any]) -> Keyset:
    """Provide a ready-made Keyset instance."""
    return Keyset(**valid_keyset_data)


# ============================================================================
# UUID AUTO-GENERATION
# ============================================================================


class TestKeysetUuidGeneration:
    """Test auto-generation and acceptance of UUIDs."""

    def test_auto_generates_uuid_when_not_provided(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test objective: Verify keyset_id is auto-generated as valid UUID."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.keyset_id is not None
        uuid.UUID(keyset.keyset_id)

    def test_each_instance_gets_unique_uuid(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test objective: Verify two instances get distinct UUIDs."""
        ks1 = Keyset(**valid_keyset_data)
        ks2 = Keyset(**valid_keyset_data)
        assert ks1.keyset_id != ks2.keyset_id

    def test_accepts_provided_uuid(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify an explicit keyset_id is preserved."""
        provided = str(uuid.uuid4())
        data = {**valid_keyset_data, "keyset_id": provided}
        keyset = Keyset(**data)
        assert keyset.keyset_id == provided

    def test_auto_generates_uuid_when_none_explicit(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test objective: Verify keyset_id=None triggers auto-generation."""
        data = {**valid_keyset_data, "keyset_id": None}
        keyset = Keyset(**data)
        assert keyset.keyset_id is not None
        uuid.UUID(keyset.keyset_id)


# ============================================================================
# FIELD VALIDATION
# ============================================================================


class TestKeysetNameValidation:
    """Test keyset_name validation: 1-100 chars, strips whitespace."""

    def test_accepts_valid_names(self, keyboard_id: str) -> None:
        """Test objective: Verify names within 1-100 chars are accepted."""
        Keyset(keyboard_id=keyboard_id, keyset_name="A", progression_order=1)
        Keyset(keyboard_id=keyboard_id, keyset_name="A" * 100, progression_order=1)

    def test_rejects_empty_name(self, keyboard_id: str) -> None:
        """Test objective: Verify empty name is rejected."""
        with pytest.raises(ValidationError, match="1..100 characters"):
            Keyset(keyboard_id=keyboard_id, keyset_name="", progression_order=1)

    def test_rejects_name_over_100_chars(self, keyboard_id: str) -> None:
        """Test objective: Verify name > 100 characters is rejected."""
        with pytest.raises(ValidationError, match="1..100 characters"):
            Keyset(keyboard_id=keyboard_id, keyset_name="A" * 101, progression_order=1)

    def test_strips_whitespace(self, keyboard_id: str) -> None:
        """Test objective: Verify leading/trailing whitespace is stripped."""
        keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="  Home Row  ",
            progression_order=1,
        )
        assert keyset.keyset_name == "Home Row"

    def test_rejects_whitespace_only_name(self, keyboard_id: str) -> None:
        """Test objective: Verify whitespace-only name is rejected after stripping."""
        with pytest.raises(ValidationError, match="1..100 characters"):
            Keyset(keyboard_id=keyboard_id, keyset_name="   ", progression_order=1)

    def test_rejects_non_string_name(self, keyboard_id: str) -> None:
        """Test objective: Verify non-string name is rejected."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=keyboard_id, keyset_name=123, progression_order=1)  # type: ignore[arg-type]


class TestProgressionOrderValidation:
    """Test progression_order validation: positive integer >= 1."""

    def test_accepts_positive_integers(self, keyboard_id: str) -> None:
        """Test objective: Verify positive integers are accepted."""
        ks1 = Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order=1)
        assert ks1.progression_order == 1
        ks2 = Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order=999)
        assert ks2.progression_order == 999

    def test_rejects_zero(self, keyboard_id: str) -> None:
        """Test objective: Verify progression_order=0 is rejected."""
        with pytest.raises(ValidationError, match=">= 1"):
            Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order=0)

    def test_rejects_negative(self, keyboard_id: str) -> None:
        """Test objective: Verify negative progression_order is rejected."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order=-1)

    def test_rejects_boolean(self, keyboard_id: str) -> None:
        """Test objective: Verify boolean is rejected (bool is subclass of int)."""
        with pytest.raises(ValidationError, match="positive integer"):
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="T",
                progression_order=True,  # type: ignore[arg-type]
            )

    def test_rejects_non_integer_types(self, keyboard_id: str) -> None:
        """Test objective: Verify float, non-numeric string, None are rejected."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order=1.5)
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order="abc")  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=keyboard_id, keyset_name="T", progression_order=None)  # type: ignore[arg-type]


class TestKeyboardIdValidation:
    """Test keyboard_id validation: required, non-empty string."""

    def test_rejects_missing_keyboard_id(self) -> None:
        """Test objective: Verify keyboard_id is required."""
        with pytest.raises(ValidationError):
            Keyset(keyset_name="T", progression_order=1)  # type: ignore[call-arg]

    def test_rejects_empty_keyboard_id(self) -> None:
        """Test objective: Verify empty string keyboard_id is rejected."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id="", keyset_name="T", progression_order=1)

    def test_rejects_whitespace_only_keyboard_id(self) -> None:
        """Test objective: Verify whitespace-only keyboard_id is rejected."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id="   ", keyset_name="T", progression_order=1)

    def test_rejects_non_string_keyboard_id(self) -> None:
        """Test objective: Verify non-string keyboard_id is rejected."""
        with pytest.raises(ValidationError):
            Keyset(keyboard_id=123, keyset_name="T", progression_order=1)  # type: ignore[arg-type]


class TestKeysetIdValidation:
    """Test keyset_id rejects invalid values."""

    def test_rejects_empty_string_keyset_id(self, keyboard_id: str) -> None:
        """Test objective: Verify empty-string keyset_id is rejected."""
        with pytest.raises(ValidationError):
            Keyset(
                keyboard_id=keyboard_id,
                keyset_name="T",
                progression_order=1,
                keyset_id="",
            )


# ============================================================================
# STATE TRACKING — in_db / is_dirty
# ============================================================================


class TestKeysetInDbFlag:
    """Test in_db state tracking (AC-12)."""

    def test_defaults_to_false(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify new keysets default to in_db=False."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.in_db is False

    def test_can_be_set_true(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify in_db=True at construction."""
        keyset = Keyset(**{**valid_keyset_data, "in_db": True})
        assert keyset.in_db is True

    def test_can_be_mutated_without_marking_dirty(
        self, sample_keyset: Keyset
    ) -> None:
        """Test objective: Verify changing in_db does NOT mark is_dirty."""
        sample_keyset.in_db = True
        assert sample_keyset.is_dirty is False


class TestKeysetIsDirtyFlag:
    """Test is_dirty auto-tracking (AC-13)."""

    def test_defaults_to_false(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify new keysets default to is_dirty=False."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.is_dirty is False

    def test_name_change_marks_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify changing keyset_name sets is_dirty=True."""
        sample_keyset.keyset_name = "New Name"
        assert sample_keyset.is_dirty is True

    def test_order_change_marks_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify changing progression_order sets is_dirty=True."""
        sample_keyset.progression_order = 5
        assert sample_keyset.is_dirty is True

    def test_keys_change_marks_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify replacing keys list sets is_dirty=True."""
        sample_keyset.keys = [KeysetKey(key_char="a", is_new_key=False)]
        assert sample_keyset.is_dirty is True

    def test_keyset_id_change_does_not_mark_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify changing keyset_id does NOT set is_dirty."""
        sample_keyset.keyset_id = str(uuid.uuid4())
        assert sample_keyset.is_dirty is False

    def test_keyboard_id_change_does_not_mark_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify changing keyboard_id does NOT set is_dirty."""
        sample_keyset.keyboard_id = str(uuid.uuid4())
        assert sample_keyset.is_dirty is False

    def test_in_db_change_does_not_mark_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify changing in_db does NOT set is_dirty."""
        sample_keyset.in_db = True
        assert sample_keyset.is_dirty is False

    def test_setting_is_dirty_itself_no_recursion(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify setting is_dirty to False works without recursion."""
        sample_keyset.keyset_name = "Changed"
        assert sample_keyset.is_dirty is True
        sample_keyset.is_dirty = False
        assert sample_keyset.is_dirty is False

    def test_can_be_reset_after_save(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify is_dirty can be cleared (simulating save)."""
        sample_keyset.keyset_name = "Edited"
        assert sample_keyset.is_dirty is True
        sample_keyset.is_dirty = False
        sample_keyset.in_db = True
        assert sample_keyset.is_dirty is False
        assert sample_keyset.in_db is True


# ============================================================================
# DOMAIN HELPERS — add_key, remove_key, has_key, get_keys_sorted
# ============================================================================


class TestKeysetAddKey:
    """Test Keyset.add_key() method (keyword-only args)."""

    def test_add_key_returns_keyset_key(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify add_key returns a KeysetKey with correct fields."""
        key = sample_keyset.add_key(key_char="a", is_new_key=True)
        assert isinstance(key, KeysetKey)
        assert key.key_char == "a"
        assert key.is_new_key is True
        assert key.keyset_id == sample_keyset.keyset_id

    def test_add_key_appends_to_keys_list(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify added key appears in keyset.keys."""
        sample_keyset.add_key(key_char="x", is_new_key=False)
        assert len(sample_keyset.keys) == 1
        assert sample_keyset.keys[0].key_char == "x"

    def test_add_key_marks_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify add_key sets is_dirty=True."""
        assert sample_keyset.is_dirty is False
        sample_keyset.add_key(key_char="a", is_new_key=True)
        assert sample_keyset.is_dirty is True

    def test_add_key_rejects_duplicate_within_keyset(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify adding same key_char twice raises ValueError."""
        sample_keyset.add_key(key_char="a", is_new_key=True)
        with pytest.raises(ValueError, match="already exists"):
            sample_keyset.add_key(key_char="a", is_new_key=False)

    def test_add_key_is_keyword_only(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify add_key requires keyword arguments."""
        with pytest.raises(TypeError):
            sample_keyset.add_key("a", True)  # type: ignore[misc]


class TestKeysetRemoveKey:
    """Test Keyset.remove_key() method (keyword-only args)."""

    def test_remove_existing_key_returns_true(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify removing an existing key returns True."""
        sample_keyset.add_key(key_char="a", is_new_key=True)
        sample_keyset.is_dirty = False
        assert sample_keyset.remove_key(key_char="a") is True

    def test_remove_nonexistent_key_returns_false(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify removing a non-existent key returns False."""
        assert sample_keyset.remove_key(key_char="z") is False

    def test_remove_key_marks_dirty(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify remove_key sets is_dirty=True on success."""
        sample_keyset.add_key(key_char="a", is_new_key=True)
        sample_keyset.is_dirty = False
        sample_keyset.remove_key(key_char="a")
        assert sample_keyset.is_dirty is True

    def test_remove_key_does_not_mark_dirty_on_miss(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify remove_key does NOT mark dirty when key not found."""
        assert sample_keyset.remove_key(key_char="z") is False
        assert sample_keyset.is_dirty is False

    def test_remove_key_is_keyword_only(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify remove_key requires keyword arguments."""
        with pytest.raises(TypeError):
            sample_keyset.remove_key("a")  # type: ignore[misc]


class TestKeysetHasKey:
    """Test Keyset.has_key() method (keyword-only args per spec)."""

    def test_has_key_returns_true_when_present(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify has_key returns True for existing key."""
        sample_keyset.add_key(key_char="a", is_new_key=True)
        assert sample_keyset.has_key(key_char="a") is True

    def test_has_key_returns_false_when_absent(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify has_key returns False for non-existent key."""
        assert sample_keyset.has_key(key_char="z") is False

    def test_has_key_is_keyword_only(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify has_key requires keyword argument."""
        with pytest.raises(TypeError):
            sample_keyset.has_key("a")  # type: ignore[misc]


class TestKeysetGetKeysSorted:
    """Test Keyset.get_keys_sorted() method."""

    def test_returns_keys_alphabetically(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify keys are returned sorted alphabetically by key_char."""
        sample_keyset.add_key(key_char="c", is_new_key=True)
        sample_keyset.add_key(key_char="a", is_new_key=True)
        sample_keyset.add_key(key_char="b", is_new_key=True)
        sorted_keys = sample_keyset.get_keys_sorted()
        chars = [k.key_char for k in sorted_keys]
        assert chars == ["a", "b", "c"]

    def test_returns_empty_list_when_no_keys(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify empty list for keyset with no keys."""
        assert sample_keyset.get_keys_sorted() == []

    def test_case_insensitive_sorting(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify sorting is case-insensitive."""
        sample_keyset.add_key(key_char="B", is_new_key=True)
        sample_keyset.add_key(key_char="a", is_new_key=True)
        sorted_keys = sample_keyset.get_keys_sorted()
        chars = [k.key_char for k in sorted_keys]
        assert chars == ["a", "B"]


# ============================================================================
# KEYSET WITH KEYS AT CONSTRUCTION
# ============================================================================


class TestKeysetWithKeys:
    """Test creating Keyset with pre-populated keys."""

    def test_keyset_accepts_key_list(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify keyset can be constructed with keys."""
        keys = [
            KeysetKey(key_char="a", is_new_key=False),
            KeysetKey(key_char="b", is_new_key=True),
        ]
        data = {**valid_keyset_data, "keys": keys}
        keyset = Keyset(**data)
        assert len(keyset.keys) == 2
        assert keyset.keys[0].key_char == "a"
        assert keyset.keys[1].key_char == "b"

    def test_keys_default_to_empty_list(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify keys defaults to empty list."""
        keyset = Keyset(**valid_keyset_data)
        assert keyset.keys == []


# ============================================================================
# SERIALISATION ROUND-TRIP
# ============================================================================


class TestKeysetSerialization:
    """Test to_dict / from_dict serialization."""

    def test_to_dict_includes_all_fields(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify to_dict returns complete field set."""
        d = sample_keyset.to_dict()
        expected_keys = {
            "keyset_id", "keyboard_id", "keyset_name",
            "progression_order", "keys", "in_db", "is_dirty",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_with_nested_keys(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify nested keys are serialized."""
        sample_keyset.add_key(key_char="a", is_new_key=False)
        d = sample_keyset.to_dict()
        assert len(d["keys"]) == 1
        assert d["keys"][0]["key_char"] == "a"

    def test_from_dict_restores_entity(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify from_dict reconstructs equivalent entity."""
        original = Keyset(**valid_keyset_data)
        original.add_key(key_char="x", is_new_key=True)
        restored = Keyset.from_dict(original.to_dict())
        assert restored.keyset_id == original.keyset_id
        assert restored.keyboard_id == original.keyboard_id
        assert restored.keyset_name == original.keyset_name
        assert restored.progression_order == original.progression_order
        assert len(restored.keys) == 1
        assert restored.keys[0].key_char == "x"

    def test_from_dict_with_nested_dict_keys(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test objective: Verify from_dict handles keys as raw dictionaries."""
        key_data = {"key_char": "a", "is_new_key": False}
        data = {**valid_keyset_data, "keys": [key_data]}
        keyset = Keyset.from_dict(data)
        assert len(keyset.keys) == 1
        assert isinstance(keyset.keys[0], KeysetKey)

    def test_roundtrip_preserves_non_ascii_key(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test objective: Verify roundtrip preserves non-ASCII key characters."""
        keyset = Keyset(**valid_keyset_data)
        keyset.add_key(key_char="é", is_new_key=True)
        restored = Keyset.from_dict(keyset.to_dict())
        assert restored.keys[0].key_char == "é"


# ============================================================================
# VALIDATE ON ASSIGNMENT
# ============================================================================


class TestKeysetAssignmentValidation:
    """Test Pydantic validate_assignment catches invalid mutations."""

    def test_rejects_empty_name_on_assignment(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify empty keyset_name on assignment raises."""
        with pytest.raises(ValidationError):
            sample_keyset.keyset_name = ""

    def test_rejects_long_name_on_assignment(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify >100 char keyset_name on assignment raises."""
        with pytest.raises(ValidationError):
            sample_keyset.keyset_name = "A" * 101

    def test_rejects_zero_order_on_assignment(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify progression_order=0 on assignment raises."""
        with pytest.raises(ValidationError):
            sample_keyset.progression_order = 0

    def test_rejects_empty_keyset_id_on_assignment(self, sample_keyset: Keyset) -> None:
        """Test objective: Verify empty keyset_id on assignment raises."""
        with pytest.raises(ValidationError):
            sample_keyset.keyset_id = ""


# ============================================================================
# EXTRA FIELDS REJECTED
# ============================================================================


class TestKeysetExtraFields:
    """Test that extra fields are rejected (model_config extra=forbid)."""

    def test_rejects_unknown_fields(self, valid_keyset_data: Dict[str, Any]) -> None:
        """Test objective: Verify construction with unknown fields raises."""
        data = {**valid_keyset_data, "extra_field": "value"}
        with pytest.raises(ValidationError, match="extra"):
            Keyset(**data)

    def test_rejects_extra_fields_in_nested_keys(
        self, valid_keyset_data: Dict[str, Any]
    ) -> None:
        """Test objective: Verify nested keys with unknown fields raise."""
        bad_key = {"key_char": "a", "is_new_key": False, "extra": "x"}
        data = {**valid_keyset_data, "keys": [bad_key]}
        with pytest.raises(ValidationError):
            Keyset.from_dict(data)


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
