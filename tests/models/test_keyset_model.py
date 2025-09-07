"""Model-focused tests for Keyset and KeysetKey.

Covers:
- UUID auto-generation for Keyset and KeysetKey
- Validation constraints (name length, progression_order, key_char length)
- is_dirty lifecycle on the Keyset model
"""
from __future__ import annotations

import re
from typing import List

import pytest

from models.keyset import Keyset, KeysetKey


class TestKeysetModelBasics:
    def test_keyset_generates_uuid_when_not_provided(self) -> None:
        ks = Keyset(keyboard_id="kb1", keyset_name="Home Keys", progression_order=1)
        assert isinstance(ks.keyset_id, str) and len(ks.keyset_id) > 0
        # loose UUID-ish shape: 8-4-4-4-12 (not strictly enforced by model)
        assert re.match(r"^[0-9a-fA-F-]{10,}$", ks.keyset_id) is not None

    def test_key_validation_single_character(self) -> None:
        KeysetKey(key_char="a")  # should not raise
        with pytest.raises(ValueError):
            KeysetKey(key_char="")
        with pytest.raises(ValueError):
            KeysetKey(key_char="ab")

    def test_keyset_name_bounds(self) -> None:
        Keyset(keyboard_id="kb1", keyset_name="A", progression_order=1)  # ok
        with pytest.raises(ValueError):
            Keyset(keyboard_id="kb1", keyset_name="", progression_order=1)
        with pytest.raises(ValueError):
            Keyset(keyboard_id="kb1", keyset_name=" ", progression_order=1)
        with pytest.raises(ValueError):
            Keyset(keyboard_id="kb1", keyset_name="x" * 101, progression_order=1)

    def test_progression_order_must_be_positive_int(self) -> None:
        Keyset(keyboard_id="kb1", keyset_name="OK", progression_order=1)  # ok
        with pytest.raises(ValueError):
            Keyset(keyboard_id="kb1", keyset_name="OK", progression_order=0)
        with pytest.raises(ValueError):
            Keyset(keyboard_id="kb1", keyset_name="OK", progression_order=-1)

    def test_is_dirty_false_on_init_true_after_mutation(self) -> None:
        ks = Keyset(keyboard_id="kb1", keyset_name="Home Keys", progression_order=1)
        # Freshly constructed model defaults to not dirty (no DB yet but clean state)
        assert ks.is_dirty is False
        # Change business field -> sets dirty
        ks.keyset_name = "Edited"
        assert ks.is_dirty is True

    def test_is_dirty_sets_true_when_keys_changed(self) -> None:
        ks = Keyset(keyboard_id="kb1", keyset_name="Home Keys", progression_order=1)
        assert ks.is_dirty is False
        # Assigning the list itself (not in-place) should flip dirty
        ks.keys = [KeysetKey(key_char="a", is_new_key=True)]
        assert ks.is_dirty is True

    def test_is_dirty_reset_expected_by_manager(self) -> None:
        # Simulate manager behavior that clears dirty after persistence
        ks = Keyset(keyboard_id="kb1", keyset_name="Home Keys", progression_order=1)
        ks.keyset_name = "Changed"
        assert ks.is_dirty is True
        # manager would clear this after successful save
        ks.is_dirty = False
        assert ks.is_dirty is False


class TestKeysetKeyModelBasics:
    def test_keysetkey_generates_uuid_when_not_provided(self) -> None:
        k = KeysetKey(key_char="x")
        assert isinstance(k.key_id, str) and len(k.key_id) > 0

    def test_keysetkey_accepts_optional_keyset_id(self) -> None:
        k = KeysetKey(key_char="y")
        assert k.keyset_id is None
        # When provided, must be non-empty string
        with pytest.raises(ValueError):
            KeysetKey(key_char="z", keyset_id=" ")
