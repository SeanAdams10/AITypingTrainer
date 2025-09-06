"""UI tests for KeysetsDialog selection behavior and edit flow.

Covers:
- AC-UI-1: Selection-dependent buttons
- AC-UI-2: RHS refresh on selection
- AC-UI-3: Edit applies to selected keyset and stages changes
"""
from __future__ import annotations

from typing import List, Tuple

import pytest
from PySide6 import QtWidgets

from db.database_manager import DatabaseManager
from desktop_ui.keysets_dialog import KeysetsDialog
from models.keyset import Keyset, KeysetKey
from models.keyset_manager import KeysetManager


def _seed_user_and_keyboard(db: DatabaseManager, user_id: str, keyboard_id: str) -> None:
    db.execute(
        "INSERT INTO users(user_id, first_name, surname, email_address) VALUES(?, ?, ?, ?)",
        (user_id, "Test", "User", f"{user_id}@example.com"),
    )
    db.execute(
        "INSERT INTO keyboards(keyboard_id, user_id, keyboard_name, target_ms_per_keystroke) VALUES(?, ?, ?, ?)",
        (keyboard_id, user_id, "KB-UI", 200),
    )


@pytest.fixture()
def keyboard_id(db_manager: DatabaseManager) -> str:
    user_id = "ui_user_1"
    kb_id = "ui_kb_1"
    _seed_user_and_keyboard(db_manager, user_id, kb_id)
    return kb_id


def _make_dialog(db: DatabaseManager, kb_id: str) -> KeysetsDialog:
    dlg = KeysetsDialog(db, kb_id)
    # Avoid actually showing a window for headless tests
    dlg.setAttribute(QtWidgets.Qt.WA_DontShowOnScreen, True)  # type: ignore[attr-defined]
    return dlg


def _list_keys(widget: QtWidgets.QListWidget) -> List[Tuple[str, bool]]:
    out: List[Tuple[str, bool]] = []
    for i in range(widget.count()):
        _, key_char, is_new = widget.item(i).data(QtWidgets.Qt.ItemDataRole.UserRole)
        out.append((str(key_char), bool(is_new)))
    return out


def test_selection_dependent_buttons(app, db_manager: DatabaseManager, keyboard_id: str) -> None:
    """AC-UI-1: Buttons disabled with no selection; enabled when selected."""
    mgr = KeysetManager(db_manager)
    ks = Keyset(keyboard_id=keyboard_id, keyset_name="K1", progression_order=1)
    mgr.create_keyset(ks)

    dlg = _make_dialog(db_manager, keyboard_id)

    # Start with first row selected by default per implementation
    assert dlg.keysets_list.currentItem() is not None
    assert dlg.delete_btn.isEnabled() is True
    assert dlg.edit_details_btn.isEnabled() is True

    # Clear selection -> buttons disabled
    dlg.keysets_list.clearSelection()
    # Manually trigger selection changed handler to update RHS and buttons
    dlg._on_keyset_selected(-1)
    assert dlg.keysets_list.currentItem() is None
    assert dlg.delete_btn.isEnabled() is False
    assert dlg.edit_details_btn.isEnabled() is False

    # Select first row again -> enabled
    if dlg.keysets_list.count() > 0:
        dlg.keysets_list.setCurrentRow(0)
        assert dlg.delete_btn.isEnabled() is True
        assert dlg.edit_details_btn.isEnabled() is True


def test_rhs_refresh_on_selection(app, db_manager: DatabaseManager, keyboard_id: str) -> None:
    """AC-UI-2: Ensure right pane refreshes with selected keyset details and keys."""
    mgr = KeysetManager(db_manager)
    ks1 = Keyset(
        keyboard_id=keyboard_id,
        keyset_name="K1",
        progression_order=1,
        keys=[KeysetKey(key_char="a", is_new_key=True), KeysetKey(key_char="c", is_new_key=False)],
    )
    ks2 = Keyset(
        keyboard_id=keyboard_id,
        keyset_name="K2",
        progression_order=2,
        keys=[KeysetKey(key_char="b", is_new_key=True)],
    )
    mgr.create_keyset(ks1)
    mgr.create_keyset(ks2)

    dlg = _make_dialog(db_manager, keyboard_id)

    # Select first
    dlg.keysets_list.setCurrentRow(0)
    assert dlg.name_edit.text() == "K1"
    assert int(dlg.order_spin.value()) == 1
    # Keys should be alphabetical: a, c
    assert _list_keys(dlg.keys_list) == [("a", True), ("c", False)]

    # Select second
    dlg.keysets_list.setCurrentRow(1)
    assert dlg.name_edit.text() == "K2"
    assert int(dlg.order_spin.value()) == 2
    assert _list_keys(dlg.keys_list) == [("b", True)]


def test_edit_applies_to_selected_and_stages_changes(
    monkeypatch: pytest.MonkeyPatch,
    app,
    db_manager: DatabaseManager,
    keyboard_id: str,
) -> None:
    """AC-UI-3: Edit applies to selected; RHS and list label update; Save enabled."""
    mgr = KeysetManager(db_manager)
    ks = Keyset(keyboard_id=keyboard_id, keyset_name="K1", progression_order=1)
    mgr.create_keyset(ks)

    dlg = _make_dialog(db_manager, keyboard_id)
    # Select first row
    dlg.keysets_list.setCurrentRow(0)

    # Monkeypatch the details dialog to return new values
    def fake_prompt(initial_name: str, initial_order: int) -> Tuple[str, int]:
        return ("K1-Edited", 2)

    monkeypatch.setattr(dlg, "_prompt_details", fake_prompt)  # type: ignore[arg-type]

    # Trigger edit
    dlg._on_edit_details()

    # Assert RHS updated and label updated
    assert dlg.name_edit.text() == "K1-Edited"
    assert int(dlg.order_spin.value()) == 2
    item = dlg.keysets_list.currentItem()
    assert item is not None
    assert item.text().endswith("K1-Edited")

    # Should be staged and save enabled
    assert dlg._dirty is True
    assert dlg.save_current_btn.isEnabled() is True
