"""Tests for Admin UI integration with Setting Type Manager.

Test objective: Validate that the Setting Type Manager can be launched
from the Admin UI with the live database connection.
"""

import sys
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

# Import the module so we can patch its attributes
import desktop_ui.admin as admin_module
from desktop_ui.admin import AdminUI


@pytest.fixture
def qtapp() -> QApplication:
    """Test objective: Provide QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Provide a mock DatabaseManager to avoid slow database connections."""
    mock = MagicMock()
    mock.init_tables.return_value = None
    return mock


@pytest.fixture
def admin_ui(qtapp: QApplication, mock_db_manager: MagicMock) -> Generator[AdminUI, None, None]:
    """Provide AdminUI instance with mocked database dependencies."""
    # Create mock classes that return our mocks
    mock_db_class = MagicMock(return_value=mock_db_manager)
    mock_user_mgr = MagicMock()
    mock_user_mgr.return_value.list_users.return_value = []
    mock_kb_mgr = MagicMock()
    mock_kb_mgr.return_value.list_keyboards_for_user.return_value = []
    mock_setting_mgr = MagicMock()
    mock_setting_mgr.get_instance.return_value = MagicMock()
    
    # Patch at module level before AdminUI is instantiated
    with patch.object(admin_module, "DatabaseManager", mock_db_class), \
         patch.object(admin_module, "UserManager", mock_user_mgr), \
         patch.object(admin_module, "KeyboardManager", mock_kb_mgr), \
         patch.object(admin_module, "SettingManager", mock_setting_mgr):
        
        admin = AdminUI(
            testing_mode=True,
            debug_mode="quiet",
        )
        yield admin


class TestAdminSettingTypeIntegration:
    """Test suite for Admin UI and Setting Type Manager integration."""

    def test_admin_has_manage_setting_types_button(
        self, admin_ui: AdminUI
    ) -> None:
        """Test objective: Verify Admin UI has Manage Setting Types button."""
        # Check that there are 7 buttons (including Quit)
        assert len(admin_ui.buttons) == 7
        
        # Find the Manage Setting Types button
        button_texts = [btn.text() for btn in admin_ui.buttons]
        assert "Manage Setting Types" in button_texts

    def test_manage_setting_types_method_exists(
        self, admin_ui: AdminUI
    ) -> None:
        """Test objective: Verify manage_setting_types method exists."""
        assert hasattr(admin_ui, "manage_setting_types")
        assert callable(admin_ui.manage_setting_types)

    def test_manage_setting_types_passes_db_manager(
        self, admin_ui: AdminUI
    ) -> None:
        """Test objective: Verify db_manager is passed to Setting Type Manager."""
        mock_instance = MagicMock()
        mock_window_class = MagicMock(return_value=mock_instance)
        
        # Patch where the import happens (the setting_type_manager module)
        with patch.dict(
            "sys.modules",
            {"desktop_ui.setting_type_manager": MagicMock(SettingTypeManagerWindow=mock_window_class)}
        ):
            # Call the method
            admin_ui.manage_setting_types()
            
            # Verify SettingTypeManagerWindow was instantiated with db_manager
            mock_window_class.assert_called_once_with(
                db_manager=admin_ui.db_manager, testing_mode=True
            )
            
            # Verify window was shown and exec'd
            mock_instance.showMaximized.assert_called_once()
            mock_instance.exec.assert_called_once()

    def test_manage_setting_types_handles_import_error(
        self, admin_ui: AdminUI
    ) -> None:
        """Test objective: Verify graceful handling of import errors."""
        # Remove module from cache so import fails
        with patch.dict("sys.modules", {"desktop_ui.setting_type_manager": None}):
            # Mock QMessageBox to verify error dialog is shown
            with patch.object(admin_module, "QMessageBox") as mock_msgbox:
                admin_ui.manage_setting_types()
                # Verify critical error dialog was shown
                mock_msgbox.critical.assert_called_once()

    def test_manage_setting_types_handles_runtime_error(
        self, admin_ui: AdminUI
    ) -> None:
        """Test objective: Verify graceful handling of runtime errors."""
        mock_window_class = MagicMock(side_effect=RuntimeError("Window creation failed"))
        
        with patch.dict(
            "sys.modules",
            {"desktop_ui.setting_type_manager": MagicMock(SettingTypeManagerWindow=mock_window_class)}
        ):
            # Mock QMessageBox to verify error dialog is shown
            with patch.object(admin_module, "QMessageBox") as mock_msgbox:
                admin_ui.manage_setting_types()
                # Verify critical error dialog was shown
                mock_msgbox.critical.assert_called_once()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
