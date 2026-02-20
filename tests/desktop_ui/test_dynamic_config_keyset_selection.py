"""Regression tests for DynamicConfigDialog keyset loading/selection in Practice Weak Points."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QAbstractItemView

from desktop_ui.dynamic_config import DynamicConfigDialog
from desktop_ui.dynamic_config import KeysetSelectionDialog
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey


class _CollectionWithCurrentApi:
    """Test double exposing current KeysetCollection API only."""

    def __init__(self, keysets: list[Keyset]) -> None:
        self._keysets = keysets
        self.loaded_keyboard_id: str | None = None

    def load_for_keyboard(self, *, keyboard_id: str) -> None:
        self.loaded_keyboard_id = keyboard_id

    def get_keysets_ordered(self) -> list[Keyset]:
        return self._keysets


class TestPracticeWeakPointsKeysetSelection:
    """Regression coverage for weak-points Select Keyset availability."""

    def test_load_keysets_uses_current_collection_api_and_populates_keysets(self) -> None:
        """Regression: _load_keysets should work with current collection API.

        The weak-points dialog must load keysets using:
        - load_for_keyboard(...)
        - get_keysets_ordered()
        and not rely on removed list_for_keyboard(...).
        """
        keyboard_id = str(uuid.uuid4())
        expected_keyset = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Home Keys",
            progression_order=1,
            keys=[],
        )
        collection = _CollectionWithCurrentApi([expected_keyset])
        button = MagicMock()

        fake_dialog = SimpleNamespace(
            keyboard_id=keyboard_id,
            keyset_collection=collection,
            keysets=[],
            select_keyset_btn=button,
            _debug_message=lambda *_args, **_kwargs: None,
        )

        DynamicConfigDialog._load_keysets(fake_dialog)

        assert collection.loaded_keyboard_id == keyboard_id
        assert len(fake_dialog.keysets) == 1
        assert fake_dialog.keysets[0].keyset_name == "Home Keys"
        button.setEnabled.assert_called_with(True)

    def test_on_select_keyset_does_not_show_no_keysets_when_keysets_loaded(self) -> None:
        """Regression: Select Keyset should open selection when keysets exist."""
        keyboard_id = str(uuid.uuid4())
        existing_keyset = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Home Keys",
            progression_order=1,
            keys=[],
        )
        fake_dialog = SimpleNamespace(
            keysets=[existing_keyset],
            current_keyset=None,
            included_keys=MagicMock(),
            _get_accumulated_keys=lambda _target: ["a", "s", "d"],
        )

        dialog_instance = MagicMock()
        dialog_instance.exec.return_value = 0  # Cancel

        with (
            patch("desktop_ui.dynamic_config.QMessageBox.information") as mock_info,
            patch("desktop_ui.dynamic_config.KeysetSelectionDialog", return_value=dialog_instance),
        ):
            DynamicConfigDialog._on_select_keyset(fake_dialog)

        mock_info.assert_not_called()

    def test_on_select_keyset_uses_unique_union_for_multiple_selected_keysets(self) -> None:
        """Regression: selecting multiple keysets should populate unique union of their keys."""
        keyboard_id = str(uuid.uuid4())
        keyset_one = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Home Keys",
            progression_order=1,
            keys=[
                KeysetKey(key_char="a", is_new_key=False),
                KeysetKey(key_char="s", is_new_key=False),
            ],
        )
        keyset_two = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="rtuy",
            progression_order=2,
            keys=[
                KeysetKey(key_char="s", is_new_key=True),
                KeysetKey(key_char="t", is_new_key=True),
                KeysetKey(key_char="u", is_new_key=True),
            ],
        )
        fake_dialog = SimpleNamespace(
            keysets=[keyset_one, keyset_two],
            current_keyset=None,
            included_keys=MagicMock(),
            _get_accumulated_keys=lambda target: [k.key_char for k in target.keys],
        )

        dialog_instance = MagicMock()
        dialog_instance.exec.return_value = 1  # Accepted
        dialog_instance.get_selected_keyset.return_value = keyset_one
        dialog_instance.get_selected_keysets.return_value = [keyset_one, keyset_two]

        with patch("desktop_ui.dynamic_config.KeysetSelectionDialog", return_value=dialog_instance):
            DynamicConfigDialog._on_select_keyset(fake_dialog)

        fake_dialog.included_keys.setText.assert_called_once_with("astu")


class TestKeysetSelectionDialogMultiSelect:
    """Dialog behavior for selecting multiple keysets."""

    def test_dialog_enables_multi_select_and_returns_all_selected(
        self,
        qtbot,
    ) -> None:
        """Dialog should allow multi-selection and return all selected keysets."""
        keyboard_id = str(uuid.uuid4())
        keyset_one = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Home Keys",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=False)],
        )
        keyset_two = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="rtuy",
            progression_order=2,
            keys=[KeysetKey(key_char="r", is_new_key=True)],
        )

        dialog = KeysetSelectionDialog(keysets=[keyset_one, keyset_two], parent=None)
        qtbot.addWidget(dialog)

        assert (
            dialog.keyset_list.selectionMode()
            == QAbstractItemView.SelectionMode.MultiSelection
        )

        dialog.keyset_list.item(0).setSelected(True)
        dialog.keyset_list.item(1).setSelected(True)
        dialog.accept()

        selected = dialog.get_selected_keysets()
        assert len(selected) == 2
        assert {ks.keyset_name for ks in selected} == {"Home Keys", "rtuy"}
