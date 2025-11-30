"""Integration tests for Admin → KeysetsDialog flow.

Tests that the Admin window can successfully open the KeysetsDialog
and that the dialog initializes correctly with the admin's database connection.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QPushButton

from desktop_ui.keysets_dialog import KeysetsDialog

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestAdminKeysetsIntegration:
    """Integration tests for Admin → KeysetsDialog flow."""

    def test_keysets_dialog_opens_with_keyword_args(self, qtbot: "QtBot") -> None:
        """Test that KeysetsDialog can be instantiated with keyword arguments.

        This tests the fix for the error:
        "KeysetManagerAdapter.__init__() takes 1 positional argument but 3 were given"
        """
        mock_db = MagicMock()
        keyboard_id = str(uuid.uuid4())

        # Mock the adapter to avoid actual database operations
        with patch("desktop_ui.keysets_dialog.KeysetManagerAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.list_keysets_for_keyboard.return_value = []
            mock_adapter.preload_keysets_for_keyboard.return_value = None
            mock_adapter_class.return_value = mock_adapter

            # This should not raise an error
            dialog = KeysetsDialog(
                db_manager=mock_db,
                keyboard_id=keyboard_id,
                parent=None,
            )
            qtbot.addWidget(dialog)
            dialog._dirty = False

            # Verify the dialog was created successfully
            assert dialog is not None
            assert dialog.keyboard_id == keyboard_id
            assert dialog.db == mock_db

            # Verify the adapter was created with keyword arguments
            mock_adapter_class.assert_called_once()
            call_kwargs = mock_adapter_class.call_args.kwargs
            assert "db" in call_kwargs
            assert "debug_util" in call_kwargs

    def test_keysets_dialog_has_promote_and_demote_buttons(self, qtbot: "QtBot") -> None:
        """Test that KeysetsDialog has both Promote and Demote buttons."""
        mock_db = MagicMock()
        keyboard_id = str(uuid.uuid4())

        with patch("desktop_ui.keysets_dialog.KeysetManagerAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.list_keysets_for_keyboard.return_value = []
            mock_adapter.preload_keysets_for_keyboard.return_value = None
            mock_adapter_class.return_value = mock_adapter

            dialog = KeysetsDialog(
                db_manager=mock_db,
                keyboard_id=keyboard_id,
                parent=None,
            )
            qtbot.addWidget(dialog)
            dialog._dirty = False

            # Find buttons
            buttons = dialog.findChildren(QPushButton)
            button_texts = [btn.text() for btn in buttons]

            assert "Promote" in button_texts, "Promote button not found"
            assert "Demote" in button_texts, "Demote button not found"

    def test_keysets_dialog_buttons_have_tooltips(self, qtbot: "QtBot") -> None:
        """Test that Promote and Demote buttons have proper tooltips with shortcuts."""
        mock_db = MagicMock()
        keyboard_id = str(uuid.uuid4())

        with patch("desktop_ui.keysets_dialog.KeysetManagerAdapter") as mock_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter.list_keysets_for_keyboard.return_value = []
            mock_adapter.preload_keysets_for_keyboard.return_value = None
            mock_adapter_class.return_value = mock_adapter

            dialog = KeysetsDialog(
                db_manager=mock_db,
                keyboard_id=keyboard_id,
                parent=None,
            )
            qtbot.addWidget(dialog)
            dialog._dirty = False

            # Find Promote and Demote buttons and check tooltips
            for btn in dialog.findChildren(QPushButton):
                if btn.text() == "Promote":
                    assert "Ctrl+Up" in btn.toolTip()
                elif btn.text() == "Demote":
                    assert "Ctrl+Down" in btn.toolTip()
