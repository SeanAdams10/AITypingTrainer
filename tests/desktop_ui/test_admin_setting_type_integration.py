"""Tests for Admin UI integration with Setting Type Manager.

Test objective: Validate that the Setting Type Manager can be launched
from the Admin UI with the live database connection.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from db.database_manager import ConnectionType
from desktop_ui.admin import AdminUI


@pytest.fixture
def qtapp() -> QApplication:
    """Test objective: Provide QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestAdminSettingTypeIntegration:
    """Test suite for Admin UI and Setting Type Manager integration."""

    def test_admin_has_manage_setting_types_button(
        self, qtapp: QApplication
    ) -> None:
        """Test objective: Verify Admin UI has Manage Setting Types button."""
        admin = AdminUI(
            testing_mode=True,
            connection_type=ConnectionType.POSTGRESS_DOCKER,
            debug_mode="quiet",
        )
        
        # Check that there are 6 buttons (including the new one)
        assert len(admin.buttons) == 6
        
        # Find the Manage Setting Types button
        button_texts = [btn.text() for btn in admin.buttons]
        assert "Manage Setting Types" in button_texts

    def test_manage_setting_types_method_exists(
        self, qtapp: QApplication
    ) -> None:
        """Test objective: Verify manage_setting_types method exists."""
        admin = AdminUI(
            testing_mode=True,
            connection_type=ConnectionType.POSTGRESS_DOCKER,
            debug_mode="quiet",
        )
        
        assert hasattr(admin, "manage_setting_types")
        assert callable(admin.manage_setting_types)

    def test_manage_setting_types_passes_db_manager(
        self, qtapp: QApplication
    ) -> None:
        """Test objective: Verify db_manager is passed to Setting Type Manager."""
        admin = AdminUI(
            testing_mode=True,
            connection_type=ConnectionType.POSTGRESS_DOCKER,
            debug_mode="quiet",
        )
        
        with patch(
            "desktop_ui.admin.SettingTypeManagerWindow"
        ) as mock_window_class:
            mock_instance = MagicMock()
            mock_window_class.return_value = mock_instance
            
            # Call the method
            admin.manage_setting_types()
            
            # Verify SettingTypeManagerWindow was instantiated with db_manager
            mock_window_class.assert_called_once_with(
                db_manager=admin.db_manager, testing_mode=True
            )
            
            # Verify window was shown and exec'd
            mock_instance.showMaximized.assert_called_once()
            mock_instance.exec.assert_called_once()

    def test_manage_setting_types_handles_import_error(
        self, qtapp: QApplication
    ) -> None:
        """Test objective: Verify graceful handling of import errors."""
        admin = AdminUI(
            testing_mode=True,
            connection_type=ConnectionType.POSTGRESS_DOCKER,
            debug_mode="quiet",
        )
        
        with patch(
            "desktop_ui.admin.SettingTypeManagerWindow",
            side_effect=ImportError("Module not found"),
        ):
            # Should not raise, but show error dialog in non-testing mode
            # In testing mode, it just prints
            admin.manage_setting_types()
            # Test passes if no exception raised

    def test_manage_setting_types_handles_runtime_error(
        self, qtapp: QApplication
    ) -> None:
        """Test objective: Verify graceful handling of runtime errors."""
        admin = AdminUI(
            testing_mode=True,
            connection_type=ConnectionType.POSTGRESS_DOCKER,
            debug_mode="quiet",
        )
        
        with patch(
            "desktop_ui.admin.SettingTypeManagerWindow",
            side_effect=RuntimeError("Window creation failed"),
        ):
            # Should not raise, but show error dialog in non-testing mode
            admin.manage_setting_types()
            # Test passes if no exception raised


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
