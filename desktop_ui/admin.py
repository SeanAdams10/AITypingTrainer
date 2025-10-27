"""Admin UI for AI Typing Trainer.

Administrative interface using PySide6 with limited functionality for data management,
database queries, content viewing, and user/keyboard management.
"""

import os
import sys
import warnings
from typing import Optional

# Ensure project root is in sys.path before any project imports
# isort: off
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# isort: on

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
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


class AdminUI(QWidget):
    """Administrative UI for AI Typing Trainer (PySide6).

    Limited interface for administrative tasks:
    - Data management
    - Database queries
    - Database content viewing
    - User and keyboard management
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        testing_mode: bool = False,
        connection_type: ConnectionType = ConnectionType.CLOUD,
        debug_mode: str = "loud",
    ) -> None:
        """Initialize the AdminUI with database configuration and options.

        Args:
            db_path: Path to the database file
            testing_mode: Whether running in test mode
            connection_type: Type of database connection to use
            debug_mode: Debug output level
        """
        super().__init__()
        self.setWindowTitle("AI Typing Trainer - Admin")
        self.resize(500, 400)
        self.testing_mode = testing_mode

        # Set debug mode and create DebugUtil instance
        if debug_mode.lower() not in ["loud", "quiet"]:
            debug_mode = "loud"  # Default to loud if invalid value provided
        os.environ["AI_TYPING_TRAINER_DEBUG_MODE"] = debug_mode.lower()

        # Create DebugUtil instance
        self.debug_util = DebugUtil()
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "typing_data.db"
            )
        self.db_manager = DatabaseManager(
            connection_type=connection_type, debug_util=self.debug_util
        )
        self.db_manager.init_tables()  # Ensure all tables are created/initialized

        # Initialize managers
        self.user_manager = UserManager(db_manager=self.db_manager)
        self.keyboard_manager = KeyboardManager(db_manager=self.db_manager)

        # Initialize attributes that will be set later
        self.user_combo: Optional[QComboBox] = None
        self.keyboard_combo: Optional[QComboBox] = None

        # Store current selections
        self.current_user: Optional[User] = None
        self.current_keyboard: Optional[Keyboard] = None
        self.setting_manager = SettingManager(db_manager=self.db_manager)
        self.keyboard_loaded = False

        self.center_on_screen()
        self.setup_ui()

    def center_on_screen(self) -> None:
        """Center the window on the screen."""
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()
            size = self.geometry()
            x = (
                screen_geometry.x() + (screen_geometry.width() - size.width()) // 2
            )
            y = (
                screen_geometry.y() + (screen_geometry.height() - size.height()) // 2
            )
            self.move(x, y)

    def setup_ui(self) -> None:
        """Set up the main user interface components."""
        layout = QVBoxLayout()
        header = QLabel("AI Typing Trainer - Admin")
        # Use correct alignment flag for PySide6
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = header.font()
        font.setPointSize(18)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        # Add user and keyboard selection
        self.setup_user_keyboard_selection(parent_layout=layout)

        # Admin-specific buttons only
        button_data = [
            ("Data Management", self.data_management),
            ("Query the Database", self.open_sql_query_screen),
            ("View Database Content", self.open_db_content_viewer),
            ("Manage Users & Keyboards", self.manage_users_keyboards),
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

    def button_stylesheet(self, *, normal: bool = True) -> str:
        """Return CSS stylesheet for button styling."""
        if normal:
            return (
                "QPushButton { background-color: #dc3545; color: white; "
                "border-radius: 5px; font-size: 14px; }"
                "QPushButton:pressed { background-color: #c82333; }"
            )
        else:
            return (
                "QPushButton { background-color: #f0f0f0; color: black; "
                "border-radius: 5px; font-size: 14px; }"
            )

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle mouse events for button hover effects."""
        if isinstance(obj, QPushButton):
            if event.type() == QEvent.Type.Enter:
                obj.setStyleSheet(self.button_stylesheet(normal=False))
            elif event.type() == QEvent.Type.Leave:
                obj.setStyleSheet(self.button_stylesheet(normal=True))
        return super().eventFilter(obj, event)

    def setup_user_keyboard_selection(self, *, parent_layout: QLayout) -> None:
        """Set up the user and keyboard selection widgets."""
        # User selection
        user_group = QGroupBox("User & Keyboard Selection")
        user_layout = QFormLayout()

        # User dropdown
        self.user_combo = QComboBox()
        self.user_combo.currentIndexChanged.connect(lambda idx: self._on_user_changed(index=idx))
        user_layout.addRow("User:", self.user_combo)

        # Keyboard dropdown
        self.keyboard_combo = QComboBox()
        self.keyboard_combo.setEnabled(False)  # Disabled until user is selected
        self.keyboard_combo.currentIndexChanged.connect(
            lambda idx: self._on_keyboard_changed(index=idx)
        )
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
                self.user_combo.addItem(user.first_name, user)

            # Select first user by default if available
            if self.user_combo.count() > 0:
                self._on_user_changed(index=0)
            else:
                self.current_user = None
        except (AttributeError, TypeError) as e:
            QMessageBox.critical(
                self, "Data Error", f"Invalid user data format: {str(e)}"
            )
        except ValueError as e:
            QMessageBox.critical(
                self, "Error Loading Users", f"Value error loading users: {str(e)}"
            )
        except IOError as e:
            QMessageBox.critical(
                self, "Database Error", f"Database access error: {str(e)}"
            )

    def _on_user_changed(self, *, index: int) -> None:
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
            self._load_keyboards_for_user(user_id=str(self.current_user.user_id))
        else:
            self.keyboard_combo.setEnabled(False)
            self.keyboard_combo.clear()

    def _on_keyboard_changed(self, *, index: int) -> None:
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
                setting = Setting(
                    setting_type_id="LSTKBD",
                    setting_value=str(self.current_keyboard.keyboard_id),
                    related_entity_id=str(self.current_user.user_id),
                )
                self.setting_manager.save_setting(setting=setting)
            except (ValueError, TypeError) as e:
                QMessageBox.warning(
                    self,
                    "Setting Error",
                    f"Could not save keyboard preference: {str(e)}",
                )
            except AttributeError as e:
                QMessageBox.warning(
                    self, "Setting Error", f"Setting manager error: {str(e)}"
                )
            except IOError as e:
                QMessageBox.critical(
                    self, "Database Error", f"Could not save to database: {str(e)}"
                )

    def _load_last_used_keyboard(self) -> None:
        """Load the last used keyboard for the selected user using SettingManager (LSTKBD)."""
        from models.setting_manager import SettingNotFound

        if not self.current_user or not self.current_user.user_id:
            return
        assert self.keyboard_combo is not None
        try:
            # related_entity_id is user_id, value is keyboard_id
            last_keyboard_setting = self.setting_manager.get_setting(
                "LSTKBD", str(self.current_user.user_id)
            )
            last_keyboard_id = last_keyboard_setting.setting_value
            # Find and select this keyboard in the combo box
            for i in range(self.keyboard_combo.count()):
                kb = self.keyboard_combo.itemData(i)
                if kb and str(kb.keyboard_id) == last_keyboard_id:
                    self.keyboard_combo.setCurrentIndex(i)
                    break
        except SettingNotFound:
            pass  # No last keyboard saved, use default (first in list)
        except (AttributeError, TypeError) as e:
            QMessageBox.warning(
                self, "Setting Error", f"Error loading last keyboard: {str(e)}"
            )
        except IOError as e:
            QMessageBox.critical(
                self, "Database Error", f"Database error loading settings: {str(e)}"
            )

    def _load_keyboards_for_user(self, *, user_id: str) -> None:
        """Load keyboards for the selected user and select last used keyboard if available."""
        assert self.keyboard_combo is not None
        self.keyboard_combo.clear()
        self.current_keyboard = None
        self.keyboard_loaded = False
        try:
            keyboards = self.keyboard_manager.list_keyboards_for_user(user_id=user_id)
            for keyboard in keyboards:
                self.keyboard_combo.addItem(keyboard.keyboard_name, keyboard)

            if self.keyboard_combo.count() > 0:
                self.keyboard_combo.setEnabled(True)
                self.keyboard_loaded = True
                self._load_last_used_keyboard()
            else:
                self.keyboard_combo.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load keyboards: {str(e)}")

    def data_management(self) -> None:
        """Open the Data Cleanup and Management dialog."""
        try:
            from desktop_ui.cleanup_data_dialog import CleanupDataDialog

            dialog = CleanupDataDialog(db_manager=self.db_manager, parent=self)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Data Management Error",
                f"Could not open data management dialog: {str(e)}",
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
            QMessageBox.critical(self, "Import Error", "Database viewer module not found.")
        except Exception as e:
            QMessageBox.critical(
                self, "Database Viewer Error", f"Error opening database viewer: {str(e)}"
            )

    def open_sql_query_screen(self) -> None:
        """Open the SQL Query Screen dialog, passing user_id and keyboard_id."""
        try:
            from desktop_ui.query_screen import QueryScreen

            user_id = str(self.current_user.user_id) if self.current_user else ""
            keyboard_id = str(self.current_keyboard.keyboard_id) if self.current_keyboard else ""
            dialog = QueryScreen(
                db_manager=self.db_manager, user_id=user_id, keyboard_id=keyboard_id
            )
            dialog.exec()
        except ImportError:
            QMessageBox.critical(self, "Import Error", "Query screen module not found.")
        except Exception as e:
            QMessageBox.critical(
                self, "Query Screen Error", f"Error opening query screen: {str(e)}"
            )

    def manage_users_keyboards(self) -> None:
        """Open the Users and Keyboards management dialog and refresh dropdowns when closed."""
        try:
            dialog = UsersAndKeyboards(self.db_manager)
            dialog.exec()
            # Refresh the dropdowns after dialog closes
            self._load_users()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Management Error",
                f"Error opening user/keyboard management: {str(e)}",
            )

    def quit_app(self) -> None:
        """Quit the application."""
        QApplication.quit()


def launch_admin_ui(
    testing_mode: bool = False,
    use_cloud: bool = True,
    debug_mode: str = "loud",
) -> None:
    """Launch the admin UI application window.

    Args:
        testing_mode: Whether to run in testing mode.
        use_cloud: Whether to use cloud Aurora connection (True) or local SQLite (False).
        debug_mode: Debug output mode - "loud" for all debug messages, "quiet" to suppress.
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    connection_type = ConnectionType.CLOUD if use_cloud else ConnectionType.POSTGRESS_DOCKER
    admin_ui = AdminUI(
        testing_mode=testing_mode,
        connection_type=connection_type,
        debug_mode=debug_mode,
    )
    admin_ui.show()
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
    print("Debug mode", debug_mode)

    launch_admin_ui(debug_mode=debug_mode)
