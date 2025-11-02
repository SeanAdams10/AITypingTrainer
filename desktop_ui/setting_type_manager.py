"""PySide6 Desktop UI for Setting Type Management.

Provides a modern UI for managing setting type definitions with full CRUD operations.
Follows UI standards from MemoriesAndRules/ui_standards.md.
"""

import sys
import uuid
from typing import Optional

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from db.database_manager import DatabaseManager
from models.setting_type import SettingType, SettingTypeValidationError
from models.setting_type_manager import SettingTypeManager

from .setting_type_dialogs import SettingTypeDialog


class SettingTypeManagerWindow(QDialog):
    """Modern UI for managing setting type definitions.
    
    Implements CRUD operations for setting types with validation and filtering.
    Follows Windows 11-style modern design patterns.
    Can be used as standalone window or as a dialog within another application.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        testing_mode: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the Setting Type Manager window.
        
        Args:
            db_manager: Optional DatabaseManager instance for dependency injection
            testing_mode: If True, suppress modal dialogs for automated testing
            parent: Optional parent widget (for dialog mode)
        """
        super().__init__(parent)
        self.testing_mode = testing_mode
        self.setWindowTitle("Setting Type Manager")
        if parent is None:
            # Standalone mode - maximize
            self.showMaximized()
        self.setMinimumSize(900, 600)
        
        # Database setup
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            # For standalone mode, create a database connection
            # This should be replaced with proper connection parameters
            self.db_manager = DatabaseManager(
                host="localhost",
                port=5432,
                database="typing_demo",
                username="postgres",
                password="postgres",
            )
        
        # Initialize setting type manager
        self.setting_type_manager = SettingTypeManager(db_manager=self.db_manager)
        
        # User ID for operations (should come from auth system)
        self.current_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        
        # Data
        self.setting_types: list[SettingType] = []
        self.selected_setting_type: Optional[SettingType] = None
        self.current_entity_filter: Optional[str] = None
        
        # UI setup
        self.setup_ui()
        self.load_data()

    def setup_ui(self) -> None:
        """Set up the user interface components."""
        QApplication.setStyle("Fusion")
        font = QFont("Segoe UI", 11)
        self.setFont(font)
        self.setStyleSheet(_modern_qss())
        
        # Main layout (QDialog doesn't use setCentralWidget)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        # Header with title and filters
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Setting Types")
        title_label.setObjectName("PanelTitle")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Entity type filter
        entity_label = QLabel("Entity Type:")
        entity_label.setStyleSheet("font-size: 14px; color: #3a3a3a;")
        header_layout.addWidget(entity_label)
        
        self.entity_filter = QComboBox()
        self.entity_filter.addItems(["All", "user", "keyboard", "global"])
        self.entity_filter.setMinimumWidth(120)
        self.entity_filter.currentTextChanged.connect(self._on_entity_filter_changed)
        header_layout.addWidget(self.entity_filter)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search setting types...")
        self.search_input.setObjectName("SearchBar")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self.filter_setting_types)
        header_layout.addWidget(self.search_input)
        
        self.main_layout.addLayout(header_layout)
        
        # Setting types list
        self.settingTypeList = QListWidget()
        self.settingTypeList.setObjectName("SettingTypeList")
        self.settingTypeList.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.settingTypeList.itemSelectionChanged.connect(
            self.on_selection_changed
        )
        self.settingTypeList.itemDoubleClicked.connect(self.edit_setting_type)
        self.main_layout.addWidget(self.settingTypeList)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.addBtn = QPushButton("Add Setting Type")
        self.addBtn.setMinimumHeight(40)
        self.addBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.addBtn.setStyleSheet(
            "font-size: 15px; font-weight: 500; min-width: 150px;"
        )
        self.addBtn.clicked.connect(self.add_setting_type)
        button_layout.addWidget(self.addBtn)
        
        self.editBtn = QPushButton("Edit")
        self.editBtn.setMinimumHeight(40)
        self.editBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.editBtn.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.editBtn.setEnabled(False)
        self.editBtn.clicked.connect(self.edit_setting_type)
        button_layout.addWidget(self.editBtn)
        
        self.delBtn = QPushButton("Delete")
        self.delBtn.setMinimumHeight(40)
        self.delBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delBtn.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.delBtn.setEnabled(False)
        self.delBtn.clicked.connect(self.delete_setting_type)
        button_layout.addWidget(self.delBtn)
        
        button_layout.addStretch()
        
        self.main_layout.addLayout(button_layout)
        
        # Status bar
        self.status = QLabel("")
        self.status.setObjectName("StatusBar")
        self.status.setMinimumHeight(32)
        self.status.setStyleSheet("font-size: 13px; color: #3a3a3a;")
        self.main_layout.addWidget(self.status)

    def load_data(self) -> None:
        """Load setting types from database into the UI."""
        try:
            entity_type = self.current_entity_filter
            self.setting_types = self.setting_type_manager.list_setting_types(
                entity_type=entity_type,
                active_only=True,
            )
            self.refresh_list()
            self.show_info(f"Loaded {len(self.setting_types)} setting types")
        except Exception as e:
            self.show_error(f"Error loading setting types: {e}")

    def refresh_list(self) -> None:
        """Refresh the setting type list widget from current data."""
        self.settingTypeList.clear()
        search_text = self.search_input.text().lower()
        
        for setting_type in self.setting_types:
            # Apply search filter
            if search_text and search_text not in setting_type.setting_type_name.lower():
                continue
            
            item = QListWidgetItem(setting_type.setting_type_name)
            item.setData(Qt.ItemDataRole.UserRole, setting_type)
            
            # Visual indicator for system setting types
            if setting_type.is_system:
                item.setToolTip("System setting type (cannot be deleted)")
                item.setForeground(Qt.GlobalColor.darkGray)
            
            self.settingTypeList.addItem(item)

    def filter_setting_types(self, search_text: str) -> None:
        """Filter the setting type list by search text.
        
        Args:
            search_text: Text to filter by (case-insensitive)
        """
        self.refresh_list()

    def filter_by_entity_type(self, entity_type: str) -> None:
        """Filter setting types by entity type.
        
        Args:
            entity_type: Entity type to filter by (user/keyboard/global)
        """
        if entity_type == "All":
            self.current_entity_filter = None
        else:
            self.current_entity_filter = entity_type
        self.load_data()

    def _on_entity_filter_changed(self, text: str) -> None:
        """Handle entity type filter changes."""
        self.filter_by_entity_type(text)

    def on_selection_changed(self) -> None:
        """Handle selection changes in the list."""
        items = self.settingTypeList.selectedItems()
        if not items:
            self.selected_setting_type = None
            self.editBtn.setEnabled(False)
            self.delBtn.setEnabled(False)
            return
        
        item = items[0]
        self.selected_setting_type = item.data(Qt.ItemDataRole.UserRole)
        self.editBtn.setEnabled(True)
        self.delBtn.setEnabled(True)

    def add_setting_type(self) -> None:
        """Open dialog to create a new setting type."""
        dlg = SettingTypeDialog(parent=self)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                setting_type = dlg.get_setting_type()
                self.setting_type_manager.create_setting_type(
                    setting_type=setting_type,
                    user_id=self.current_user_id,
                )
                self.load_data()
                self.show_info(
                    f"Setting type '{setting_type.setting_type_name}' created"
                )
            except SettingTypeValidationError as e:
                self.show_error(f"Validation error: {e}")
            except Exception as e:
                self.show_error(f"Failed to create setting type: {e}")

    def edit_setting_type(self) -> None:
        """Open dialog to edit the selected setting type."""
        if not self.selected_setting_type:
            self.show_error("No setting type selected")
            return
        
        # Prevent editing system setting types
        if self.selected_setting_type.is_system:
            self.show_error("Cannot edit system setting type")
            return
        
        dlg = SettingTypeDialog(
            setting_type=self.selected_setting_type, parent=self
        )
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                updated_setting_type = dlg.get_setting_type()
                self.setting_type_manager.update_setting_type(
                    setting_type=updated_setting_type,
                    user_id=self.current_user_id,
                )
                self.load_data()
                self.show_info(
                    f"Setting type '{updated_setting_type.setting_type_name}' updated"
                )
            except SettingTypeValidationError as e:
                self.show_error(f"Validation error: {e}")
            except Exception as e:
                self.show_error(f"Failed to update setting type: {e}")

    def delete_setting_type(self) -> None:
        """Delete the selected setting type after confirmation."""
        if not self.selected_setting_type:
            self.show_error("No setting type selected")
            return
        
        # Prevent deleting system setting types
        if self.selected_setting_type.is_system:
            self.show_error("Cannot delete system setting type")
            return
        
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Delete Setting Type",
            f"Delete setting type '{self.selected_setting_type.setting_type_name}'?\n\n"
            "This will soft-delete the setting type (mark as inactive).",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        
        try:
            self.setting_type_manager.delete_setting_type(
                setting_type_id=self.selected_setting_type.setting_type_id,
                user_id=self.current_user_id,
            )
            self.load_data()
            self.show_info(
                f"Setting type '{self.selected_setting_type.setting_type_name}' deleted"
            )
        except SettingTypeValidationError as e:
            self.show_error(f"Validation error: {e}")
        except Exception as e:
            self.show_error(f"Failed to delete setting type: {e}")

    def show_error(self, msg: str) -> None:
        """Display an error message to the user.
        
        Args:
            msg: Error message to display
        """
        if self.testing_mode:
            print(f"ERROR: {msg}")
        else:
            QMessageBox.critical(self, "Error", msg)
        self.status.setText(msg)

    def show_info(self, msg: str) -> None:
        """Display an information message to the user.
        
        Args:
            msg: Information message to display
        """
        if self.testing_mode:
            print(f"INFO: {msg}")
        else:
            # Don't show info dialogs, just update status
            pass
        self.status.setText(msg)


