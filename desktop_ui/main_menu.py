"""
Main Menu UI for AI Typing Trainer (PyQt5)

This module provides the native PyQt5 UI for the AI Typing Trainer main menu.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PyQt5 import QtCore, QtWidgets

from db.database_manager import DatabaseManager


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
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "typing_data.db"
            )
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.init_tables()  # Ensure all tables are created/initialized
        self.center_on_screen()
        self.setup_ui()

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        header = QtWidgets.QLabel("AI Typing Trainer")
        header.setAlignment(QtCore.Qt.AlignCenter)
        font = header.font()
        font.setPointSize(18)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        button_data = [
            ("Manage Your Library of Text", self.open_library),
            ("Do a Typing Drill", self.configure_drill),
            ("Practice Weak Points", self.practice_weak_points),
            ("View Progress Over Time", self.view_progress),
            ("Data Management", self.data_management),
            ("View DB Content", self.open_db_content_viewer),
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

    def button_stylesheet(self, normal=True):
        if normal:
            return (
                "QPushButton { background-color: #0d6efd; color: white; border-radius: 5px; font-size: 14px; }"
                "QPushButton:pressed { background-color: #0b5ed7; }"
            )
        else:
            return "QPushButton { background-color: #f0f0f0; color: black; border-radius: 5px; font-size: 14px; }"

    def eventFilter(self, obj, event):
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

    def configure_drill(self):
        """
        Open the Drill Configuration dialog, passing the existing DatabaseManager.
        """
        from desktop_ui.drill_config import DrillConfigDialog

        dialog = DrillConfigDialog(db_manager=self.db_manager)
        dialog.exec_()

    def practice_weak_points(self) -> None:
        """Open the Dynamic N-gram Practice Configuration dialog."""
        try:
            from desktop_ui.dynamic_config import DynamicConfigDialog
            
            dialog = DynamicConfigDialog(db_manager=self.db_manager, parent=self)
            dialog.exec_()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Could not open Practice Weak Points configuration: {str(e)}"
            )

    def view_progress(self):
        QtWidgets.QMessageBox.information(
            self, "Progress", "View Progress Over Time - Not yet implemented."
        )

    def data_management(self):
        QtWidgets.QMessageBox.information(
            self, "Data Management", "Data Management - Not yet implemented."
        )
        
    def reset_sessions(self):
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
            QtWidgets.QMessageBox.StandardButton.No  # Default is No
        )
        
        # If user cancels, just return to main menu
        if confirm == QtWidgets.QMessageBox.StandardButton.No:
            return
            
        # If user confirms, proceed with deletion
        try:
            from models.practice_session import PracticeSessionManager
            
            # Create session manager
            session_manager = PracticeSessionManager(self.db_manager)
            
            # Clear all session data
            success = session_manager.clear_all_session_data()
            
            if success:
                QtWidgets.QMessageBox.information(
                    self,
                    "Success",
                    "All session data has been successfully removed."
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "Some errors occurred while removing session data."
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while removing session data: {str(e)}"
            )

    def open_db_content_viewer(self):
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
                self, "DB Viewer", "The Database Viewer UI is not yet implemented. API and Service layers are available."
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "DB Viewer Error", f"Could not open the Database Viewer: {str(e)}"
            )

    # The real reset_sessions method is already implemented above

    def quit_app(self):
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
