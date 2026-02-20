"""Tests for KeysetKey entity.

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

from entities.keyset_key import KeysetKey

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def valid_key_data() -> Dict[str, Any]:
    """Provide minimal valid data for KeysetKey construction."""
    return {
        "key_char": "a",
        "is_new_key": False,
    }


@pytest.fixture
def sample_key() -> KeysetKey:
    """Provide a ready-made KeysetKey instance."""
    return KeysetKey(key_char="a", is_new_key=False)


# ============================================================================
# UUID AUTO-GENERATION
# ============================================================================


class TestKeysetKeyUuidGeneration:
    """Test auto-generation and acceptance of UUIDs."""

    def test_auto_generates_uuid_when_not_provided(self) -> None:
        """Test objective: Verify key_id is auto-generated as valid UUID when omitted."""
        key = KeysetKey(key_char="a", is_new_key=False)
        assert key.key_id is not None
        uuid.UUID(key.key_id)  # raises if not valid UUID

    def test_each_instance_gets_unique_uuid(self) -> None:
        """Test objective: Verify two instances get distinct auto-generated UUIDs."""
        k1 = KeysetKey(key_char="a", is_new_key=False)
        k2 = KeysetKey(key_char="b", is_new_key=False)
        assert k1.key_id != k2.key_id

    def test_accepts_provided_uuid(self) -> None:
        """Test objective: Verify an explicit key_id is preserved."""
        provided = str(uuid.uuid4())
        key = KeysetKey(key_id=provided, key_char="a", is_new_key=False)
        assert key.key_id == provided

    def test_auto_generates_uuid_when_none_explicit(self) -> None:
        """Test objective: Verify key_id=None triggers auto-generation."""
        key = KeysetKey(key_id=None, key_char="x", is_new_key=False)
        assert key.key_id is not None
        uuid.UUID(key.key_id)

    def test_rejects_empty_string_key_id(self) -> None:
        """Test objective: Verify empty-string key_id is rejected."""
        with pytest.raises(ValidationError, match="non-empty"):
            KeysetKey(key_id="", key_char="a", is_new_key=False)

    def test_rejects_whitespace_only_key_id(self) -> None:
        """Test objective: Verify whitespace-only key_id is rejected."""
        with pytest.raises(ValidationError, match="non-empty"):
            KeysetKey(key_id="   ", key_char="a", is_new_key=False)


# ============================================================================
# key_char VALIDATION — SINGLE UNICODE CODE POINT
# ============================================================================


class TestKeyCharValidation:
    """Test key_char must be exactly one Unicode code point."""

    @pytest.mark.parametrize(
        "char",
        ["a", "Z", "0", "!", " ", "\t"],
        ids=["lowercase", "uppercase", "digit", "punctuation", "space", "tab"],
    )
    def test_accepts_single_ascii_characters(self, char: str) -> None:
        """Test objective: Verify common ASCII single characters are accepted."""
        key = KeysetKey(key_char=char, is_new_key=False)
        assert key.key_char == char

    @pytest.mark.parametrize(
        "char",
        ["é", "ñ", "ü", "ç", "ö"],
        ids=["e-acute", "n-tilde", "u-umlaut", "c-cedilla", "o-umlaut"],
    )
    def test_accepts_non_ascii_letters(self, char: str) -> None:
        """Test objective: Verify non-ASCII letters (accented) are accepted."""
        key = KeysetKey(key_char=char, is_new_key=False)
        assert key.key_char == char

    @pytest.mark.parametrize(
        "char",
        ["中", "日", "한", "本", "語"],
        ids=["zhong", "ri", "han", "ben", "go"],
    )
    def test_accepts_cjk_characters(self, char: str) -> None:
        """Test objective: Verify CJK characters are accepted."""
        key = KeysetKey(key_char=char, is_new_key=False)
        assert key.key_char == char

    @pytest.mark.parametrize(
        "char",
        ["😀", "🎉", "🔥", "💻", "🚀"],
        ids=["grin", "party", "fire", "laptop", "rocket"],
    )
    def test_accepts_emoji_characters(self, char: str) -> None:
        """Test objective: Verify emoji characters are accepted."""
        key = KeysetKey(key_char=char, is_new_key=False)
        assert key.key_char == char

    @pytest.mark.parametrize(
        "char",
        ["!", "?", "@", "#", "$", "%", "&", "*", "(", ")", "-", "+", "="],
        ids=["bang", "question", "at", "hash", "dollar", "percent", "amp", "star",
             "lparen", "rparen", "dash", "plus", "equals"],
    )
    def test_accepts_punctuation_and_symbols(self, char: str) -> None:
        """Test objective: Verify punctuation and symbol characters are accepted."""
        key = KeysetKey(key_char=char, is_new_key=False)
        assert key.key_char == char

    def test_rejects_empty_string(self) -> None:
        """Test objective: Verify empty string is rejected."""
        with pytest.raises(ValidationError, match="exactly one character"):
            KeysetKey(key_char="", is_new_key=False)

    def test_rejects_multi_character_string(self) -> None:
        """Test objective: Verify multi-character string is rejected."""
        with pytest.raises(ValidationError, match="exactly one character"):
            KeysetKey(key_char="ab", is_new_key=False)

    def test_rejects_non_string_type(self) -> None:
        """Test objective: Verify non-string types (int, None) are rejected."""
        with pytest.raises(ValidationError):
            KeysetKey(key_char=123, is_new_key=False)  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            KeysetKey(key_char=None, is_new_key=False)  # type: ignore[arg-type]


# ============================================================================
# keyset_id VALIDATION
# ============================================================================


class TestKeysetIdValidation:
    """Test keyset_id is optional but validated when provided."""

    def test_keyset_id_defaults_to_none(self) -> None:
        """Test objective: Verify keyset_id is None when not provided."""
        key = KeysetKey(key_char="a", is_new_key=False)
        assert key.keyset_id is None

    def test_accepts_valid_keyset_id(self) -> None:
        """Test objective: Verify a valid keyset_id string is accepted."""
        ks_id = str(uuid.uuid4())
        key = KeysetKey(key_char="a", is_new_key=False, keyset_id=ks_id)
        assert key.keyset_id == ks_id

    def test_rejects_whitespace_only_keyset_id(self) -> None:
        """Test objective: Verify whitespace-only keyset_id is rejected."""
        with pytest.raises(ValidationError, match="non-empty"):
            KeysetKey(key_char="a", is_new_key=False, keyset_id="   ")

    def test_rejects_empty_string_keyset_id(self) -> None:
        """Test objective: Verify empty-string keyset_id is rejected."""
        with pytest.raises(ValidationError, match="non-empty"):
            KeysetKey(key_char="a", is_new_key=False, keyset_id="")


# ============================================================================
# STATE TRACKING — in_db
# ============================================================================


class TestKeysetKeyInDbFlag:
    """Test in_db state tracking flag."""

    def test_in_db_defaults_to_false(self) -> None:
        """Test objective: Verify new keys default to in_db=False (AC-12)."""
        key = KeysetKey(key_char="a", is_new_key=False)
        assert key.in_db is False

    def test_in_db_can_be_set_true_at_construction(self) -> None:
        """Test objective: Verify in_db=True can be set at construction."""
        key = KeysetKey(key_char="a", is_new_key=False, in_db=True)
        assert key.in_db is True

    def test_in_db_can_be_mutated(self) -> None:
        """Test objective: Verify in_db can be changed after construction."""
        key = KeysetKey(key_char="a", is_new_key=False)
        assert key.in_db is False
        key.in_db = True
        assert key.in_db is True


# ============================================================================
# SERIALISATION ROUND-TRIP
# ============================================================================


class TestKeysetKeySerialization:
    """Test to_dict / from_dict serialization."""

    def test_to_dict_includes_all_fields(self, sample_key: KeysetKey) -> None:
        """Test objective: Verify to_dict returns complete field set."""
        d = sample_key.to_dict()
        assert set(d.keys()) == {"key_id", "keyset_id", "key_char", "is_new_key", "in_db"}

    def test_from_dict_restores_entity(self) -> None:
        """Test objective: Verify from_dict reconstructs equivalent entity."""
        original = KeysetKey(key_char="z", is_new_key=True, keyset_id="ks-1")
        restored = KeysetKey.from_dict(original.to_dict())
        assert restored.key_id == original.key_id
        assert restored.keyset_id == original.keyset_id
        assert restored.key_char == original.key_char
        assert restored.is_new_key == original.is_new_key
        assert restored.in_db == original.in_db

    def test_roundtrip_preserves_non_ascii(self) -> None:
        """Test objective: Verify roundtrip preserves non-ASCII characters."""
        key = KeysetKey(key_char="é", is_new_key=True)
        restored = KeysetKey.from_dict(key.to_dict())
        assert restored.key_char == "é"

    def test_roundtrip_preserves_emoji(self) -> None:
        """Test objective: Verify roundtrip preserves emoji characters."""
        key = KeysetKey(key_char="🔥", is_new_key=False)
        restored = KeysetKey.from_dict(key.to_dict())
        assert restored.key_char == "🔥"


# ============================================================================
# VALIDATE ON ASSIGNMENT
# ============================================================================


class TestKeysetKeyAssignmentValidation:
    """Test that Pydantic validate_assignment catches invalid mutations."""

    def test_can_reassign_key_char_to_valid_character(self, sample_key: KeysetKey) -> None:
        """Test objective: Verify key_char can be updated to another valid char."""
        sample_key.key_char = "b"
        assert sample_key.key_char == "b"

    def test_rejects_multi_char_on_assignment(self, sample_key: KeysetKey) -> None:
        """Test objective: Verify assignment rejects multi-character string."""
        with pytest.raises(ValidationError, match="exactly one character"):
            sample_key.key_char = "ab"

    def test_rejects_empty_string_on_assignment(self, sample_key: KeysetKey) -> None:
        """Test objective: Verify assignment rejects empty string."""
        with pytest.raises(ValidationError, match="exactly one character"):
            sample_key.key_char = ""


# ============================================================================
# EXTRA FIELDS REJECTED
# ============================================================================


class TestKeysetKeyExtraFields:
    """Test that extra fields are rejected (model_config extra=forbid)."""

    def test_rejects_unknown_fields(self) -> None:
        """Test objective: Verify construction with unknown fields raises."""
        with pytest.raises(ValidationError, match="extra"):
            KeysetKey(key_char="a", is_new_key=False, unknown_field="x")  # type: ignore[call-arg]


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
