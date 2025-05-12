"""
Drill Configuration Dialog for AI Typing Trainer.

This module provides a dialog for configuring typing drill parameters,
including snippet selection, index ranges, and launches the typing drill.
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Add project root to path for direct script execution
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5 import QtWidgets, QtCore


class DrillConfigDialog(QtWidgets.QDialog):
    """
    Dialog for configuring typing drill parameters.
    
    Allows users to:
    - Select a snippet from the library
    - Set start and end indices for partial snippets
    - Launch the typing drill with configured parameters
    
    Args:
        db_manager: Database manager instance to access snippets
        parent: Optional parent widget
    """
    
    def __init__(
        self,
        db_manager: Any,
        parent: Optional[QtWidgets.QDialog] = None
    ) -> None:
        super().__init__(parent)
        self.db_manager = db_manager
        self.snippets: List[Dict[str, Any]] = []
        
        self.setWindowTitle("Configure Typing Drill")
        self.setMinimumSize(600, 450)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        
        self._setup_ui()
        self._load_snippets()
        
    def _setup_ui(self) -> None:
        """Set up the UI components of the dialog."""
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # Snippet selection group
        snippet_group = QtWidgets.QGroupBox("Select Snippet")
        snippet_layout = QtWidgets.QVBoxLayout(snippet_group)
        
        # Snippet selector
        self.snippet_selector = QtWidgets.QComboBox()
        self.snippet_selector.setMinimumWidth(400)
        self.snippet_selector.currentIndexChanged.connect(self._update_preview)
        snippet_layout.addWidget(QtWidgets.QLabel("Snippet:"))
        snippet_layout.addWidget(self.snippet_selector)
        
        # Snippet preview
        self.snippet_preview = QtWidgets.QTextEdit()
        self.snippet_preview.setReadOnly(True)
        self.snippet_preview.setMinimumHeight(120)
        snippet_layout.addWidget(QtWidgets.QLabel("Preview:"))
        snippet_layout.addWidget(self.snippet_preview)
        
        main_layout.addWidget(snippet_group)
        
        # Range selection group
        range_group = QtWidgets.QGroupBox("Text Range")
        range_layout = QtWidgets.QFormLayout(range_group)
        
        # Start and end index inputs
        self.start_index = QtWidgets.QSpinBox()
        self.start_index.setMinimum(0)
        self.start_index.setMaximum(9999)
        self.start_index.setValue(0)
        self.start_index.valueChanged.connect(self._update_preview)
        
        self.end_index = QtWidgets.QSpinBox()
        self.end_index.setMinimum(0)
        self.end_index.setMaximum(9999)
        self.end_index.setValue(100)
        self.end_index.valueChanged.connect(self._update_preview)
        
        range_layout.addRow("Start Index:", self.start_index)
        range_layout.addRow("End Index:", self.end_index)
        
        # Custom text option
        self.use_custom_text = QtWidgets.QCheckBox("Use custom text instead")
        self.use_custom_text.toggled.connect(self._toggle_custom_text)
        range_layout.addRow("", self.use_custom_text)
        
        self.custom_text = QtWidgets.QTextEdit()
        self.custom_text.setPlaceholderText("Enter custom text for typing practice...")
        self.custom_text.setEnabled(False)
        self.custom_text.textChanged.connect(self._update_preview)
        range_layout.addRow("Custom Text:", self.custom_text)
        
        main_layout.addWidget(range_group)
        
        # Buttons area
        button_box = QtWidgets.QDialogButtonBox()
        self.start_button = QtWidgets.QPushButton("Start Typing Drill")
        self.start_button.clicked.connect(self._start_drill)
        button_box.addButton(self.start_button, QtWidgets.QDialogButtonBox.AcceptRole)
        
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_box.addButton(cancel_button, QtWidgets.QDialogButtonBox.RejectRole)
        
        main_layout.addWidget(button_box)
    
    def _load_snippets(self) -> None:
        """Load snippets from the database."""
        try:
            snippet_manager = self.db_manager.get_snippet_manager()
            self.snippets = snippet_manager.get_all_snippets()
            
            self.snippet_selector.clear()
            for snippet in self.snippets:
                self.snippet_selector.addItem(
                    f"{snippet['id']}: {snippet['title']}", 
                    snippet['id']
                )
                
            if self.snippets:
                self._update_preview()
                
        except (AttributeError, IndexError, ValueError) as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Loading Snippets",
                f"Failed to load snippets: {str(e)}"
            )
    
    def _update_preview(self) -> None:
        """Update the preview based on selected snippet and range."""
        if self.use_custom_text.isChecked():
            # Show custom text in preview
            self.snippet_preview.setText(self.custom_text.toPlainText())
            return
            
        if not self.snippets:
            return
            
        idx = self.snippet_selector.currentIndex()
        if idx < 0 or idx >= len(self.snippets):
            return
            
        snippet = self.snippets[idx]
        content = snippet["content"]
        
        # Get selected range
        start = self.start_index.value()
        end = self.end_index.value()
        
        # Validate and adjust range
        start = max(0, min(start, len(content)))
        end = max(start, min(end, len(content)))
        
        # Update spinbox limits based on content
        self.end_index.setMaximum(len(content))
        
        # Update preview
        preview_text = content[start:end]
        self.snippet_preview.setText(preview_text)
    
    def _toggle_custom_text(self, checked: bool) -> None:
        """Toggle between snippet selection and custom text."""
        self.snippet_selector.setEnabled(not checked)
        self.start_index.setEnabled(not checked)
        self.end_index.setEnabled(not checked)
        self.custom_text.setEnabled(checked)
        self._update_preview()
    
    def _start_drill(self) -> None:
        """Launch the typing drill with configured parameters."""
        try:
            from desktop_ui.typing_drill import TypingDrillScreen
            
            if self.use_custom_text.isChecked():
                # Use custom text
                snippet_id = -1  # -1 indicates custom text
                start = 0
                end = 0
                content = self.custom_text.toPlainText()
            else:
                # Use selected snippet
                idx = self.snippet_selector.currentIndex()
                if idx < 0 or idx >= len(self.snippets):
                    return
                    
                snippet = self.snippets[idx]
                snippet_id = snippet["id"]
                content = snippet["content"]
                start = self.start_index.value()
                end = self.end_index.value()
                
                # Validate range
                start = max(0, min(start, len(content)))
                end = max(start, min(end, len(content)))
                content = content[start:end]
            
            # Create and show the typing drill dialog
            drill = TypingDrillScreen(
                snippet_id=snippet_id,
                start=start,
                end=end,
                content=content,
                db_manager=self.db_manager,  # Pass the database manager
                parent=self
            )
            
            # This accepts and closes the config dialog
            self.accept()
            
            # Show the typing drill dialog
            drill.exec_()
            
        except (ImportError, RuntimeError, ValueError) as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Error Starting Drill",
                f"Failed to start typing drill: {str(e)}"
            )


if __name__ == "__main__":
    from db.database_manager import DatabaseManager
    
    app = QtWidgets.QApplication([])
    
    # Test with real database
    db_path = os.path.join(project_root, "typing_data.db")
    db_manager_instance = DatabaseManager(db_path)
    
    dialog = DrillConfigDialog(db_manager=db_manager_instance)
    dialog.exec_()
