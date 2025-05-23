"""
View Snippet Dialog for the Desktop UI

Provides a maximized dialog for viewing snippet content with proper formatting.
"""

from typing import Optional

# Properly import PyQt5 widgets
from PyQt5 import QtCore, QtGui, QtWidgets

# Use explicit imports to fix linting issues
QDialog = QtWidgets.QDialog
QVBoxLayout = QtWidgets.QVBoxLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QTextEdit = QtWidgets.QTextEdit
QPushButton = QtWidgets.QPushButton
QWidget = QtWidgets.QWidget
QScrollArea = QtWidgets.QScrollArea
QSizePolicy = QtWidgets.QSizePolicy

# Import core and gui items
Qt = QtCore.Qt
QIcon = QtGui.QIcon
QFont = QtGui.QFont


class ViewSnippetDialog(QDialog):
    """
    Dialog for viewing snippet content with all its parts.
    Shows in maximized mode with proper formatting.
    """

    def __init__(
        self,
        title: str,
        snippet_name: str,
        content: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Initialize the view snippet dialog.

        Args:
            title: Dialog title
            snippet_name: Name of the snippet
            content: Full snippet content (all parts)
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setStyleSheet(_view_dialog_qss())
        self.setWindowState(Qt.WindowMaximized)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Snippet name header
        self.name_label = QLabel(f"<h1>{snippet_name}</h1>")
        self.name_label.setObjectName("SnippetTitle")
        self.name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.name_label)

        # Content area with formatting
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        self.content_display.setFont(QFont("Consolas", 12))
        self.content_display.setLineWrapMode(QTextEdit.FixedColumnWidth)
        self.content_display.setLineWrapColumnOrWidth(100)
        self.content_display.setText(content)
        self.content_display.setMinimumHeight(400)
        layout.addWidget(self.content_display)

        # Close button
        btns = QHBoxLayout()
        self.closeBtn = QPushButton(QIcon.fromTheme("window-close"), "Close")
        self.closeBtn.setMinimumHeight(36)
        self.closeBtn.setCursor(QtCore.Qt.PointingHandCursor)
        self.closeBtn.setStyleSheet("font-size: 15px; font-weight: 500;")
        self.closeBtn.setMinimumWidth(120)
        btns.addStretch(1)
        btns.addWidget(self.closeBtn)
        layout.addLayout(btns)

        # Connect signals
        self.closeBtn.clicked.connect(self.accept)


def _view_dialog_qss() -> str:
    """
    Return QSS for a modern Windows 11 view dialog look.

    Returns:
        str: QSS styling for the view dialog
    """
    return """
    QDialog {
        background-color: #f5f5f5;
        border: 1px solid #d1d1d1;
    }
    
    QTextEdit {
        background-color: #ffffff;
        border: 1px solid #d1d1d1;
        border-radius: 8px;
        padding: 15px;
        selection-background-color: #0078d4;
        selection-color: white;
    }
    
    QPushButton {
        background-color: #0078d4;
        color: white;
        border-radius: 4px;
        padding: 8px 15px;
        border: none;
    }
    
    QPushButton:hover {
        background-color: #0066b5;
    }
    
    QPushButton:pressed {
        background-color: #005a9e;
    }
    
    QPushButton[text="Cancel"] {
        background-color: #e0e0e0;
        color: #202020;
    }
    
    QPushButton[text="Cancel"]:hover {
        background-color: #d1d1d1;
    }
    
    #SnippetTitle {
        color: #0078d4;
        font-size: 18px;
        padding: 5px;
    }
    """
