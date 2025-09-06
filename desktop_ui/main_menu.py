"""Main Menu UI for AI Typing Trainer.

Modern main menu interface using PySide6 with user selection, keyboard management,
and session controls.
"""

import os
import sys
import warnings
from typing import Optional, cast

# Ensure project root is in sys.path before any project imports
# isort: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# isort: on

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from db.database_manager import ConnectionType, DatabaseManager
from desktop_ui.users_and_keyboards import UsersAndKeyboards
from helpers.debug_util import DebugUtil
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.setting import Setting
from models.setting_manager import SettingManager
from models.user import User
from models.user_manager import UserManager

warnings.filterwarnings("ignore", message="sipPyTypeDict() is deprecated")


class MainMenu(QWidget):
    """Modern Main Menu UI for AI Typing Trainer (PySide6).

    - Uses Fusion style, Segoe UI font, and modern color palette
    - Initiates a single DatabaseManager connection to typing_data.db
    - Passes the open database connection to the Library window
    - Testable: supports dependency injection and testing_mode
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        testing_mode: bool = False,
        connection_type: ConnectionType = ConnectionType.CLOUD,
        debug_mode: str = "loud",
    ) -> None:
        """Initialize the MainMenu with database configuration and options.

        Args:
            db_path: Path to the database file
            testing_mode: Whether running in test mode
            connection_type: Type of database connection to use
            debug_mode: Debug output level
        """
        super().__init__()
        self.setWindowTitle("AI Typing Trainer")
        self.resize(600, 600)
        self.testing_mode = testing_mode

        # Set debug mode and create DebugUtil instance
        if debug_mode.lower() not in ["loud", "quiet"]:
            debug_mode = "loud"  # Default to loud if invalid value provided
        os.environ["AI_TYPING_TRAINER_DEBUG_MODE"] = debug_mode.lower()

        # Create DebugUtil instance
        self.debug_util = DebugUtil()
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")
        self.db_manager = DatabaseManager(
            db_path, connection_type=connection_type, debug_util=self.debug_util
        )
        self.db_manager.init_tables()  # Ensure all tables are created/initialized

        # Initialize managers
        self.user_manager = UserManager(self.db_manager)
        self.keyboard_manager = KeyboardManager(self.db_manager)

        # Initialize attributes that will be set later
        self.library_ui: Optional[QWidget] = None
        self.user_combo: Optional[QComboBox] = None
        self.keyboard_combo: Optional[QComboBox] = None
        self.heatmap_dialog: Optional[QDialog] = None

        # Store current selections
        self.current_user: Optional[User] = None
        self.current_keyboard: Optional[Keyboard] = None
        self.setting_manager = SettingManager(self.db_manager)
        self.keyboard_loaded = False

        self.center_on_screen()
        self.setup_ui()

    def center_on_screen(self) -> None:
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()
            size = self.geometry()
            x = screen_geometry.x() + (screen_geometry.width() - size.width()) // 2
            y = screen_geometry.y() + (screen_geometry.height() - size.height()) // 2
            self.move(x, y)

    def setup_ui(self) -> None:
        """Set up the main user interface components."""
        layout = QVBoxLayout()
        header = QLabel("AI Typing Trainer")
        # Use correct alignment flag for PySide6
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = header.font()
        font.setPointSize(18)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        # Add user and keyboard selection
        self.setup_user_keyboard_selection(layout)

        button_data = [
            ("Manage Your Library of Text", self.open_library),
            ("Do a Typing Drill", self.configure_drill),
            ("Practice Weak Points", self.practice_weak_points),
            ("Games", self.open_games_menu),
            ("View Last Progress", self.view_last_progress),
            ("N-gram Speed Heatmap", self.open_ngram_heatmap),
            ("Data Management", self.data_management),
            ("View DB Content", self.open_db_content_viewer),
            ("Query the DB", self.open_sql_query_screen),
            ("Manage Users & Keyboards", self.manage_users_keyboards),
            ("Edit Keysets", self.open_keysets),
            ("Quit Application", self.quit_app),
        ]
        self.buttons = []
        for text, slot in button_data:
            btn = QPushButton(text)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(self.button_stylesheet(normal=True))
            btn.clicked.connect(slot)
            btn.installEventFilter(self)
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()
        self.setLayout(layout)

    def button_stylesheet(self, normal: bool = True) -> str:
        """Return CSS stylesheet for button styling."""
        if normal:
            return (
                "QPushButton { background-color: #0d6efd; color: white; border-radius: 5px; "
                "font-size: 14px; }"
                "QPushButton:pressed { background-color: #0b5ed7; }"
            )
        else:
            return (
                "QPushButton { background-color: #f0f0f0; color: black; border-radius: 5px; "
                "font-size: 14px; }"
            )

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle mouse events for button hover effects."""
        if isinstance(obj, QPushButton):
            if event.type() == QEvent.Type.Enter:
                obj.setStyleSheet(self.button_stylesheet(normal=False))
            elif event.type() == QEvent.Type.Leave:
                obj.setStyleSheet(self.button_stylesheet(normal=True))
        return super().eventFilter(obj, event)

    # Placeholder slots for button actions
    def open_library(self) -> None:
        """Open the Snippets Library main window, passing the existing DatabaseManager."""
        try:
            from desktop_ui.library_main import LibraryMainWindow

            window = LibraryMainWindow(db_manager=self.db_manager, testing_mode=self.testing_mode)
            self.library_ui = cast(QWidget, window)
            window.showMaximized()
        except (ImportError, ModuleNotFoundError) as e:
            QMessageBox.critical(
                self, "Library Error", f"Could not find the Library module: {str(e)}"
            )
        except RuntimeError as e:
            QMessageBox.critical(self, "Library Error", f"Error initializing the Library: {str(e)}")

    def setup_user_keyboard_selection(self, parent_layout: QLayout) -> None:
        """Set up the user and keyboard selection widgets."""
        # User selection
        user_group = QGroupBox("User & Keyboard Selection")
        user_layout = QFormLayout()

        # User dropdown
        self.user_combo = QComboBox()
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)
        user_layout.addRow("User:", self.user_combo)

        # Keyboard dropdown
        self.keyboard_combo = QComboBox()
        self.keyboard_combo.setEnabled(False)  # Disabled until user is selected
        self.keyboard_combo.currentIndexChanged.connect(self._on_keyboard_changed)
        user_layout.addRow("Keyboard:", self.keyboard_combo)

        # Load users
        self._load_users()
        # After loading users, try to load last used keyboard for the first user
        assert self.user_combo is not None
        if self.user_combo.count() > 0:
            self._load_last_used_keyboard()

        user_group.setLayout(user_layout)
        parent_layout.addWidget(user_group)

    def _load_users(self) -> None:
        """Load all users into the user dropdown."""
        assert self.user_combo is not None
        self.user_combo.clear()
        try:
            users = self.user_manager.list_all_users()
            for user in users:
                display_text = f"{user.first_name} {user.surname} ({user.email_address})"
                self.user_combo.addItem(display_text, user)

            # Select first user by default if available
            if self.user_combo.count() > 0:
                self.user_combo.setCurrentIndex(0)
            else:
                QMessageBox.warning(
                    self, "No Users Found", "Please create a user before starting a typing drill."
                )
        except (AttributeError, TypeError) as e:
            QMessageBox.critical(self, "Data Error", f"Invalid user data format: {str(e)}")
        except ValueError as e:
            QMessageBox.critical(
                self, "Error Loading Users", f"Value error loading users: {str(e)}"
            )
        except IOError as e:
            QMessageBox.critical(self, "Database Error", f"Database access error: {str(e)}")

    def _on_user_changed(self, index: int) -> None:
        """Handle user selection change."""
        assert self.keyboard_combo is not None
        assert self.user_combo is not None
        if index < 0:
            self.current_user = None
            self.keyboard_combo.setEnabled(False)
            self.keyboard_combo.clear()
            return
        # Safely obtain the current user from the combo box
        self.current_user = self.user_combo.currentData()
        if self.current_user and self.current_user.user_id:
            self._load_keyboards_for_user(str(self.current_user.user_id))
        else:
            self.keyboard_combo.setEnabled(False)
            self.keyboard_combo.clear()

    def _on_keyboard_changed(self, index: int) -> None:
        """Handle keyboard selection change."""
        if not self.keyboard_loaded:
            return
        assert self.keyboard_combo is not None
        if index < 0:
            self.current_keyboard = None
            return

        self.current_keyboard = self.keyboard_combo.currentData()

        # Save the last used keyboard setting for this user
        if (
            self.current_user
            and self.current_user.user_id
            and self.current_keyboard
            and self.current_keyboard.keyboard_id
        ):
            try:
                # related_entity_id is user_id, value is keyboard_id
                user_id = str(self.current_user.user_id)
                kbd_id = str(self.current_keyboard.keyboard_id)

                this_setting = Setting(
                    setting_type_id="LSTKBD", setting_value=kbd_id, related_entity_id=user_id
                )
                self.setting_manager.save_setting(this_setting)
            except (ValueError, TypeError) as e:
                # Just log the error but continue - not critical if setting isn't saved
                print(f"Error with setting values: {str(e)}")
            except AttributeError as e:
                print(f"Missing attribute when saving keyboard setting: {str(e)}")
            except IOError as e:
                print(f"Database error when saving keyboard setting: {str(e)}")

    def _load_last_used_keyboard(self) -> None:
        """Load the last used keyboard for the selected user using SettingManager (LSTKBD)."""
        from models.setting_manager import SettingNotFound

        if not self.current_user or not self.current_user.user_id:
            return
        assert self.keyboard_combo is not None
        try:
            # related_entity_id is user_id, value is keyboard_id
            setting = self.setting_manager.get_setting("LSTKBD", str(self.current_user.user_id))
            last_kbd_id = setting.setting_value
            # Try to find this keyboard in the combo
            for i in range(self.keyboard_combo.count()):
                kbd = cast(Optional[Keyboard], self.keyboard_combo.itemData(i))
                if (
                    kbd is not None
                    and getattr(kbd, "keyboard_id", None) is not None
                    and str(kbd.keyboard_id) == last_kbd_id
                ):
                    self.keyboard_combo.setCurrentIndex(i)
                    return
            # If not found, default to first
            if self.keyboard_combo.count() > 0:
                self.keyboard_combo.setCurrentIndex(0)
        except SettingNotFound:
            # No setting, default to first
            if self.keyboard_combo.count() > 0:
                self.keyboard_combo.setCurrentIndex(0)
        except (AttributeError, TypeError) as e:
            # Handle type errors or missing attributes
            print(f"Error accessing keyboard attributes: {str(e)}")
            if self.keyboard_combo.count() > 0:
                self.keyboard_combo.setCurrentIndex(0)
        except IOError as e:
            # Handle database/IO errors
            print(f"Error retrieving keyboard setting from database: {str(e)}")
            if self.keyboard_combo.count() > 0:
                self.keyboard_combo.setCurrentIndex(0)

    def _load_keyboards_for_user(self, user_id: str) -> None:
        """Load keyboards for the selected user and select last used keyboard if available."""
        assert self.keyboard_combo is not None
        self.keyboard_combo.clear()
        self.current_keyboard = None
        self.keyboard_loaded = False
        try:
            keyboards = self.keyboard_manager.list_keyboards_for_user(user_id)
            for keyboard in keyboards:
                self.keyboard_combo.addItem(keyboard.keyboard_name, keyboard)
            has_keyboards = self.keyboard_combo.count() > 0
            self.keyboard_combo.setEnabled(has_keyboards)

            if not has_keyboards:
                QMessageBox.warning(
                    self,
                    "No Keyboards Found",
                    "Please create a keyboard for this user before starting a typing drill.",
                )
            else:
                # Set keyboard_loaded to True BEFORE calling _load_last_used_keyboard
                # so that _on_keyboard_changed will properly set self.current_keyboard
                self.keyboard_loaded = True
                # Try to load last used keyboard for this user
                self._load_last_used_keyboard()
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Keyboards", f"Failed to load keyboards: {str(e)}"
            )
            self.keyboard_combo.setEnabled(False)

    def configure_drill(self) -> None:
        """Open the Drill Configuration dialog with the selected user and keyboard."""
        if not self.current_user or not self.current_user.user_id:
            QMessageBox.warning(
                self, "No User Selected", "Please select a user before starting a typing drill."
            )
            return
        assert self.keyboard_combo is not None
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QMessageBox.warning(
                self,
                "No Keyboard Selected",
                "Please select a keyboard before starting a typing drill.",
            )
            return
        self.current_keyboard = self.keyboard_combo.currentData()
        if not self.current_keyboard or not self.current_keyboard.keyboard_id:
            QMessageBox.warning(
                self,
                "No Keyboard Selected",
                "Please select a keyboard before starting a typing drill.",
            )
            return
        from desktop_ui.drill_config import DrillConfigDialog

        dialog = DrillConfigDialog(
            db_manager=self.db_manager,
            user_id=str(self.current_user.user_id),
            keyboard_id=str(self.current_keyboard.keyboard_id),
        )
        dialog.exec()

    def practice_weak_points(self) -> None:
        """Open the Dynamic N-gram Practice Configuration dialog."""
        if not self.current_user or not self.current_user.user_id:
            QMessageBox.warning(
                self, "No User Selected", "Please select a user before starting practice."
            )
            return
        assert self.keyboard_combo is not None
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QMessageBox.warning(
                self, "No Keyboard Selected", "Please select a keyboard before starting practice."
            )
            return
        self.current_keyboard = self.keyboard_combo.currentData()
        if not self.current_keyboard or not self.current_keyboard.keyboard_id:
            QMessageBox.warning(
                self, "No Keyboard Selected", "Please select a keyboard before starting practice."
            )
            return
        try:
            from desktop_ui.dynamic_config import DynamicConfigDialog

            dialog = DynamicConfigDialog(
                db_manager=self.db_manager,
                user_id=str(self.current_user.user_id),
                keyboard_id=str(self.current_keyboard.keyboard_id),
                parent=self,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not open Practice Weak Points configuration: {str(e)}"
            )

    def open_games_menu(self) -> None:
        """Open the Games Menu dialog."""
        try:
            from desktop_ui.games_menu import GamesMenu

            dialog = GamesMenu(parent=self)
            dialog.exec()
        except ImportError:
            QMessageBox.information(self, "Games Menu", "The Games Menu UI is not yet implemented.")
        except Exception as e:
            QMessageBox.critical(
                self, "Games Menu Error", f"Could not open the Games Menu: {str(e)}"
            )

    def view_last_progress(self) -> None:
        """Open the Last Progress dialog, passing current user_id and keyboard_id."""
        # Validate selections
        if not self.current_user or not self.current_user.user_id:
            QMessageBox.warning(self, "No User Selected", "Please select a user first.")
            return
        assert self.keyboard_combo is not None
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QMessageBox.warning(self, "No Keyboard Selected", "Please select a keyboard first.")
            return
        self.current_keyboard = self.keyboard_combo.currentData()
        if not self.current_keyboard or not self.current_keyboard.keyboard_id:
            QMessageBox.warning(self, "No Keyboard Selected", "Please select a keyboard first.")
            return

        try:
            from desktop_ui.progress_dialog import ProgressDialog

            dialog = ProgressDialog(
                db_manager=self.db_manager,
                user_id=str(self.current_user.user_id),
                keyboard_id=str(self.current_keyboard.keyboard_id),
                parent=self,
            )
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Progress Error", f"Could not open Last Progress: {str(e)}")

    def open_ngram_heatmap(self) -> None:
        """Open the N-gram Speed Heatmap screen with the selected user and keyboard."""
        if not self.current_user or not self.current_user.user_id:
            QMessageBox.warning(
                self, "No User Selected", "Please select a user before viewing the heatmap."
            )
            return
        assert self.keyboard_combo is not None
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QMessageBox.warning(
                self,
                "No Keyboard Selected",
                "Please select a keyboard before viewing the heatmap.",
            )
            return
        self.current_keyboard = self.keyboard_combo.currentData()
        if not self.current_keyboard or not self.current_keyboard.keyboard_id:
            QMessageBox.warning(
                self,
                "No Keyboard Selected",
                "Please select a keyboard before viewing the heatmap.",
            )
            return

        try:
            from desktop_ui.ngram_heatmap_screen import NGramHeatmapDialog

            self.heatmap_dialog = NGramHeatmapDialog(
                db_manager=self.db_manager,
                user=self.current_user,
                keyboard=self.current_keyboard,
                parent=self,
            )
            self.heatmap_dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self, "Heatmap Error", f"Could not open the N-gram Heatmap: {str(e)}"
            )

    def open_keysets(self) -> None:
        """Open the Keysets Editor for the selected keyboard."""
        # Validate selections
        if not self.current_user or not self.current_user.user_id:
            QMessageBox.warning(self, "No User Selected", "Please select a user first.")
            return
        assert self.keyboard_combo is not None
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QMessageBox.warning(self, "No Keyboard Selected", "Please select a keyboard first.")
            return
        self.current_keyboard = self.keyboard_combo.currentData()
        if not self.current_keyboard or not self.current_keyboard.keyboard_id:
            QMessageBox.warning(self, "No Keyboard Selected", "Please select a keyboard first.")
            return
        try:
            from desktop_ui.keysets_dialog import KeysetsDialog

            dlg = KeysetsDialog(
                db_manager=self.db_manager,
                keyboard_id=str(self.current_keyboard.keyboard_id),
                parent=self,
            )
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Keysets Error", f"Could not open Keysets Editor: {str(e)}")

    def data_management(self) -> None:
        """Open the Data Cleanup and Management dialog."""
        try:
            from desktop_ui.cleanup_data_dialog import CleanupDataDialog

            dialog = CleanupDataDialog(
                parent=self,
                db_path=self.db_manager.db_path,
                connection_type=self.db_manager.connection_type,
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Data Management Error", f"Could not open Data Management dialog: {str(e)}"
            )

    def reset_sessions(self) -> None:
        """Reset all session data after user confirmation.

        The following tables will be cleared:
        - practice_sessions
        - session_keystrokes
        - session_ngram_speed
        - session_ngram_errors
        """
        # Create confirmation dialog
        confirm = QMessageBox.question(
            self,
            "Reset Session Details",
            "This will remove all session details - are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,  # Default is No
        )
        # If user cancels, just return to main menu
        if confirm == QMessageBox.StandardButton.No:
            return
        # If user confirms, proceed with deletion
        try:
            from models.session_manager import SessionManager

            session_manager = SessionManager(self.db_manager)
            success = session_manager.delete_all()
            if success:
                QMessageBox.information(
                    self, "Success", "All session data has been successfully removed."
                )
            else:
                QMessageBox.warning(
                    self, "Warning", "Some errors occurred while removing session data."
                )
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"An error occurred while removing session data: {str(e)}"
            )

    def open_db_content_viewer(self) -> None:
        """Open the Database Viewer dialog, using the DatabaseViewerService."""
        try:
            from desktop_ui.db_viewer_dialog import DatabaseViewerDialog
            from services.database_viewer_service import DatabaseViewerService

            service = DatabaseViewerService(self.db_manager)
            dialog = DatabaseViewerDialog(service, parent=self)
            dialog.exec()
        except ImportError:
            QMessageBox.information(
                self,
                "DB Viewer",
                "The Database Viewer UI is not yet implemented. "
                "API and Service layers are available.",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "DB Viewer Error", f"Could not open the Database Viewer: {str(e)}"
            )

    def open_sql_query_screen(self) -> None:
        """Open the SQL Query Screen dialog, passing user_id and keyboard_id."""
        try:
            from desktop_ui.query_screen import QueryScreen

            # Get current user and keyboard IDs
            user_id = None
            keyboard_id = None
            if self.current_user:
                user_id = str(self.current_user.user_id)
            if self.current_keyboard:
                keyboard_id = str(self.current_keyboard.keyboard_id)

            dialog = QueryScreen(
                db_manager=self.db_manager, user_id=user_id, keyboard_id=keyboard_id, parent=self
            )
            dialog.exec()
        except ImportError:
            QMessageBox.information(
                self, "SQL Query", "The SQL Query Screen UI is not yet implemented."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "SQL Query Error", f"Could not open the SQL Query Screen: {str(e)}"
            )

    def manage_users_keyboards(self) -> None:
        """Open the Users and Keyboards management dialog and refresh dropdowns when closed."""
        try:
            dialog = UsersAndKeyboards(db_manager=self.db_manager, parent=self)
            # Save current selections
            current_user = self.current_user

            # Show the dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Reload users and keyboards
                self._load_users()

                # Try to restore previous selections if they still exist
                assert self.user_combo is not None
                if current_user:
                    for i in range(self.user_combo.count()):
                        user = cast(Optional[User], self.user_combo.itemData(i))
                        if user is not None and user.user_id == current_user.user_id:
                            self.user_combo.setCurrentIndex(i)
                            break
                else:
                    # If previous user not found, select first user if available
                    if self.user_combo.count() > 0:
                        self.user_combo.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to open Users & Keyboards manager: {str(e)}"
            )

    def quit_app(self) -> None:
        """Quit the application."""
        QApplication.quit()


def launch_main_menu(
    testing_mode: bool = False, use_cloud: bool = True, debug_mode: str = "loud"
) -> None:
    """Launch the main menu application window.

    Args:
        testing_mode: Whether to run in testing mode
        use_cloud: Whether to use cloud Aurora connection (True) or local SQLite (False)
        debug_mode: Debug output mode - "loud" for all debug messages, "quiet" to suppress them
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.LOCAL
    main_menu = MainMenu(
        testing_mode=testing_mode, connection_type=connection_type, debug_mode=debug_mode
    )
    main_menu.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Parse command line arguments for debug mode
    # Default to "quiet" unless "loud" is explicitly passed
    debug_mode = "quiet"  # Default to quiet

    print("Arguments", sys.argv)
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.lower() == "loud":
                debug_mode = "loud"
                break
            elif arg.lower() == "quiet":
                debug_mode = "quiet"
                break
    print("Debug mode", debug_mode)

    launch_main_menu(debug_mode=debug_mode)
