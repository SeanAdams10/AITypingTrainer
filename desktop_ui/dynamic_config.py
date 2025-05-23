"""
Dynamic N-gram Practice Configuration Dialog.

This module provides a dialog for configuring n-gram based practice sessions,
allowing users to target specific n-gram patterns for improvement.
"""

import os
import sys
from typing import Optional

# Add project root to path for direct script execution
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from models.llm_ngram_service import LLMMissingAPIKeyError, LLMNgramService

# Import MCP server for database operations
try:
    from mcp_servers.typing_sqlite import typing_sqlite as mcp_db
except ImportError:
    mcp_db = None  # type: ignore


class DynamicConfigDialog(QtWidgets.QDialog):
    """
    Dialog for configuring n-gram based typing practice.
    
    Allows users to:
    - Select n-gram size (3-10 characters)
    - Choose focus area (speed or accuracy)
    - Set desired practice length
    - View problematic n-grams
    - Generate and preview practice content
    - Launch the typing drill with generated content
    
    Args:
        db_manager: Database manager instance
        parent: Optional parent widget
    """
    
    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.ngram_service: Optional[LLMNgramService] = None
        self.generated_content: str = ""
        
        self.setWindowTitle("Practice Weak Points")
        self.setMinimumSize(700, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self._setup_ui()
        self._load_ngram_analysis()
    
    def _check_db_connection(self) -> bool:
        """Check if database connection is available."""
        if mcp_db is None:
            QtWidgets.QMessageBox.critical(
                self,
                "Database Error",
                "Database connection is not available. Please ensure the MCP server is running."
            )
            return False
        return True
    
    def _setup_ui(self) -> None:
        """Set up the UI components of the dialog."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Configuration group
        config_group = QtWidgets.QGroupBox("Practice Configuration")
        config_layout = QtWidgets.QFormLayout(config_group)
        
        # N-gram size selection
        self.ngram_size = QtWidgets.QComboBox()
        self.ngram_size.addItems([str(i) for i in range(3, 11)])  # 3-10
        self.ngram_size.setCurrentText("4")  # Default to 4-grams
        self.ngram_size.currentTextChanged.connect(self._load_ngram_analysis)
        
        # Focus selection
        self.focus_group = QtWidgets.QButtonGroup(self)
        self.speed_radio = QtWidgets.QRadioButton("Focus on Speed")
        self.accuracy_radio = QtWidgets.QRadioButton("Focus on Accuracy")
        self.focus_group.addButton(self.speed_radio, 0)
        self.focus_group.addButton(self.accuracy_radio, 1)
        self.speed_radio.setChecked(True)  # Default to speed focus
        self.focus_group.buttonToggled.connect(self._load_ngram_analysis)
        
        focus_layout = QtWidgets.QHBoxLayout()
        focus_layout.addWidget(self.speed_radio)
        focus_layout.addWidget(self.accuracy_radio)
        
        # Practice length
        self.practice_length = QtWidgets.QSpinBox()
        self.practice_length.setRange(50, 2000)
        self.practice_length.setValue(200)  # Default length
        self.practice_length.setSuffix(" characters")
        
        # Add to form
        config_layout.addRow("N-gram Size:", self.ngram_size)
        config_layout.addRow("Practice Focus:", focus_layout)
        config_layout.addRow("Practice Length:", self.practice_length)
        
        # N-gram analysis group
        analysis_group = QtWidgets.QGroupBox("N-gram Analysis")
        analysis_layout = QtWidgets.QVBoxLayout(analysis_group)
        
        self.ngram_table = QtWidgets.QTableWidget(5, 3)  # 5 rows, 3 columns
        self.ngram_table.setHorizontalHeaderLabels(["N-gram", "Metric", "Value"])
        self.ngram_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.ngram_table.verticalHeader().setVisible(False)
        self.ngram_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        analysis_layout.addWidget(self.ngram_table)
        
        # Generate button
        self.generate_btn = QtWidgets.QPushButton("Generate Practice Content")
        self.generate_btn.clicked.connect(self._generate_content)
        
        # Generated content preview
        self.content_preview = QtWidgets.QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setPlaceholderText("Generated practice content will appear here...")
        
        # Button box
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        # Set OK button text to "Start Drill"
        start_drill_btn = button_box.button(QtWidgets.QDialogButtonBox.Ok)
        start_drill_btn.setText("Start Drill")
        start_drill_btn.setEnabled(False)  # Disabled until content is generated
        
        # Add to main layout
        layout.addWidget(config_group)
        layout.addWidget(analysis_group)
        layout.addWidget(self.generate_btn)
        layout.addWidget(self.content_preview)
        layout.addWidget(button_box)
    
    def _load_ngram_analysis(self) -> None:
        """Load and display n-gram analysis based on current settings."""
        if not self._check_db_connection():
            return
            
        ngram_size = int(self.ngram_size.currentText())
        focus_on_speed = self.speed_radio.isChecked()
        
        try:
            # Clear existing data
            self.ngram_table.setRowCount(0)
            
            # Query for top problematic n-grams
            if focus_on_speed:
                query = """
                    SELECT ngram_text, AVG(ngram_time) as avg_time
                    FROM session_ngram_speed
                    WHERE ngram_size = ?
                    GROUP BY ngram_text
                    ORDER BY avg_time DESC
                    LIMIT 5
                """
                result = mcp_db.mcp2_read_query(query, (ngram_size,))
                
                # Debug: Print query and result
                print(f"Speed query: {query} with ngram_size={ngram_size}")
                print(f"Result: {result}")
                
                # Populate table
                self.ngram_table.setRowCount(len(result))
                for row, row_data in enumerate(result):
                    ngram = str(row_data['ngram_text'])
                    metric = float(row_data['avg_time'])
                    self.ngram_table.setItem(row, 0, QtWidgets.QTableWidgetItem(ngram))
                    self.ngram_table.setItem(row, 1, QtWidgets.QTableWidgetItem("Avg Time (ms)"))
                    self.ngram_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{metric:.2f}"))
                    
            else:  # Focus on errors
                query = """
                    SELECT ngram, error_count
                    FROM session_ngram_errors
                    WHERE ngram_size = ?
                    ORDER BY error_count DESC
                    LIMIT 5
                """
                result = mcp_db.mcp2_read_query(query, (ngram_size,))
                
                # Debug: Print query and result
                print(f"Error query: {query} with ngram_size={ngram_size}")
                print(f"Result: {result}")
                
                # Populate table
                self.ngram_table.setRowCount(len(result))
                for row, row_data in enumerate(result):
                    ngram = str(row_data['ngram'])
                    metric = int(row_data['error_count'])
                    self.ngram_table.setItem(row, 0, QtWidgets.QTableWidgetItem(ngram))
                    self.ngram_table.setItem(row, 1, QtWidgets.QTableWidgetItem("Error Count"))
                    self.ngram_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{metric}"))
                    
        except KeyError as ke:
            error_msg = f"Unexpected data format in result: {str(ke)}\nResult: {result}"
            print(error_msg)
            QtWidgets.QMessageBox.warning(
                self,
                "Data Format Error",
                f"Unexpected data format in result: {str(ke)}"
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in _load_ngram_analysis: {error_details}")
            QtWidgets.QMessageBox.warning(
                self,
                "Error Loading N-grams",
                f"Could not load n-gram analysis.\n\nError: {str(e)}"
            )
    
    def _generate_content(self) -> None:
        """Generate practice content based on selected n-grams."""
        if not self._check_db_connection():
            return
            
        try:
            # Get selected n-grams
            ngrams = []
            for row in range(min(5, self.ngram_table.rowCount())):
                item = self.ngram_table.item(row, 0)
                if item and item.text():
                    ngrams.append(item.text())
            
            if not ngrams:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No N-grams Selected",
                    "Please ensure n-gram analysis is loaded correctly."
                )
                return
            
            # Check if LLM service is available
            if not self.ngram_service:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "API Key Required",
                        "Please set the OPENAI_API_KEY environment variable to use this feature."
                    )
                    return
                self.ngram_service = LLMNgramService(api_key)
            
            # Generate content
            self.generated_content = self.ngram_service.get_words_with_ngrams(
                ngrams=ngrams,
                max_length=self.practice_length.value()
            )
            
            # Update UI
            self.content_preview.setPlainText(self.generated_content)
            
            # Enable Start Drill button
            button_box = self.findChild(QtWidgets.QDialogButtonBox)
            if button_box:
                start_btn = button_box.button(QtWidgets.QDialogButtonBox.Ok)
                if start_btn:
                    start_btn.setEnabled(True)
            
        except LLMMissingAPIKeyError as e:
            QtWidgets.QMessageBox.critical(
                self,
                "API Key Error",
                f"OpenAI API key is required: {str(e)}"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Generation Error",
                f"Failed to generate practice content: {str(e)}"
            )
    
    def _on_accept(self) -> None:
        """Handle accept (Start Drill) button click."""
        if not self.generated_content.strip():
            QtWidgets.QMessageBox.warning(
                self,
                "No Content",
                "Please generate practice content before starting the drill."
            )
            return
        
        # TODO: Launch typing drill with generated content
        # For now, just show a message
        QtWidgets.QMessageBox.information(
            self,
            "Drill Starting",
            f"Starting drill with {len(self.generated_content)} characters of generated content."
        )
        self.accept()


def main() -> None:
    """Main function for standalone execution."""
    import sys

    from PyQt5.QtWidgets import QApplication
    
    # Check if MCP server is available
    if mcp_db is None:
        print("Error: MCP server for database operations is not available.")
        print("Please ensure the typing_sqlite MCP server is running.")
        return 1
    
    app = QApplication(sys.argv)
    
    # Create and show the dialog
    dialog = DynamicConfigDialog()
    dialog.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
