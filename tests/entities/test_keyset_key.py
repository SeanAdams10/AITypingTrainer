"""Comprehensive tests for KeysetKey entity.

Tests cover creation, serialization, validation, UUID generation, state tracking,
and edge cases as specified in Requirements/Keyset_req.md.

This tests the ENTITIES LAYER ONLY - pure unit tests with no database or mocks.
"""

import uuid
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from entities.keyset_key import KeysetKey

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_key_data() -> Dict[str, Any]:
    """Fixture providing valid key data for testing."""
    return {
        "key_char": "a",
        "is_new_key": False,
    }


@pytest.fixture
def sample_key(valid_key_data: Dict[str, Any]) -> KeysetKey:
    """Fixture providing a sample KeysetKey instance."""
    return KeysetKey(**valid_key_data)


# ============================================================================
# KEYSETKEY CREATION TESTS
# ============================================================================


class TestKeysetKeyCreation:
    """Test KeysetKey entity creation and validation."""

    def test_key_creation_with_valid_data(self, valid_key_data: Dict[str, Any]) -> None:
        """Test creating a KeysetKey with valid data."""
        key = KeysetKey(**valid_key_data)
        assert key.key_char == valid_key_data["key_char"]
        assert key.is_new_key == valid_key_data["is_new_key"]
        assert key.in_db is False  # Default value

    def test_key_auto_generates_uuid(self, valid_key_data: Dict[str, Any]) -> None:
        """AC: UUID Generation - KeysetKey automatically generates UUID when not provided."""
        key = KeysetKey(**valid_key_data)
        assert key.key_id is not None
        assert isinstance(key.key_id, str)
        # Verify it's a valid UUID
        uuid.UUID(key.key_id)

    def test_key_accepts_provided_uuid(self, valid_key_data: Dict[str, Any]) -> None:
        """Test KeysetKey accepts a provided UUID."""
        provided_uuid = str(uuid.uuid4())
        data = {**valid_key_data, "key_id": provided_uuid}
        key = KeysetKey(**data)
        assert key.key_id == provided_uuid

    def test_key_keyset_id_optional(self, valid_key_data: Dict[str, Any]) -> None:
        """Test KeysetKey keyset_id can be None before persistence."""
        key = KeysetKey(**valid_key_data)
        assert key.keyset_id is None

    def test_key_accepts_keyset_id(self, valid_key_data: Dict[str, Any]) -> None:
        """Test KeysetKey accepts a keyset_id when provided."""
        keyset_id = str(uuid.uuid4())
        data = {**valid_key_data, "keyset_id": keyset_id}
        key = KeysetKey(**data)
        assert key.keyset_id == keyset_id


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestKeysetKeyValidation:
    """Test KeysetKey validation rules."""

    def test_key_char_must_be_single_character(self) -> None:
        """Test key_char must be exactly one Unicode character."""
        # Valid single characters - ASCII
        valid_chars = ["a", "Z", "1", "!", " ", "\t"]
        for char in valid_chars:
            key = KeysetKey(key_char=char, is_new_key=False)
            assert key.key_char == char

    def test_key_char_rejects_multiple_characters(self) -> None:
        """Test key_char rejects strings with multiple characters."""
        with pytest.raises(ValidationError) as exc_info:
            KeysetKey(key_char="ab", is_new_key=False)
        assert "exactly one character" in str(exc_info.value).lower()

    def test_key_char_rejects_empty_string(self) -> None:
        """Test key_char rejects empty string."""
        with pytest.raises(ValidationError) as exc_info:
            KeysetKey(key_char="", is_new_key=False)
        assert "exactly one character" in str(exc_info.value).lower()

    def test_key_char_supports_unicode_non_ascii_letters(self) -> None:
        """Test key_char supports non-ASCII letters."""
        unicode_letters = ["é", "ñ", "ü", "ç", "ö"]
        for char in unicode_letters:
            key = KeysetKey(key_char=char, is_new_key=False)
            assert key.key_char == char

    def test_key_char_supports_cjk_characters(self) -> None:
        """Test key_char supports CJK (Chinese, Japanese, Korean) characters."""
        cjk_chars = ["中", "日", "한", "本", "語"]
        for char in cjk_chars:
            key = KeysetKey(key_char=char, is_new_key=False)
            assert key.key_char == char

    def test_key_char_supports_emojis(self) -> None:
        """Test key_char supports emoji characters."""
        emojis = ["😀", "🎉", "🔥", "💻", "🚀"]
        for emoji in emojis:
            key = KeysetKey(key_char=emoji, is_new_key=False)
            assert key.key_char == emoji

    def test_key_char_supports_punctuation_and_symbols(self) -> None:
        """Test key_char supports punctuation and symbols."""
        symbols = ["!", "?", "@", "#", "$", "%", "&", "*", "(", ")", "-", "+", "="]
        for symbol in symbols:
            key = KeysetKey(key_char=symbol, is_new_key=False)
            assert key.key_char == symbol

    def test_key_char_must_be_string(self) -> None:
        """Test key_char must be a string."""
        with pytest.raises(ValidationError):
            KeysetKey(key_char=123, is_new_key=False)  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            KeysetKey(key_char=None, is_new_key=False)  # type: ignore[arg-type]


