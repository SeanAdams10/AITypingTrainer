"""Tests for Setting Type Manager UI.

Test objective: Validate Setting Type Manager UI functionality including
add, edit, delete operations, validation, and database integration.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from desktop_ui.setting_type_manager import SettingTypeManagerWindow
from models.library import DatabaseManager
from models.setting_type import SettingType


@pytest.fixture
def qtapp() -> QApplication:
    """Test objective: Provide QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Test objective: Provide mock DatabaseManager for testing."""
    mock_db = MagicMock(spec=DatabaseManager)
    return mock_db


@pytest.fixture
def sample_setting_types() -> list[SettingType]:
    """Test objective: Provide sample setting types for testing."""
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
            created_user_id="test-user",
            updated_user_id="test-user",
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
            created_user_id="system",
            updated_user_id="system",
        ),
    ]


class TestSettingTypeManagerWindow:
    """Test suite for SettingTypeManagerWindow."""

    def test_window_initialization(
        self, qtapp: QApplication, mock_db_manager: MagicMock
    ) -> None:
        """Test objective: Verify window initializes with correct title and size."""
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
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify setting types load into list widget."""
        with patch(
            "desktop_ui.setting_type_manager.SettingsManager"
        ) as mock_settings_mgr:
            mock_instance = MagicMock()
            mock_settings_mgr.get_instance.return_value = mock_instance
            mock_instance.list_setting_types.return_value = sample_setting_types
            
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            assert window.settingTypeList.count() == 2
            assert window.settingTypeList.item(0).text() == "User Font Size"
            assert window.settingTypeList.item(1).text() == "Keyboard Layout"

    def test_add_button_enabled(
        self, qtapp: QApplication, mock_db_manager: MagicMock
    ) -> None:
        """Test objective: Verify add button is always enabled."""
        window = SettingTypeManagerWindow(
            db_manager=mock_db_manager, testing_mode=True
        )
        
        assert window.addBtn.isEnabled()

    def test_edit_delete_buttons_disabled_initially(
        self, qtapp: QApplication, mock_db_manager: MagicMock
    ) -> None:
        """Test objective: Verify edit/delete buttons disabled without selection."""
        window = SettingTypeManagerWindow(
            db_manager=mock_db_manager, testing_mode=True
        )
        
        assert not window.editBtn.isEnabled()
        assert not window.delBtn.isEnabled()

    def test_edit_delete_buttons_enabled_on_selection(
        self,
        qtapp: QApplication,
        mock_db_manager: MagicMock,
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify edit/delete buttons enable when item selected."""
        with patch(
            "desktop_ui.setting_type_manager.SettingsManager"
        ) as mock_settings_mgr:
            mock_instance = MagicMock()
            mock_settings_mgr.get_instance.return_value = mock_instance
            mock_instance.list_setting_types.return_value = sample_setting_types
            
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
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify system setting types show warning on delete."""
        with patch(
            "desktop_ui.setting_type_manager.SettingsManager"
        ) as mock_settings_mgr:
            mock_instance = MagicMock()
            mock_settings_mgr.get_instance.return_value = mock_instance
            mock_instance.list_setting_types.return_value = sample_setting_types
            
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
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify search filter works correctly."""
        with patch(
            "desktop_ui.setting_type_manager.SettingsManager"
        ) as mock_settings_mgr:
            mock_instance = MagicMock()
            mock_settings_mgr.get_instance.return_value = mock_instance
            mock_instance.list_setting_types.return_value = sample_setting_types
            
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            # Filter by "font"
            window.filter_setting_types("font")
            
            assert window.settingTypeList.count() == 1
            assert window.settingTypeList.item(0).text() == "User Font Size"

    def test_validation_error_handling(
        self, qtapp: QApplication, mock_db_manager: MagicMock
    ) -> None:
        """Test objective: Verify validation errors are displayed to user."""
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
        sample_setting_types: list[SettingType],
    ) -> None:
        """Test objective: Verify entity type filter works correctly."""
        with patch(
            "desktop_ui.setting_type_manager.SettingsManager"
        ) as mock_settings_mgr:
            mock_instance = MagicMock()
            mock_settings_mgr.get_instance.return_value = mock_instance
            mock_instance.list_setting_types.return_value = sample_setting_types
            
            window = SettingTypeManagerWindow(
                db_manager=mock_db_manager, testing_mode=True
            )
            window.load_data()
            
            # Filter by entity type "user"
            window.filter_by_entity_type("user")
            
            assert window.settingTypeList.count() == 1
            assert window.settingTypeList.item(0).text() == "User Font Size"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
