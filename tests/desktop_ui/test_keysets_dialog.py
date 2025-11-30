"""Tests for KeysetsDialog UI component.

Tests button states, keyboard shortcuts, and UI behavior using QtBot.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Generator
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QPushButton

from desktop_ui.keysets_dialog import KeysetsDialog
from entities.keyset import Keyset

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Fixture providing a mock DatabaseManager."""
    return MagicMock()


@pytest.fixture
def keyboard_id() -> str:
    """Fixture providing a test keyboard UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Fixture providing a mock KeysetManagerAdapter."""
    adapter = MagicMock()
    # Return empty list for initial preload
    adapter.list_keysets_for_keyboard.return_value = []
    adapter.preload_keysets_for_keyboard.return_value = None
    return adapter


@pytest.fixture
def keysets_dialog(
    qtbot: "QtBot",
    mock_db_manager: MagicMock,
    keyboard_id: str,
    mock_adapter: MagicMock,
) -> Generator[KeysetsDialog, None, None]:
    """Fixture providing KeysetsDialog with mocked dependencies."""
    with patch(
        "desktop_ui.keysets_dialog.KeysetManagerAdapter", return_value=mock_adapter
    ):
        dialog = KeysetsDialog(
            db_manager=mock_db_manager,
            keyboard_id=keyboard_id,
            parent=None,
        )
        qtbot.addWidget(dialog)
        # Set dirty to False to avoid confirmation dialog on close
        dialog._dirty = False
        yield dialog
        # Don't explicitly close - let qtbot handle it


class TestKeyboardShortcuts:
    """Test keyboard shortcuts for Promote and Demote."""

    def test_promote_button_has_tooltip_with_shortcut(
        self, keysets_dialog: KeysetsDialog
    ) -> None:
        """Test that Promote button has tooltip showing Ctrl+Up shortcut."""
        # Find the Promote button
        promote_btn = None
        for widget in keysets_dialog.findChildren(QPushButton):
            if widget.text() == "Promote":
                promote_btn = widget
                break

        assert promote_btn is not None, "Promote button not found"
        assert "Ctrl+Up" in promote_btn.toolTip()

    def test_demote_button_has_tooltip_with_shortcut(
        self, keysets_dialog: KeysetsDialog
    ) -> None:
        """Test that Demote button has tooltip showing Ctrl+Down shortcut."""
        # Find the Demote button
        demote_btn = None
        for widget in keysets_dialog.findChildren(QPushButton):
            if widget.text() == "Demote":
                demote_btn = widget
                break

        assert demote_btn is not None, "Demote button not found"
        assert "Ctrl+Down" in demote_btn.toolTip()

    def test_demote_button_exists(self, keysets_dialog: KeysetsDialog) -> None:
        """Test that Demote button exists in the dialog."""
        demote_btn = None
        for widget in keysets_dialog.findChildren(QPushButton):
            if widget.text() == "Demote":
                demote_btn = widget
                break

        assert demote_btn is not None, "Demote button not found"

    def test_promote_button_exists(self, keysets_dialog: KeysetsDialog) -> None:
        """Test that Promote button exists in the dialog."""
        promote_btn = None
        for widget in keysets_dialog.findChildren(QPushButton):
            if widget.text() == "Promote":
                promote_btn = widget
                break

        assert promote_btn is not None, "Promote button not found"


class TestKeysetManagerAdapterIntegration:
    """Test that dialog uses KeysetManagerAdapter with keyword arguments."""

    def test_adapter_created_with_keyword_args(
        self,
        qtbot: "QtBot",
        mock_db_manager: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that KeysetManagerAdapter is created with keyword arguments."""
        with patch(
            "desktop_ui.keysets_dialog.KeysetManagerAdapter"
        ) as mock_adapter_class:
            mock_adapter_class.return_value.list_keysets_for_keyboard.return_value = []
            mock_adapter_class.return_value.preload_keysets_for_keyboard.return_value = (
                None
            )

            dialog = KeysetsDialog(
                db_manager=mock_db_manager,
                keyboard_id=keyboard_id,
                parent=None,
            )
            qtbot.addWidget(dialog)

            # Verify adapter was called with keyword arguments
            mock_adapter_class.assert_called_once()
            call_kwargs = mock_adapter_class.call_args.kwargs
            assert "db" in call_kwargs
            assert "debug_util" in call_kwargs
            assert call_kwargs["db"] == mock_db_manager

            dialog.close()


class TestDemoteHandler:
    """Test the demote button handler."""

    def test_demote_calls_manager_demote_keyset(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that clicking Demote calls manager.demote_keyset."""
        # Create a mock keyset to select
        keyset_id = str(uuid.uuid4())
        mock_keyset = Keyset(
            keyset_id=keyset_id,
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[],
        )

        # Add keyset to the list
        mock_adapter.list_keysets_for_keyboard.return_value = [mock_keyset]
        keysets_dialog._load_keysets()

        # Select the first item
        keysets_dialog.keysets_list.setCurrentRow(0)

        # Mock the demote_keyset method
        mock_adapter.demote_keyset.return_value = True

        # Click the demote button
        keysets_dialog._on_demote()

        # Verify demote_keyset was called
        mock_adapter.demote_keyset.assert_called_once_with(keyboard_id, keyset_id)
