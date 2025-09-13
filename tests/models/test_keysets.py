"""Tests for Keyset models and KeysetManager (DB-independent history logic).

Test objective:
- Verify keyset and keyset_keys persistence
- Verify SCD-2 history close-update insertions
- Enforce unique progression per keyboard
- Verify promote/set order swaps without uniqueness violations
"""
from __future__ import annotations

from typing import cast

import pytest

from db.database_manager import DatabaseManager
from models.keyset import Keyset, KeysetKey
from models.keyset_manager import KeysetManager


@pytest.mark.usefixtures("db_with_tables", "test_keyboard")
class TestKeysets:

    def test_create_keyset_and_keys_persist_and_history(self, db_with_tables: DatabaseManager, test_keyboard) -> None:
        """Test objective: Creating a keyset persists base rows and writes history + keys."""
        db = db_with_tables
        kb_id = cast(str, str(test_keyboard.keyboard_id))

        mgr = KeysetManager(db)
        ks = Keyset(
            keyboard_id=kb_id,
            keyset_name="Home Keys",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=True),
                KeysetKey(key_char="s", is_new_key=True),
            ],
        )
        kid = mgr.create_keyset(ks)
        assert isinstance(kid, str) and len(kid) > 0

        # Base table
        rows = db.fetchall(
            "SELECT keyset_id, keyboard_id, keyset_name, progression_order FROM keysets WHERE keyset_id = ?",
            (kid,),
        )
        assert rows and rows[0]["keyset_name"] == "Home Keys"

        # Keys
        krows = db.fetchall(
            "SELECT key_char, is_new_key FROM keyset_keys WHERE keyset_id = ? ORDER BY key_char",
            (kid,),
        )
        pairs = [(cast(str, r["key_char"]), cast(int, r["is_new_key"])) for r in krows]
        assert pairs == [("a", 1), ("s", 1)]

        # History exists
        hist = db.fetchall(
            "SELECT keyset_id, is_current, version_no FROM keysets_history WHERE keyset_id = ?",
            (kid,),
        )
        assert hist and cast(int, hist[0]["is_current"]) == 1 and cast(int, hist[0]["version_no"]) == 1

    def test_unique_progression_per_keyboard(self, db_with_tables: DatabaseManager, test_keyboard) -> None:
        """Test objective: progression_order must be unique per keyboard."""
        db = db_with_tables
        kb_id = cast(str, str(test_keyboard.keyboard_id))

        mgr = KeysetManager(db)
        ks1 = Keyset(keyboard_id=kb_id, keyset_name="K1", progression_order=1)
        mgr.create_keyset(ks1)

        ks2 = Keyset(keyboard_id=kb_id, keyset_name="K2", progression_order=1)
        with pytest.raises(ValueError):
            mgr.create_keyset(ks2)

    def test_promote_keyset_swaps_order(self, db_with_tables: DatabaseManager, test_keyboard) -> None:
        """Test objective: promoting a keyset swaps its progression with the previous order."""
        db = db_with_tables
        kb_id = cast(str, str(test_keyboard.keyboard_id))

        mgr = KeysetManager(db)
        k1 = Keyset(keyboard_id=kb_id, keyset_name="First", progression_order=1)
        k2 = Keyset(keyboard_id=kb_id, keyset_name="Second", progression_order=2)
        id1 = mgr.create_keyset(k1)
        id2 = mgr.create_keyset(k2)

        # Promote second -> should swap to 1 and first becomes 2
        ok = mgr.promote_keyset(kb_id, id2)
        assert ok is True
        rows = db.fetchall(
            "SELECT keyset_id, progression_order FROM keysets WHERE keyset_id IN (?, ?) ORDER BY progression_order",
            (id1, id2),
        )
        # After swap, id2 should be order 1
        orders = [(cast(str, r["keyset_id"]), cast(int, r["progression_order"])) for r in rows]
        assert orders[0][0] == id2 and orders[0][1] == 1
        assert orders[1][0] == id1 and orders[1][1] == 2

    def test_load_one_add_another_persist_both(self, db_with_tables: DatabaseManager, test_keyboard) -> None:
        """Test objective: After loading one keyset and adding another, save should persist both (count == 2).

        Preconditions:
        - An empty temp DB is initialized and seeded with a user and keyboard.
        Steps:
        - Create first keyset via create_keyset (persisted) for keyboard 'kb1'.
        - Instantiate a fresh manager and preload for 'kb1' (loads the one existing keyset).
        - Create a second keyset in memory (in_db=False).
        - Call save_all_keysets([loaded_keyset, new_keyset]).
        - Verify two rows exist for keyboard 'kb1'.
        """
        db = db_with_tables
        kb_id = cast(str, str(test_keyboard.keyboard_id))

        # Persist the first keyset
        mgr1 = KeysetManager(db)
        ks1 = Keyset(keyboard_id=kb_id, keyset_name="First", progression_order=1)
        mgr1.create_keyset(ks1)

        # New manager, load from DB
        mgr2 = KeysetManager(db)
        loaded_list = mgr2.preload_keysets_for_keyboard(kb_id)
        assert len(loaded_list) == 1
        loaded_ks = loaded_list[0]

        # Create second (in memory)
        ks2 = Keyset(keyboard_id=kb_id, keyset_name="Second", progression_order=2)

        # Persist both
        ok = mgr2.save_all_keysets([loaded_ks, ks2])
        assert ok is True

        # Verify count == 2 for kb1
        row = db.fetchone("SELECT COUNT(*) AS c FROM keysets WHERE keyboard_id = ?", (kb_id,))
        assert row is not None and cast(int, row["c"]) == 2

    def test_delete_keyset_cascade_and_history(self, db_with_tables: DatabaseManager, test_keyboard) -> None:
        """Test objective: Deleting a keyset removes base rows and writes proper history records.

        Assertions:
        - keysets and keyset_keys rows are deleted
        - history tables contain records including an action='D' row for both keyset and its keys
        """
        db = db_with_tables
        kb_id = cast(str, str(test_keyboard.keyboard_id))

        mgr = KeysetManager(db)
        ks = Keyset(
            keyboard_id=kb_id,
            keyset_name="ToDelete",
            progression_order=1,
            keys=[KeysetKey(key_char="x", is_new_key=True), KeysetKey(key_char="y", is_new_key=False)],
        )
        kid = mgr.create_keyset(ks)

        # Sanity
        assert db.fetchone("SELECT 1 AS x FROM keysets WHERE keyset_id = ?", (kid,)) is not None
        assert db.fetchone("SELECT 1 AS x FROM keyset_keys WHERE keyset_id = ?", (kid,)) is not None

        # Delete
        ok = mgr.delete_keyset(kid)
        assert ok is True

        # Base rows gone
        assert db.fetchone("SELECT 1 AS x FROM keysets WHERE keyset_id = ?", (kid,)) is None
        assert db.fetchone("SELECT 1 AS x FROM keyset_keys WHERE keyset_id = ?", (kid,)) is None

        # History rows exist with delete entries
        hks = db.fetchall(
            "SELECT action, is_current FROM keysets_history WHERE keyset_id = ? ORDER BY version_no",
            (kid,),
        )
        actions_keyset = [cast(str, r["action"]) for r in hks]
        assert "D" in actions_keyset

        hkeys = db.fetchall(
            "SELECT action FROM keyset_keys_history WHERE keyset_id = ?",
            (kid,),
        )
        actions_keys = [cast(str, r["action"]) for r in hkeys]
        assert "D" in actions_keys

    def test_delete_keyset_nonexistent_returns_false(self, db_with_tables: DatabaseManager) -> None:
        """Test objective: Deleting a non-existent keyset returns False and changes nothing."""
        mgr = KeysetManager(db_with_tables)
        assert mgr.delete_keyset("nonexistent") is False


if __name__ == "__main__":
    import sys as _sys

    _sys.exit(pytest.main([__file__]))
