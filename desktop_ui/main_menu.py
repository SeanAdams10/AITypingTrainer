"""
Main Menu UI for AI Typing Trainer (PyQt5)

This module provides the native PyQt5 UI for the AI Typing Trainer main menu.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5 import QtWidgets, QtCore, QtGui
from db.database_manager import DatabaseManager
from db.table_operations import TableOperations

class MainMenu(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Typing Trainer")
        self.resize(600, 600)  # 100px taller than before
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
            return (
                "QPushButton { background-color: #f0f0f0; color: black; border-radius: 5px; font-size: 14px; }"
            )

    def eventFilter(self, obj, event):
        if isinstance(obj, QtWidgets.QPushButton):
            if event.type() == QtCore.QEvent.Enter:
                obj.setStyleSheet(self.button_stylesheet(normal=False))
            elif event.type() == QtCore.QEvent.Leave:
                obj.setStyleSheet(self.button_stylesheet(normal=True))
        return super().eventFilter(obj, event)

    # Placeholder slots for button actions
    def open_library(self):
        from desktop_ui.library_manager import LibraryManagerUI
        try:
            from desktop_ui.library_service import LibraryService
            service = LibraryService()
        except Exception as e:
            # Fallback to stub service if API service fails
            print(f"Warning: Could not initialize API service: {e}")
            from collections import namedtuple
            # Simple stub service for fallback
            class LibraryService:
                def get_categories(self):
                    Category = namedtuple('Category', ['category_id', 'name'])
                    return [Category(1, "Sample Category")]
                def get_snippets(self, category_id):
                    Snippet = namedtuple('Snippet', ['snippet_id', 'name'])
                    return [Snippet(1, "Sample Snippet")]
            service = LibraryService()
        self.library_ui = LibraryManagerUI(service)
        self.library_ui.show()

    def configure_drill(self):
        from desktop_ui.drill_config import DrillConfigDialog
        # Ensure we pass a backend/service object that implements get_categories
        # Replace 'self.service' with the actual service instance if named differently
        dialog = DrillConfigDialog(service=self.service if hasattr(self, 'service') else None)
        dialog.exec_()

    def practice_weak_points(self):
        QtWidgets.QMessageBox.information(self, "Practice Weak Points", "Practice Weak Points - Not yet implemented.")

    def view_progress(self):
        QtWidgets.QMessageBox.information(self, "Progress", "View Progress Over Time - Not yet implemented.")

    def data_management(self):
        QtWidgets.QMessageBox.information(self, "Data Management", "Data Management - Not yet implemented.")

    def open_db_content_viewer(self):
        QtWidgets.QMessageBox.information(self, "DB Content", "View DB Content - Not yet implemented.")

    def reset_sessions(self):
        QtWidgets.QMessageBox.information(self, "Reset Sessions", "Reset Session Details - Not yet implemented.")

    def quit_app(self):
        QtWidgets.QApplication.quit()

def launch_main_menu():
    app = QtWidgets.QApplication(sys.argv)
    window = MainMenu()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    launch_main_menu()
