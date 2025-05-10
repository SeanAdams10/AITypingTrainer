"""
Drill Screen Tester UI
---------------------
A minimal PyQt5 UI for selecting between snippet-based or manual text input.
- If 'Snippet Selection' is chosen: shows a dropdown of snippets and start/end index fields.
- If 'Manual Input' is chosen: shows a text box for manual entry.
- A preview panel always shows the current text (subset or manual).
- A Start button emits the relevant parameters.
"""
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup,
    QLabel, QComboBox, QLineEdit, QTextEdit, QPushButton
)
from PyQt5.QtCore import Qt
import sys

# Dummy snippet data for demonstration
SNIPPETS = [
    {"id": 1, "name": "Hello World", "content": "Hello, world! This is a test snippet."},
    {"id": 2, "name": "Quick Brown Fox", "content": "The quick brown fox jumps over the lazy dog."},
    {"id": 3, "name": "Lorem Ipsum", "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit."}
]

class DrillScreenTester(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Drill Screen Tester")
        self.setGeometry(200, 200, 600, 320)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()

        # Radio buttons
        radio_layout = QHBoxLayout()
        self.rb_snippet = QRadioButton("Snippet Selection")
        self.rb_manual = QRadioButton("Manual Text Input")
        self.rb_snippet.setChecked(True)
        self.rb_snippet.toggled.connect(self.on_radio_changed)
        self.rb_manual.toggled.connect(self.on_radio_changed)
        radio_group = QButtonGroup()
        radio_group.addButton(self.rb_snippet)
        radio_group.addButton(self.rb_manual)
        radio_layout.addWidget(self.rb_snippet)
        radio_layout.addWidget(self.rb_manual)
        layout.addLayout(radio_layout)

        # Snippet selection widgets
        self.snippet_combo = QComboBox()
        for s in SNIPPETS:
            self.snippet_combo.addItem(s["name"], s["id"])
        self.snippet_combo.currentIndexChanged.connect(self.update_preview)
        self.snippet_content_box = QTextEdit()
        self.snippet_content_box.setReadOnly(True)
        self.snippet_content_box.setMinimumHeight(40)
        self.snippet_start = QLineEdit("0")
        self.snippet_start.setFixedWidth(50)
        self.snippet_end = QLineEdit("10")
        self.snippet_end.setFixedWidth(50)
        self.snippet_start.textChanged.connect(self.update_preview)
        self.snippet_end.textChanged.connect(self.update_preview)
        snippet_layout = QVBoxLayout()
        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("Snippet:"))
        combo_layout.addWidget(self.snippet_combo)
        snippet_layout.addLayout(combo_layout)
        snippet_layout.addWidget(self.snippet_content_box)
        idx_layout = QHBoxLayout()
        idx_layout.addWidget(QLabel("Start:"))
        idx_layout.addWidget(self.snippet_start)
        idx_layout.addWidget(QLabel("End:"))
        idx_layout.addWidget(self.snippet_end)
        snippet_layout.addLayout(idx_layout)
        self.snippet_panel = QWidget()
        self.snippet_panel.setLayout(snippet_layout)

        # Manual input widgets
        self.manual_text = QTextEdit()
        self.manual_panel = QWidget()
        manual_layout = QVBoxLayout()
        manual_layout.addWidget(QLabel("Enter text:"))
        manual_layout.addWidget(self.manual_text)
        self.manual_panel.setLayout(manual_layout)
        self.manual_text.textChanged.connect(self.update_preview)

        # Preview and Start
        preview_layout = QHBoxLayout()
        self.preview_label = QLabel("Preview:")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.on_start)
        preview_layout.addWidget(self.preview_label)
        preview_layout.addWidget(self.preview_text, 1)
        preview_layout.addWidget(self.btn_start)

        # Add panels
        layout.addWidget(self.snippet_panel)
        layout.addWidget(self.manual_panel)
        layout.addLayout(preview_layout)
        self.setLayout(layout)
        self.on_radio_changed()
        self.update_preview()

    def on_radio_changed(self) -> None:
        snippet_mode = self.rb_snippet.isChecked()
        self.snippet_panel.setVisible(snippet_mode)
        self.manual_panel.setVisible(not snippet_mode)
        self.update_preview()

    def update_preview(self) -> None:
        if self.rb_snippet.isChecked():
            idx = self.snippet_combo.currentIndex()
            snippet = SNIPPETS[idx]
            # Show full snippet in the box
            self.snippet_content_box.setText(snippet["content"])
            try:
                start = int(self.snippet_start.text())
            except ValueError:
                start = 0
            try:
                end = int(self.snippet_end.text())
            except ValueError:
                end = len(snippet["content"])
            start = max(0, min(start, len(snippet["content"])))
            end = max(start, min(end, len(snippet["content"])))
            preview = snippet["content"][start:end]
            self.preview_text.setText(preview)
        else:
            self.preview_text.setText(self.manual_text.toPlainText())

    def on_start(self) -> None:
        from PyQt5.QtWidgets import QMessageBox
        if self.rb_manual.isChecked():
            snippet_id = -1
            snippet_start = 0
            snippet_end = 0
            text = self.manual_text.toPlainText()
        else:
            idx = self.snippet_combo.currentIndex()
            snippet = SNIPPETS[idx]
            snippet_id = snippet["id"]
            try:
                snippet_start = int(self.snippet_start.text())
            except ValueError:
                snippet_start = 0
            try:
                snippet_end = int(self.snippet_end.text())
            except ValueError:
                snippet_end = len(snippet["content"])
            snippet_start = max(0, min(snippet_start, len(snippet["content"])))
            snippet_end = max(snippet_start, min(snippet_end, len(snippet["content"])))
            text = snippet["content"][snippet_start:snippet_end]
        msg = QMessageBox(self)
        msg.setWindowTitle("Drill Parameters")
        msg.setText(f"snippet_id: {snippet_id}\nstart: {snippet_start}\nend: {snippet_end}\ncontent: {text}")
        msg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DrillScreenTester()
    win.show()
    sys.exit(app.exec_())
