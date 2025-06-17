import os
import sys
import warnings
from typing import Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt5 import QtCore, QtWidgets

from db.database_manager import DatabaseManager
from desktop_ui.users_and_keyboards import UsersAndKeyboards
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.user import User
from models.user_manager import UserManager

warnings.filterwarnings("ignore", message="sipPyTypeDict() is deprecated")


class MainMenu(QtWidgets.QWidget):
    """
    Modern Main Menu UI for AI Typing Trainer (PyQt5).

    - Uses Fusion style, Segoe UI font, and modern color palette
    - Initiates a single DatabaseManager connection to typing_data.db
    - Passes the open database connection to the Library window
    - Testable: supports dependency injection and testing_mode
    """

    def __init__(self, db_path: str = None, testing_mode: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("AI Typing Trainer")
        self.resize(600, 600)
        self.testing_mode = testing_mode
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.init_tables()  # Ensure all tables are created/initialized
        
        # Initialize managers
        self.user_manager = UserManager(self.db_manager)
        self.keyboard_manager = KeyboardManager(self.db_manager)
        
        # Store current selections
        self.current_user: Optional[User] = None
        self.current_keyboard: Optional[Keyboard] = None
        
        self.center_on_screen()
        self.setup_ui()

    def center_on_screen(self) -> None:
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()
        header = QtWidgets.QLabel("AI Typing Trainer")
        header.setAlignment(QtCore.Qt.AlignCenter)
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
            ("View Progress Over Time", self.view_progress),
            ("Data Management", self.data_management),
            ("View DB Content", self.open_db_content_viewer),
            ("Manage Users & Keyboards", self.manage_users_keyboards),
            ("Reset Session Details", self.reset_sessions),
            ("Quit Application", self.quit_app),
        ]
        self.buttons = []
        for text, slot in button_data:
            btn = QtWidgets.QPushButton(text)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(self.button_stylesheet(normal=True))
            btn.clicked.connect(slot)
            btn.installEventFilter(self)
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()
        self.setLayout(layout)

    def button_stylesheet(self, normal: bool = True) -> str:
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

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(obj, QtWidgets.QPushButton):
            if event.type() == QtCore.QEvent.Enter:
                obj.setStyleSheet(self.button_stylesheet(normal=False))
            elif event.type() == QtCore.QEvent.Leave:
                obj.setStyleSheet(self.button_stylesheet(normal=True))
        return super().eventFilter(obj, event)

    # Placeholder slots for button actions
    def open_library(self) -> None:
        """
        Open the Snippets Library main window, passing the existing DatabaseManager.
        """
        try:
            from desktop_ui.library_main import LibraryMainWindow

            self.library_ui = LibraryMainWindow(
                db_manager=self.db_manager, testing_mode=self.testing_mode
            )
            self.library_ui.showMaximized()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Library Error", f"Could not open the Snippets Library: {str(e)}"
            )

    def setup_user_keyboard_selection(self, parent_layout: QtWidgets.QLayout) -> None:
        """
        Set up the user and keyboard selection widgets.
        """
        # User selection
        user_group = QtWidgets.QGroupBox("User & Keyboard Selection")
        user_layout = QtWidgets.QFormLayout()
        
        # User dropdown
        self.user_combo = QtWidgets.QComboBox()
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)
        user_layout.addRow("User:", self.user_combo)
        
        # Keyboard dropdown
        self.keyboard_combo = QtWidgets.QComboBox()
        self.keyboard_combo.setEnabled(False)  # Disabled until user is selected
        user_layout.addRow("Keyboard:", self.keyboard_combo)
        
        # Load users
        self._load_users()
        
        user_group.setLayout(user_layout)
        parent_layout.addWidget(user_group)
    
    def _load_users(self) -> None:
        """Load all users into the user dropdown."""
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
                QtWidgets.QMessageBox.warning(
                    self, 
                    "No Users Found", 
                    "Please create a user before starting a typing drill."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Error Loading Users", 
                f"Failed to load users: {str(e)}"
            )
    
    def _on_user_changed(self, index: int) -> None:
        """Handle user selection change."""
        if index < 0:
            self.current_user = None
            self.keyboard_combo.setEnabled(False)
            self.keyboard_combo.clear()
            return
            
        self.current_user = self.user_combo.currentData()
        self._load_keyboards_for_user(self.current_user.user_id)
    
    def _load_keyboards_for_user(self, user_id: str) -> None:
        """Load keyboards for the selected user."""
        self.keyboard_combo.clear()
        self.current_keyboard = None
        
        try:
            keyboards = self.keyboard_manager.list_keyboards_for_user(user_id)
            for keyboard in keyboards:
                self.keyboard_combo.addItem(keyboard.keyboard_name, keyboard)
            
            # Enable keyboard selection if we have keyboards
            has_keyboards = self.keyboard_combo.count() > 0
            self.keyboard_combo.setEnabled(has_keyboards)
            
            if not has_keyboards:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Keyboards Found",
                    "Please create a keyboard for this user before starting a typing drill."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error Loading Keyboards",
                f"Failed to load keyboards: {str(e)}"
            )
            self.keyboard_combo.setEnabled(False)
    
    def configure_drill(self) -> None:
        """
        Open the Drill Configuration dialog with the selected user and keyboard.
        """
        if not self.current_user:
            QtWidgets.QMessageBox.warning(
                self, 
                "No User Selected", 
                "Please select a user before starting a typing drill."
            )
            return
            
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QtWidgets.QMessageBox.warning(
                self,
                "No Keyboard Selected",
                "Please select a keyboard before starting a typing drill."
            )
            return
            
        self.current_keyboard = self.keyboard_combo.currentData()
        
        from desktop_ui.drill_config import DrillConfigDialog

        dialog = DrillConfigDialog(
            db_manager=self.db_manager,
            user_id=self.current_user.user_id,
            keyboard_id=self.current_keyboard.keyboard_id
        )
        dialog.exec_()

    def practice_weak_points(self) -> None:
        """Open the Dynamic N-gram Practice Configuration dialog."""
        if not self.current_user:
            QtWidgets.QMessageBox.warning(
                self, 
                "No User Selected", 
                "Please select a user before starting practice."
            )
            return
            
        if not self.keyboard_combo.isEnabled() or self.keyboard_combo.currentIndex() < 0:
            QtWidgets.QMessageBox.warning(
                self,
                "No Keyboard Selected",
                "Please select a keyboard before starting practice."
            )
            return
            
        self.current_keyboard = self.keyboard_combo.currentData()
        
        try:
            from desktop_ui.dynamic_config import DynamicConfigDialog

            dialog = DynamicConfigDialog(
                db_manager=self.db_manager,
                user_id=self.current_user.user_id,
                keyboard_id=self.current_keyboard.keyboard_id,
                parent=self
            )
            dialog.exec_()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Could not open Practice Weak Points configuration: {str(e)}"
            )

    def view_progress(self) -> None:
        QtWidgets.QMessageBox.information(
            self, "Progress", "View Progress Over Time - Not yet implemented."
        )

    def data_management(self) -> None:
        QtWidgets.QMessageBox.information(
            self, "Data Management", "Data Management - Not yet implemented."
        )

    def reset_sessions(self) -> None:
        """
        Reset all session data after user confirmation.
        The following tables will be cleared:
        - practice_sessions
        - session_keystrokes
        - session_ngram_speed
        - session_ngram_errors
        """
        # Create confirmation dialog
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Reset Session Details",
            "This will remove all session details - are you sure?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,  # Default is No
        )
        # If user cancels, just return to main menu
        if confirm == QtWidgets.QMessageBox.StandardButton.No:
            return
        # If user confirms, proceed with deletion
        try:
            from models.session_manager import SessionManager

            session_manager = SessionManager(self.db_manager)
            success = session_manager.delete_all()
            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", "All session data has been successfully removed."
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Warning", "Some errors occurred while removing session data."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"An error occurred while removing session data: {str(e)}"
            )

    def open_db_content_viewer(self) -> None:
        """
        Open the Database Viewer dialog, using the DatabaseViewerService.
        """
        try:
            from desktop_ui.db_viewer_dialog import DatabaseViewerDialog
            from services.database_viewer_service import DatabaseViewerService

            service = DatabaseViewerService(self.db_manager)
            dialog = DatabaseViewerDialog(service, parent=self)
            dialog.exec_()
        except ImportError:
            QtWidgets.QMessageBox.information(
                self,
                "DB Viewer",
                "The Database Viewer UI is not yet implemented. "
                "API and Service layers are available.",
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "DB Viewer Error", f"Could not open the Database Viewer: {str(e)}"
            )

    def manage_users_keyboards(self) -> None:
        """Open the Users and Keyboards management dialog and refresh dropdowns when closed."""
        try:
            dialog = UsersAndKeyboards(db_manager=self.db_manager, parent=self)
            # Save current selections
            current_user = self.current_user
            current_keyboard = self.current_keyboard
            
            # Show the dialog
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                # Reload users and keyboards
                self._load_users()
                
                # Try to restore previous selections if they still exist
                if current_user:
                    for i in range(self.user_combo.count()):
                        user = self.user_combo.itemData(i)
                        if user and user.user_id == current_user.user_id:
                            self.user_combo.setCurrentIndex(i)
                            break
                    else:
                        # If previous user not found, select first user if available
                        if self.user_combo.count() > 0:
                            self.user_combo.setCurrentIndex(0)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to open Users & Keyboards manager: {str(e)}"
            )

    def quit_app(self) -> None:
        """Quit the application."""
        QtWidgets.QApplication.quit()


def launch_main_menu(testing_mode: bool = False) -> None:
    """
    Launch the main menu application window.
    """
    app = QtWidgets.QApplication(sys.argv)
    window = MainMenu(testing_mode=testing_mode)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    launch_main_menu()