# ============================================================================
# STATE TRACKING TESTS
# ============================================================================


class TestKeysetKeyStateTracking:
    """Test KeysetKey database state tracking."""

    def test_key_in_db_defaults_to_false(self, valid_key_data: Dict[str, Any]) -> None:
        """AC: Database State Tracking - New keys created in UI marked with in_db=False."""
        key = KeysetKey(**valid_key_data)
        assert key.in_db is False

    def test_key_in_db_can_be_set_true(self, valid_key_data: Dict[str, Any]) -> None:
        """Test in_db can be set to True (after loading from DB)."""
        data = {**valid_key_data, "in_db": True}
        key = KeysetKey(**data)
        assert key.in_db is True

    def test_key_in_db_can_be_updated(self, sample_key: KeysetKey) -> None:
        """Test in_db flag can be updated after creation."""
        assert sample_key.in_db is False
        sample_key.in_db = True
        assert sample_key.in_db is True


# ============================================================================
# SERIALIZATION TESTS
# ============================================================================


class TestKeysetKeySerialization:
    """Test KeysetKey serialization methods."""

    def test_key_to_dict(self, sample_key: KeysetKey) -> None:
        """Test KeysetKey to_dict method."""
        result = sample_key.to_dict()
        assert isinstance(result, dict)
        assert result["key_char"] == sample_key.key_char
        assert result["is_new_key"] == sample_key.is_new_key
        assert result["in_db"] == sample_key.in_db
        assert result["key_id"] == sample_key.key_id

    def test_key_from_dict(self, valid_key_data: Dict[str, Any]) -> None:
        """Test KeysetKey from_dict method."""
        key_id = str(uuid.uuid4())
        data = {**valid_key_data, "key_id": key_id}
        key = KeysetKey.from_dict(data)
        assert key.key_char == data["key_char"]
        assert key.is_new_key == data["is_new_key"]
        assert key.key_id == key_id

    def test_key_roundtrip_serialization(self, sample_key: KeysetKey) -> None:
        """Test to_dict -> from_dict roundtrip preserves all data."""
        dict_data = sample_key.to_dict()
        restored = KeysetKey.from_dict(dict_data)
        assert restored.key_id == sample_key.key_id
        assert restored.keyset_id == sample_key.keyset_id
        assert restored.key_char == sample_key.key_char
        assert restored.is_new_key == sample_key.is_new_key
        assert restored.in_db == sample_key.in_db


# ============================================================================
# EDGE CASES AND ERROR CONDITIONS
# ============================================================================


class TestKeysetKeyEdgeCases:
    """Test edge cases and error conditions."""

    def test_keysetkey_forbids_extra_fields(self, valid_key_data: Dict[str, Any]) -> None:
        """Test KeysetKey forbids extra fields."""
        data = {**valid_key_data, "extra_field": "value"}
        with pytest.raises(ValidationError) as exc_info:
            KeysetKey(**data)
        assert "extra" in str(exc_info.value).lower()

    def test_keysetkey_handles_none_key_id(self, valid_key_data: Dict[str, Any]) -> None:
        """Test KeysetKey handles None key_id gracefully."""
        data = {**valid_key_data, "key_id": None}
        key = KeysetKey(**data)
        # Should auto-generate UUID
        assert key.key_id is not None
        uuid.UUID(key.key_id)

    def test_keysetkey_validates_on_assignment(self, sample_key: KeysetKey) -> None:
        """Test KeysetKey validates fields on assignment (validate_assignment=True)."""
        # Valid assignment
        sample_key.key_char = "b"
        assert sample_key.key_char == "b"

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            sample_key.key_char = "ab"  # Multiple characters

        with pytest.raises(ValidationError):
            sample_key.key_char = ""  # Empty string
