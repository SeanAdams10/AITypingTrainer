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
    with patch("desktop_ui.keysets_dialog.KeysetManagerAdapter", return_value=mock_adapter):
        dialog = KeysetsDialog(
            db_manager=mock_db_manager,
            keyboard_id=keyboard_id,
            user_id=str(uuid.uuid4()),
            parent=None,
        )
        qtbot.addWidget(dialog)
        # Set dirty to False to avoid confirmation dialog on close
        dialog._dirty = False
        yield dialog
        # Don't explicitly close - let qtbot handle it


class TestKeyboardShortcuts:
    """Test keyboard shortcuts for Promote and Demote."""

    def test_promote_button_has_tooltip_with_shortcut(self, keysets_dialog: KeysetsDialog) -> None:
        """Test that Promote button has tooltip showing Ctrl+Up shortcut."""
        # Find the Promote button
        promote_btn = None
        for widget in keysets_dialog.findChildren(QPushButton):
            if widget.text() == "Promote":
                promote_btn = widget
                break

        assert promote_btn is not None, "Promote button not found"
        assert "Ctrl+Up" in promote_btn.toolTip()

    def test_demote_button_has_tooltip_with_shortcut(self, keysets_dialog: KeysetsDialog) -> None:
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
        with patch("desktop_ui.keysets_dialog.KeysetManagerAdapter") as mock_adapter_class:
            mock_adapter_class.return_value.list_keysets_for_keyboard.return_value = []
            mock_adapter_class.return_value.preload_keysets_for_keyboard.return_value = None

            dialog = KeysetsDialog(
                db_manager=mock_db_manager,
                keyboard_id=keyboard_id,
                user_id=str(uuid.uuid4()),
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

        # Verify demote_keyset was called with keyword arguments
        mock_adapter.demote_keyset.assert_called_once_with(
            keyboard_id=keyboard_id, keyset_id=keyset_id, updated_by=keysets_dialog.user_id
        )

        # Reset dirty flag to prevent unsaved changes dialog on teardown
        keysets_dialog._dirty = False


class TestSaveAllBehavior:
    """Test that Save button saves ALL staged keysets."""

    def test_save_button_calls_save_all_keysets(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that Save button persists all staged keysets, not just selected."""
        # Create two mock keysets
        keyset1 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Keyset 1",
            progression_order=1,
            keys=[],
        )
        keyset2 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Keyset 2",
            progression_order=2,
            keys=[],
        )

        # Stage both keysets
        keysets_dialog._staged[str(keyset1.keyset_id)] = keyset1
        keysets_dialog._staged[str(keyset2.keyset_id)] = keyset2
        keysets_dialog._dirty = True

        # Mock save_all_keysets to return True
        mock_adapter.save_all_keysets.return_value = True
        mock_adapter.list_keysets_for_keyboard.return_value = [keyset1, keyset2]

        # Call _on_save_all
        keysets_dialog._on_save_all()

        # Verify save_all_keysets was called with both keysets
        mock_adapter.save_all_keysets.assert_called_once()
        call_kwargs = mock_adapter.save_all_keysets.call_args.kwargs
        assert "keysets" in call_kwargs
        assert len(call_kwargs["keysets"]) == 2

        keysets_dialog._dirty = False

    def test_save_button_labeled_save_all(self, keysets_dialog: KeysetsDialog) -> None:
        """Test that Save button is labeled 'Save All'."""
        assert keysets_dialog.save_current_btn.text() == "Save All"


class TestPromoteDemoteUnsavedCheck:
    """Test that Promote/Demote require saved keysets."""

    def test_promote_unsaved_keyset_shows_warning(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
        qtbot: "QtBot",
    ) -> None:
        """Test that promoting an unsaved (temp-*) keyset shows warning."""
        from PySide6 import QtCore
        from PySide6.QtWidgets import QListWidgetItem

        # Add a temp keyset to the list
        temp_keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Unsaved Keyset",
            progression_order=1,
            keys=[],
        )
        temp_id = "temp-1"
        keysets_dialog._staged[temp_id] = temp_keyset
        
        item = QListWidgetItem("01: Unsaved Keyset")
        item.setData(QtCore.Qt.ItemDataRole.UserRole, temp_id)
        keysets_dialog.keysets_list.addItem(item)
        keysets_dialog.keysets_list.setCurrentItem(item)

        # Mock QMessageBox to capture the warning
        with patch("desktop_ui.keysets_dialog.QtWidgets.QMessageBox.warning") as mock_warning:
            keysets_dialog._on_promote()
            
            # Verify warning was shown
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert "save" in str(call_args).lower()

        keysets_dialog._dirty = False

    def test_demote_unsaved_keyset_shows_warning(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that demoting an unsaved (temp-*) keyset shows warning."""
        from PySide6 import QtCore
        from PySide6.QtWidgets import QListWidgetItem

        # Add a temp keyset to the list
        temp_keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Unsaved Keyset",
            progression_order=1,
            keys=[],
        )
        temp_id = "temp-1"
        keysets_dialog._staged[temp_id] = temp_keyset
        
        item = QListWidgetItem("01: Unsaved Keyset")
        item.setData(QtCore.Qt.ItemDataRole.UserRole, temp_id)
        keysets_dialog.keysets_list.addItem(item)
        keysets_dialog.keysets_list.setCurrentItem(item)

        # Mock QMessageBox to capture the warning
        with patch("desktop_ui.keysets_dialog.QtWidgets.QMessageBox.warning") as mock_warning:
            keysets_dialog._on_demote()
            
            # Verify warning was shown
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert "save" in str(call_args).lower()

        keysets_dialog._dirty = False


class TestKeyValidation:
    """Test that key addition validates against earlier keysets."""

    def test_get_earlier_keyset_keys_returns_keys_from_lower_order(
        self,
        keysets_dialog: KeysetsDialog,
        keyboard_id: str,
    ) -> None:
        """Test _get_earlier_keyset_keys returns keys from lower progression orders."""
        from entities.keyset_key import KeysetKey

        # Create keysets with different orders
        keyset1 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="First",
            progression_order=1,
            keys=[KeysetKey(key_char="a", is_new_key=True), KeysetKey(key_char="b", is_new_key=True)],
        )
        keyset2 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Second",
            progression_order=2,
            keys=[KeysetKey(key_char="c", is_new_key=True)],
        )
        keyset3 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Third",
            progression_order=3,
            keys=[],
        )

        # Stage all keysets
        keysets_dialog._staged[str(keyset1.keyset_id)] = keyset1
        keysets_dialog._staged[str(keyset2.keyset_id)] = keyset2
        keysets_dialog._staged[str(keyset3.keyset_id)] = keyset3

        # Get keys for order 3 (should include keys from orders 1 and 2)
        earlier_keys = keysets_dialog._get_earlier_keyset_keys(3)
        
        assert "a" in earlier_keys
        assert "b" in earlier_keys
        assert "c" in earlier_keys

        # Get keys for order 2 (should only include keys from order 1)
        earlier_keys = keysets_dialog._get_earlier_keyset_keys(2)
        
        assert "a" in earlier_keys
        assert "b" in earlier_keys
        assert "c" not in earlier_keys

        keysets_dialog._dirty = False


