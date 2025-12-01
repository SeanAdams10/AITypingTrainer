"""Tests for Setting Type Manager UI.

Test objective: Validate Setting Type Manager UI functionality including
add, edit, delete operations, validation, and database integration.
"""

import sys
from typing import Generator, Optional
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

import desktop_ui.setting_type_manager as stm_module
from db.database_manager import DatabaseManager
from desktop_ui.setting_type_manager import SettingTypeManagerWindow
from models.setting_type import SettingType


@pytest.fixture
def qtapp() -> QApplication:
    """Test objective: Provide QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app  # type: ignore[return-value]


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Test objective: Provide mock DatabaseManager for testing."""
    mock_db = MagicMock(spec=DatabaseManager)
    return mock_db


@pytest.fixture
def mock_setting_type_manager() -> MagicMock:
    """Provide a mock SettingTypeManager."""
    mock = MagicMock()
    mock.list_setting_types.return_value = []
    return mock


@pytest.fixture
def window_with_mocks(
    qtapp: QApplication,
    mock_db_manager: MagicMock,
    mock_setting_type_manager: MagicMock,
) -> Generator[SettingTypeManagerWindow, None, None]:
    """Provide SettingTypeManagerWindow with mocked dependencies."""
    with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
        window = SettingTypeManagerWindow(
            db_manager=mock_db_manager, testing_mode=True
        )
        yield window


@pytest.fixture
def sample_setting_types() -> list[SettingType]:
    """Test objective: Provide sample setting types for testing."""
    test_user_id = "00000000-0000-0000-0000-000000000001"
    system_user_id = "00000000-0000-0000-0000-000000000000"
    return [
        SettingType(
            setting_type_id="USRFNT",
            setting_type_name="User Font Size",
            description="Font size preference for user interface",
            related_entity_type="user",
            data_type="integer",
            default_value="14",
            validation_rules='{"min": 8, "max": 32}',
            is_system=False,
            is_active=True,
            created_user_id=test_user_id,
            updated_user_id=test_user_id,
        ),
        SettingType(
            setting_type_id="KBDLAY",
            setting_type_name="Keyboard Layout",
            description="Keyboard layout preference",
            related_entity_type="keyboard",
            data_type="string",
            default_value="QWERTY",
            validation_rules='{"pattern": "^[A-Z]+$"}',
            is_system=True,
            is_active=True,
            created_user_id=system_user_id,
            updated_user_id=system_user_id,
        ),
    ]


class TestSettingTypeManagerWindow:
    """Test suite for SettingTypeManagerWindow."""

    def test_window_initialization(
        self, qtapp: QApplication, mock_db_manager: MagicMock, mock_setting_type_manager: MagicMock
    ) -> None:
        """Test objective: Verify window initializes with correct title and size."""
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            
            assert window.windowTitle() == "Setting Type Manager"
            assert window.minimumSize().width() >= 900
            assert window.minimumSize().height() >= 600
            assert window.db_manager == mock_db_manager

    def test_load_setting_types(
        self,
        qtapp: QApplication,
        mock_db_manager: MagicMock,
        mock_setting_type_manager: MagicMock,
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify setting types load into list widget."""
        mock_setting_type_manager.list_setting_types.return_value = sample_setting_types
        
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            assert window.settingTypeList.count() == 2
            assert window.settingTypeList.item(0).text() == "User Font Size"
            assert window.settingTypeList.item(1).text() == "Keyboard Layout"

    def test_add_button_enabled(
        self, qtapp: QApplication, mock_db_manager: MagicMock, mock_setting_type_manager: MagicMock
    ) -> None:
        """Test objective: Verify add button is always enabled."""
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            
            assert window.addBtn.isEnabled()

    def test_edit_delete_buttons_disabled_initially(
        self, qtapp: QApplication, mock_db_manager: MagicMock, mock_setting_type_manager: MagicMock
    ) -> None:
        """Test objective: Verify edit/delete buttons disabled without selection."""
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            
            assert not window.editBtn.isEnabled()
            assert not window.delBtn.isEnabled()

    def test_edit_delete_buttons_enabled_on_selection(
        self,
        qtapp: QApplication,
        mock_db_manager: MagicMock,
        mock_setting_type_manager: MagicMock,
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify edit/delete buttons enable when item selected."""
        mock_setting_type_manager.list_setting_types.return_value = sample_setting_types
        
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            # Select first item
            window.settingTypeList.setCurrentRow(0)
            
            assert window.editBtn.isEnabled()
            assert window.delBtn.isEnabled()

    def test_system_setting_type_cannot_be_deleted(
        self,
        qtapp: QApplication,
        mock_db_manager: MagicMock,
        mock_setting_type_manager: MagicMock,
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify system setting types show warning on delete."""
        mock_setting_type_manager.list_setting_types.return_value = sample_setting_types
        
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            # Select system setting type (second item)
            window.settingTypeList.setCurrentRow(1)
            
            # Attempt delete
            window.delete_setting_type()
            
            # Should show error about system setting type
            assert "system setting type" in window.status.text().lower()

    def test_filter_setting_types(
        self,
        qtapp: QApplication,
        mock_db_manager: MagicMock,
        mock_setting_type_manager: MagicMock,
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify search filter works correctly."""
        mock_setting_type_manager.list_setting_types.return_value = sample_setting_types
        
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            # Set search text in the input field, then trigger filter
            window.search_input.setText("font")
            window.filter_setting_types("font")
            
            assert window.settingTypeList.count() == 1
            assert window.settingTypeList.item(0).text() == "User Font Size"

    def test_validation_error_handling(
        self, qtapp: QApplication, mock_db_manager: MagicMock, mock_setting_type_manager: MagicMock
    ) -> None:
        """Test objective: Verify validation errors are displayed to user."""
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            
            # Show error
            window.show_error("Test validation error")
            
            assert "Test validation error" in window.status.text()

    def test_entity_type_filter(
        self,
        qtapp: QApplication,
        mock_db_manager: MagicMock,
        mock_setting_type_manager: MagicMock,
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify entity type filter works correctly."""
        # Filter the sample data to only "user" entity types
        user_setting_types = [st for st in sample_setting_types if st.related_entity_type == "user"]
        
        # Configure mock to return filtered results when entity_type is specified
        def list_setting_types_side_effect(
            entity_type: Optional[str] = None, active_only: bool = True
        ) -> list[SettingType]:
            if entity_type == "user":
                return user_setting_types
            return sample_setting_types
        
        mock_setting_type_manager.list_setting_types.side_effect = list_setting_types_side_effect
        
        with patch.object(stm_module, "SettingTypeManager", return_value=mock_setting_type_manager):
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            # Initially should have all 2 items
            assert window.settingTypeList.count() == 2
            
            # Filter by entity type "user"
            window.filter_by_entity_type("user")
            
            assert window.settingTypeList.count() == 1
            assert window.settingTypeList.item(0).text() == "User Font Size"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
