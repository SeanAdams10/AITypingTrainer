"""Integration-style tests for MainMenu -> Practice Weak Points flow."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from desktop_ui.main_menu import ConnectionType, MainMenu
from models.keyboard import Keyboard
from models.user import User

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestMainMenuPracticeWeakPoints:
    """Regression coverage for opening Practice Weak Points from MainMenu."""

    def test_practice_weak_points_button_opens_dynamic_config_with_selected_context(
        self,
        qtbot: "QtBot",
    ) -> None:
        """Clicking the main-menu button should open DynamicConfigDialog with user+keyboard IDs."""
        user_id = str(uuid.uuid4())
        keyboard_id = str(uuid.uuid4())

        user = User(
            user_id=user_id,
            first_name="Sean",
            surname="Adams",
            email_address="sean.adams@example.com",
        )
        keyboard = Keyboard(
            keyboard_id=keyboard_id,
            user_id=user_id,
            keyboard_name="Logi Ergo",
            target_ms_per_keystroke=600,
        )

        mock_db_manager = MagicMock()
        mock_db_manager.init_tables.return_value = None

        mock_user_manager = MagicMock()
        mock_user_manager.list_all_users.return_value = [user]

        mock_keyboard_manager = MagicMock()
        mock_keyboard_manager.list_keyboards_for_user.return_value = [keyboard]

        mock_setting_manager = MagicMock()

        with (
            patch("desktop_ui.main_menu.DatabaseManager", return_value=mock_db_manager),
            patch("desktop_ui.main_menu.UserManager", return_value=mock_user_manager),
            patch("desktop_ui.main_menu.KeyboardManager", return_value=mock_keyboard_manager),
            patch("desktop_ui.main_menu.SettingManager.get_instance", return_value=mock_setting_manager),
            patch("desktop_ui.dynamic_config.DynamicConfigDialog") as mock_dialog_class,
        ):
            mock_dialog_instance = MagicMock()
            mock_dialog_class.return_value = mock_dialog_instance

            menu = MainMenu(
                testing_mode=True,
                connection_type=ConnectionType.POSTGRESS_DOCKER,
                debug_mode="quiet",
            )
            qtbot.addWidget(menu)

            practice_btn = next(btn for btn in menu.buttons if btn.text() == "Practice Weak Points")
            qtbot.mouseClick(practice_btn, Qt.MouseButton.LeftButton)

            mock_dialog_class.assert_called_once()
            call_kwargs = mock_dialog_class.call_args.kwargs
            assert call_kwargs["db_manager"] is mock_db_manager
            assert call_kwargs["user_id"] == user_id
            assert call_kwargs["keyboard_id"] == keyboard_id
            assert call_kwargs["parent"] is menu
            mock_dialog_instance.exec.assert_called_once()