class TestSaveReloadBehavior:
    """Test save and reload behavior to prevent duplicate key errors."""

    def test_load_keysets_clears_staged_to_prevent_duplicates(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that _load_keysets clears _staged to prevent duplicate entries.
        
        Regression test for bug where temp-* entries remained in _staged after
        save+reload, causing UniqueViolation on subsequent saves.
        """
        # Simulate a temp keyset that was staged before save
        temp_keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[],
        )
        keysets_dialog._staged["temp-1"] = temp_keyset

        # Now simulate a saved keyset being returned from the database
        saved_keyset = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Test Keyset",
            progression_order=1,
            keys=[],
        )
        mock_adapter.list_keysets_for_keyboard.return_value = [saved_keyset]

        # Load keysets (simulating post-save reload)
        keysets_dialog._load_keysets()

        # Verify temp-1 was cleared and only the saved keyset remains
        assert "temp-1" not in keysets_dialog._staged
        assert saved_keyset.keyset_id in keysets_dialog._staged
        assert len(keysets_dialog._staged) == 1

        keysets_dialog._dirty = False

    def test_save_all_then_reload_does_not_duplicate_keysets(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that saving all keysets and reloading doesn't create duplicates.
        
        This tests the full flow: create temp keyset -> save all -> reload should
        result in only the saved keyset being in _staged (not temp + saved).
        """
        from PySide6 import QtCore
        from PySide6.QtWidgets import QListWidgetItem

        # Add a temp keyset
        temp_keyset = Keyset(
            keyboard_id=keyboard_id,
            keyset_name="New Keyset",
            progression_order=1,
            keys=[],
        )
        temp_id = "temp-1"
        keysets_dialog._staged[temp_id] = temp_keyset

        item = QListWidgetItem("01: New Keyset")
        item.setData(QtCore.Qt.ItemDataRole.UserRole, temp_id)
        keysets_dialog.keysets_list.addItem(item)
        keysets_dialog.keysets_list.setCurrentItem(item)

        # Simulate saved keyset returned after save
        saved_id = str(uuid.uuid4())
        saved_keyset = Keyset(
            keyset_id=saved_id,
            keyboard_id=keyboard_id,
            keyset_name="New Keyset",
            progression_order=1,
            keys=[],
            in_db=True,
        )
        mock_adapter.save_all_keysets.return_value = True
        mock_adapter.list_keysets_for_keyboard.return_value = [saved_keyset]

        # Mock QMessageBox to suppress dialogs
        with patch("desktop_ui.keysets_dialog.QtWidgets.QMessageBox.information"):
            keysets_dialog._on_save_all()

        # Verify only the saved keyset is in _staged
        assert temp_id not in keysets_dialog._staged
        assert saved_id in keysets_dialog._staged
        assert len(keysets_dialog._staged) == 1

        keysets_dialog._dirty = False


class TestDuplicateNameValidation:
    """Test duplicate keyset name validation."""

    def test_check_duplicate_keyset_names_detects_duplicates(
        self,
        keysets_dialog: KeysetsDialog,
        keyboard_id: str,
    ) -> None:
        """Test that _check_duplicate_keyset_names detects duplicate names."""
        # Create two keysets with the same name
        keyset1 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Same Name",
            progression_order=1,
            keys=[],
        )
        keyset2 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Same Name",  # Duplicate!
            progression_order=2,
            keys=[],
        )

        keysets_dialog._staged["id1"] = keyset1
        keysets_dialog._staged["id2"] = keyset2

        error = keysets_dialog._check_duplicate_keyset_names()
        assert error is not None
        assert "Same Name" in error
        assert "unique" in error.lower() or "duplicate" in error.lower()

        keysets_dialog._dirty = False

    def test_check_duplicate_keyset_names_case_insensitive(
        self,
        keysets_dialog: KeysetsDialog,
        keyboard_id: str,
    ) -> None:
        """Test that duplicate check is case-insensitive."""
        keyset1 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="TestSet",
            progression_order=1,
            keys=[],
        )
        keyset2 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="testset",  # Same name, different case
            progression_order=2,
            keys=[],
        )

        keysets_dialog._staged["id1"] = keyset1
        keysets_dialog._staged["id2"] = keyset2

        error = keysets_dialog._check_duplicate_keyset_names()
        assert error is not None

        keysets_dialog._dirty = False

    def test_check_duplicate_keyset_names_no_duplicates(
        self,
        keysets_dialog: KeysetsDialog,
        keyboard_id: str,
    ) -> None:
        """Test that unique names pass validation."""
        keyset1 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="First Set",
            progression_order=1,
            keys=[],
        )
        keyset2 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Second Set",
            progression_order=2,
            keys=[],
        )

        keysets_dialog._staged["id1"] = keyset1
        keysets_dialog._staged["id2"] = keyset2

        error = keysets_dialog._check_duplicate_keyset_names()
        assert error is None

        keysets_dialog._dirty = False

    def test_save_all_with_duplicate_names_shows_warning(
        self,
        keysets_dialog: KeysetsDialog,
        mock_adapter: MagicMock,
        keyboard_id: str,
    ) -> None:
        """Test that _on_save_all shows warning for duplicate names and doesn't save."""
        # Create two keysets with the same name
        keyset1 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Duplicate",
            progression_order=1,
            keys=[],
        )
        keyset2 = Keyset(
            keyset_id=str(uuid.uuid4()),
            keyboard_id=keyboard_id,
            keyset_name="Duplicate",
            progression_order=2,
            keys=[],
        )

        keysets_dialog._staged["id1"] = keyset1
        keysets_dialog._staged["id2"] = keyset2

        # Mock the QMessageBox
        with patch("desktop_ui.keysets_dialog.QtWidgets.QMessageBox.warning") as mock_warning:
            keysets_dialog._on_save_all()

            # Verify warning was shown
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            assert "duplicate" in str(call_args).lower()

        # Verify save was NOT called
        mock_adapter.save_all_keysets.assert_not_called()

        keysets_dialog._dirty = False
