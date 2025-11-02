"""Dialog components for Setting Type management.

Provides modern dialogs for creating and editing setting type definitions.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.setting_type import SettingType


class SettingTypeDialog(QDialog):
    """Dialog for creating or editing a setting type.
    
    Provides form fields for all setting type attributes with validation.
    """

    def __init__(
        self,
        setting_type: Optional[SettingType] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the setting type dialog.
        
        Args:
            setting_type: Existing setting type to edit (None for new)
            parent: Parent widget
        """
        super().__init__(parent)
        self.setting_type = setting_type
        self.is_edit_mode = setting_type is not None
        
        self.setWindowTitle(
            "Edit Setting Type" if self.is_edit_mode else "Add Setting Type"
        )
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.setup_ui()
        
        if self.is_edit_mode and setting_type:
            self.populate_fields(setting_type)

    def setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # Setting Type ID (6 chars, uppercase, alphanumeric)
        self.type_id_input = QLineEdit()
        self.type_id_input.setMaxLength(6)
        self.type_id_input.setPlaceholderText("6-char uppercase ID (e.g., USRFNT)")
        if self.is_edit_mode:
            self.type_id_input.setEnabled(False)  # Cannot change ID
        form_layout.addRow("Type ID*:", self.type_id_input)
        
        # Setting Type Name
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(100)
        self.name_input.setPlaceholderText("Human-readable name")
        form_layout.addRow("Name*:", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText(
            "Detailed description of what this setting controls"
        )
        form_layout.addRow("Description*:", self.description_input)
        
        # Related Entity Type
        self.entity_type_combo = QComboBox()
        self.entity_type_combo.addItems(["user", "keyboard", "global"])
        form_layout.addRow("Entity Type*:", self.entity_type_combo)
        
        # Data Type
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(["string", "integer", "boolean", "decimal"])
        self.data_type_combo.currentTextChanged.connect(
            self._on_data_type_changed
        )
        form_layout.addRow("Data Type*:", self.data_type_combo)
        
        # Default Value
        self.default_value_input = QLineEdit()
        self.default_value_input.setPlaceholderText("Optional default value")
        form_layout.addRow("Default Value:", self.default_value_input)
        
        # Validation Rules (JSON)
        self.validation_rules_input = QTextEdit()
        self.validation_rules_input.setMaximumHeight(100)
        self.validation_rules_input.setPlaceholderText(
            'Optional JSON validation rules\n'
            'Examples:\n'
            '  Integer: {"min": 8, "max": 32}\n'
            '  String: {"min_length": 1, "max_length": 50}\n'
            '  Pattern: {"pattern": "^[A-Z]+$"}'
        )
        form_layout.addRow("Validation Rules:", self.validation_rules_input)
        
        # Is System checkbox
        self.is_system_checkbox = QCheckBox("System Setting Type")
        self.is_system_checkbox.setToolTip(
            "System setting types cannot be deleted"
        )
        form_layout.addRow("", self.is_system_checkbox)
        
        # Is Active checkbox
        self.is_active_checkbox = QCheckBox("Active")
        self.is_active_checkbox.setChecked(True)
        self.is_active_checkbox.setToolTip(
            "Inactive setting types are hidden from users"
        )
        form_layout.addRow("", self.is_active_checkbox)
        
        layout.addLayout(form_layout)
        
        # Help text
        help_label = QLabel(
            "* Required fields\n"
            "Type ID must be exactly 6 uppercase alphanumeric characters"
        )
        help_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 10px;")
        layout.addWidget(help_label)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setMinimumWidth(100)
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        # Apply modern styling
        self.setStyleSheet(_dialog_qss())

    def _on_data_type_changed(self, data_type: str) -> None:
        """Update validation rules placeholder based on data type.
        
        Args:
            data_type: Selected data type
        """
        placeholders = {
            "integer": '{"min": 0, "max": 100}',
            "decimal": '{"min": 0.0, "max": 100.0}',
            "string": '{"min_length": 1, "max_length": 255}',
            "boolean": "{}",
        }
        
        current_text = self.validation_rules_input.toPlainText().strip()
        if not current_text:
            self.validation_rules_input.setPlaceholderText(
                f"Example: {placeholders.get(data_type, '{}')}"
            )

    def populate_fields(self, setting_type: SettingType) -> None:
        """Populate form fields with existing setting type data.
        
        Args:
            setting_type: Setting type to populate from
        """
        self.type_id_input.setText(setting_type.setting_type_id)
        self.name_input.setText(setting_type.setting_type_name)
        self.description_input.setPlainText(setting_type.description)
        
        # Set combo box values
        entity_index = self.entity_type_combo.findText(
            setting_type.related_entity_type
        )
        if entity_index >= 0:
            self.entity_type_combo.setCurrentIndex(entity_index)
        
        data_type_index = self.data_type_combo.findText(setting_type.data_type)
        if data_type_index >= 0:
            self.data_type_combo.setCurrentIndex(data_type_index)
        
        if setting_type.default_value:
            self.default_value_input.setText(setting_type.default_value)
        
        if setting_type.validation_rules:
            self.validation_rules_input.setPlainText(setting_type.validation_rules)
        
        self.is_system_checkbox.setChecked(setting_type.is_system)
        self.is_active_checkbox.setChecked(setting_type.is_active)

    def get_setting_type(self) -> SettingType:
        """Get the setting type from form fields.
        
        Returns:
            SettingType instance with form data
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        type_id = self.type_id_input.text().strip().upper()
        if not type_id or len(type_id) != 6:
            raise ValueError("Type ID must be exactly 6 characters")
        
        name = self.name_input.text().strip()
        if not name:
            raise ValueError("Name is required")
        
        description = self.description_input.toPlainText().strip()
        if not description:
            raise ValueError("Description is required")
        
        # Get optional fields
        default_value = self.default_value_input.text().strip() or None
        validation_rules = self.validation_rules_input.toPlainText().strip() or None
        
        # Create setting type
        setting_type_data = {
            "setting_type_id": type_id,
            "setting_type_name": name,
            "description": description,
            "related_entity_type": self.entity_type_combo.currentText(),
            "data_type": self.data_type_combo.currentText(),
            "default_value": default_value,
            "validation_rules": validation_rules,
            "is_system": self.is_system_checkbox.isChecked(),
            "is_active": self.is_active_checkbox.isChecked(),
            "created_user_id": "current-user",  # TODO: Get from session
            "updated_user_id": "current-user",  # TODO: Get from session
        }
        
        return SettingType(**setting_type_data)


def _dialog_qss() -> str:
    """Return QSS for modern dialog styling.
    
    Returns:
        QSS stylesheet string
    """
    return """
    QDialog {
        background: #f8f8f8;
    }
    QLabel {
        color: #333;
        font-size: 14px;
    }
    QLineEdit, QTextEdit {
        background: #fff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 8px;
        font-size: 14px;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1px solid #7aa2f7;
    }
    QLineEdit:disabled {
        background: #f0f0f0;
        color: #999;
    }
    QComboBox {
        background: #fff;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 6px 10px;
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
    QCheckBox {
        font-size: 14px;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid #d0d0d0;
    }
    QCheckBox::indicator:checked {
        background: #7aa2f7;
        border: 1px solid #7aa2f7;
    }
    QPushButton {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1, stop:0 #e8e8ef, stop:1 #d1d1e0
        );
        border-radius: 8px;
        border: 1px solid #bfc8d6;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 500;
        min-height: 36px;
    }
    QPushButton:hover {
        background: #e0e6f5;
        border: 1px solid #7aa2f7;
    }
    QPushButton:pressed {
        background: #d1d7e6;
    }
    QPushButton[default="true"] {
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1, stop:0 #7aa2f7, stop:1 #5a82d7
        );
        color: white;
        border: 1px solid #5a82d7;
    }
    QPushButton[default="true"]:hover {
        background: #6a92e7;
    }
    """