def _modern_qss() -> str:
    """Return QSS for modern Windows 11-style appearance.
    
    Returns:
        QSS stylesheet string
    """
    return """
    QWidget {
        background: #f3f3f3;
        color: #222;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QDialog {
        background: #f3f3f3;
    }
    QListWidget {
        background: #fff;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        padding: 8px;
        font-size: 14px;
    }
    QListWidget::item {
        padding: 8px;
        border-radius: 6px;
    }
    QListWidget::item:selected {
        background: #e0e6f5;
        color: #222;
    }
    QListWidget::item:hover {
        background: #f0f0f0;
    }
    QPushButton {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1, stop:0 #e8e8ef, stop:1 #d1d1e0
        );
        border-radius: 10px;
        border: 1px solid #bfc8d6;
        padding: 10px 20px;
        font-size: 15px;
        font-weight: 500;
        min-width: 120px;
        min-height: 36px;
        color: #222;
    }
    QPushButton:hover {
        background: #e0e6f5;
        border: 1px solid #7aa2f7;
    }
    QPushButton:pressed {
        background: #d1d7e6;
    }
    QPushButton:disabled {
        background: #e8e8e8;
        color: #999;
        border: 1px solid #ccc;
    }
    QLabel#PanelTitle {
        font-size: 20px;
        font-weight: 600;
        color: #2a2a2a;
        margin-bottom: 10px;
    }
    QLabel#StatusBar {
        background: #e7eaf0;
        border-radius: 8px;
        padding: 8px 18px;
        margin: 10px;
        font-size: 13px;
        color: #3a3a3a;
    }
    QLineEdit#SearchBar {
        background: #fff;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
    }
    QLineEdit#SearchBar:focus {
        border: 1px solid #7aa2f7;
    }
    QComboBox {
        background: #fff;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 14px;
        min-height: 28px;
    }
    QComboBox:hover {
        border: 1px solid #7aa2f7;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SettingTypeManagerWindow()
    win.showMaximized()
    exit_code = app.exec()
    sys.exit(exit_code)
