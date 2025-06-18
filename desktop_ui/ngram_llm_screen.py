import os
import sys
from typing import Any, List, Optional

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.llm_ngram_service import LLMMissingAPIKeyError, LLMNgramService


class NgramLLMScreen(QWidget):
    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("LLM N-Gram Word Generator")
        self.setMinimumWidth(600)
        self.service = None
        self.api_key = None
        key_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "Keys", "OpenAPI_Key.txt"
        )
        key_file = os.path.normpath(key_file)
        if os.path.isfile(key_file):
            try:
                with open(key_file, "r") as f:
                    file_key = f.read().strip()
                    if file_key:
                        self.api_key = file_key
            except Exception as e:
                QMessageBox.warning(
                    self, "Key File Error", f"Could not read API key file: {e}"
                )
        if not self.api_key:
            # Prompt the user for the API key
            while not self.api_key:
                key, ok = QInputDialog.getText(
                    self, "OpenAI API Key Required", "Enter your OpenAI API key:"
                )
                if ok and key:
                    self.api_key = key.strip()
                else:
                    QMessageBox.critical(
                        self,
                        "API Key Error",
                        "OpenAI API key must be provided to use this feature.",
                    )
        try:
            self.service = LLMNgramService(api_key=self.api_key)
        except LLMMissingAPIKeyError as e:
            QMessageBox.critical(self, "API Key Error", str(e))
        self.snippet_inputs: List[QLineEdit] = []
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()

        # Instructions
        layout.addWidget(QLabel("Enter one or more short snippets (n-grams):"))

        # Scroll area for snippet inputs
        self.snippet_area = QVBoxLayout()
        snippet_container = QVBoxLayout()
        self.add_snippet_input()  # Add initial input
        snippet_container.addLayout(self.snippet_area)
        add_btn = QPushButton("Add Snippet")
        add_btn.clicked.connect(self.add_snippet_input)
        snippet_container.addWidget(add_btn)
        layout.addLayout(snippet_container)

        # Call LLM button
        self.llm_btn = QPushButton("Call LLM")
        self.llm_btn.clicked.connect(self.call_llm)
        layout.addWidget(self.llm_btn)

        # Results box
        layout.addWidget(QLabel("LLM Results:"))
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        layout.addWidget(self.result_box)

        self.setLayout(layout)

    def add_snippet_input(self) -> None:
        hbox = QHBoxLayout()
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Enter n-gram (e.g., ada, Fish)")
        hbox.addWidget(line_edit)
        remove_btn = QPushButton("Remove")
        remove_btn.setMaximumWidth(80)
        remove_btn.clicked.connect(lambda: self.remove_snippet_input(hbox, line_edit))
        hbox.addWidget(remove_btn)
        self.snippet_area.addLayout(hbox)
        self.snippet_inputs.append(line_edit)

    def remove_snippet_input(self, hbox: QHBoxLayout, line_edit: QLineEdit) -> None:
        # Remove from layout and list
        for i in reversed(range(hbox.count())):
            item = hbox.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget:
                widget.setParent(None)
        self.snippet_area.removeItem(hbox)
        if line_edit in self.snippet_inputs:
            self.snippet_inputs.remove(line_edit)

    def call_llm(self) -> None:
        if not self.service:
            QMessageBox.critical(self, "Service Error", "LLM service not available.")
            return
        snippets = [
            le.text().strip() for le in self.snippet_inputs if le.text().strip()
        ]
        if not snippets:
            QMessageBox.warning(
                self, "Input Error", "Please enter at least one n-gram snippet."
            )
            return
        self.llm_btn.setEnabled(False)
        self.result_box.setPlainText("Calling LLM, please wait...")
        try:
            result = self.service.get_words_with_ngrams(snippets)
            self.result_box.setPlainText(result)
        except Exception as e:
            self.result_box.setPlainText(f"Error: {str(e)}")
        finally:
            self.llm_btn.setEnabled(True)


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = NgramLLMScreen()
    win.show()
    sys.exit(app.exec_())
