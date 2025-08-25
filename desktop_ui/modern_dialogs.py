"""Modern Windows 11-style dialogs for the Snippets Library desktop UI.

Includes: CategoryDialog, SnippetDialog (with multi-line editing), ConfirmDialog.
"""

from typing import Optional

# Properly import PySide6 widgets
from PySide6 import QtCore, QtGui, QtWidgets

# Use explicit imports to fix linting issues
QDialog = QtWidgets.QDialog
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QTextEdit = QtWidgets.QTextEdit
QPushButton = QtWidgets.QPushButton
QWidget = QtWidgets.QWidget

# Import core and gui items
# Access the Qt class properly for type checking
Qt = QtCore.Qt  # For direct access
QtCursorShape = QtCore.Qt.CursorShape  # For cursor shapes
QIcon = QtGui.QIcon
QFont = QtGui.QFont


def remove_non_ascii(text: str) -> str:
    """Remove non-ASCII characters from a string."""
    return text.encode("ascii", "ignore").decode()


class CategoryDialog(QDialog):
    def __init__(
        self: "CategoryDialog",
        title: str,
        label: str,
        default: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(350)
        self.setStyleSheet(_modern_dialog_qss())
        layout = QVBoxLayout(self)
        self.label = QLabel(label)
        layout.addWidget(self.label)
        self.input = QLineEdit(default)
        self.input.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.input)
        btns = QHBoxLayout()
        self.okBtn = QPushButton(QIcon.fromTheme("dialog-ok-apply"), "OK")
        self.cancelBtn = QPushButton(QIcon.fromTheme("dialog-cancel"), "Cancel")
        for btn in (self.okBtn, self.cancelBtn):
            btn.setMinimumHeight(36)
            btn.setCursor(QtCursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 15px; font-weight: 500;")
        btns.addWidget(self.okBtn)
        btns.addWidget(self.cancelBtn)
        layout.addLayout(btns)
        self.okBtn.clicked.connect(self.accept)
        self.cancelBtn.clicked.connect(self.reject)
        self.input.returnPressed.connect(self.accept)

    def get_value(self) -> str:
        return self.input.text().strip()


class SnippetDialog(QDialog):
    def __init__(
        self: "SnippetDialog",
        title: str,
        name_label: str,
        content_label: str,
        default_name: str = "",
        default_content: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setStyleSheet(_modern_dialog_qss())
        layout = QVBoxLayout(self)
        self.name_label = QLabel(name_label)
        layout.addWidget(self.name_label)
        self.name_input = QLineEdit(default_name)
        self.name_input.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.name_input)
        self.content_label = QLabel(content_label)
        layout.addWidget(self.content_label)
        self.content_input = QTextEdit(default_content)
        self.content_input.setFont(QFont("Segoe UI", 11))
        self.content_input.setMinimumHeight(120)
        layout.addWidget(self.content_input)
        btns = QHBoxLayout()
        self.okBtn = QPushButton(QIcon.fromTheme("dialog-ok-apply"), "OK")
        self.cancelBtn = QPushButton(QIcon.fromTheme("dialog-cancel"), "Cancel")
        for btn in (self.okBtn, self.cancelBtn):
            btn.setMinimumHeight(36)
            btn.setCursor(QtCursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 15px; font-weight: 500;")
        btns.addWidget(self.okBtn)
        btns.addWidget(self.cancelBtn)
        layout.addLayout(btns)
        self.okBtn.clicked.connect(self.accept)
        self.cancelBtn.clicked.connect(self.reject)
        self.name_input.returnPressed.connect(self.accept)

    def get_values(self) -> tuple[str, str]:
        name = remove_non_ascii(self.name_input.text().strip())
        content = remove_non_ascii(self.content_input.toPlainText().strip())
        return name, content


def _modern_dialog_qss() -> str:
    return """
    QDialog {
        background: #fff;
        border-radius: 14px;
        border: 1px solid #e0e0e0;
    }
    QLabel {
        font-size: 15px;
        margin-bottom: 2px;
    }
    QLineEdit, QTextEdit {
        background: #f7f8fa;
        border-radius: 8px;
        border: 1px solid #cfd8dc;
        padding: 7px 10px;
        font-size: 15px;
    }
    QLineEdit:focus, QTextEdit:focus {
        border: 1.5px solid #7aa2f7;
        background: #f0f4ff;
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e8e8ef, stop:1 #d1d1e0);
        border-radius: 10px;
        border: 1px solid #bfc8d6;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: 500;
        min-width: 100px;
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
    """
