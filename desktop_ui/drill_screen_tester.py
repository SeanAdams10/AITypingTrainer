"""Drill Screen Tester UI.

---------------------
A minimal PySide6 UI for selecting between snippet-based or manual text input.
- If 'Snippet Selection' is chosen: shows a dropdown of snippets and start/end index fields.
- If 'Manual Input' is chosen: shows a text box for manual entry.
- A preview panel always shows the current text (subset or manual).
- A Start button emits the relevant parameters.
"""

import os
import sys

# Add project root to path for direct script execution
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sys

from PySide6 import QtWidgets

# Dummy snippet data for demonstration
SNIPPETS = [
    {
        "id": 1,
        "name": "Hello World",
        "content": "Hello, world! This is a test snippet.",
    },
    {
        "id": 2,
        "name": "Quick Brown Fox",
        "content": "The quick brown fox jumps over the lazy dog.",
    },
    {
        "id": 3,
        "name": "Lorem Ipsum",
        "content": "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    },
]


class DrillScreenTester(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Drill Screen Tester")
        self.setGeometry(200, 200, 600, 320)
        self.init_ui()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()

        # Radio buttons
        radio_layout = QtWidgets.QHBoxLayout()
        self.rb_snippet = QtWidgets.QRadioButton("Snippet Selection")
        self.rb_manual = QtWidgets.QRadioButton("Manual Text Input")
        self.rb_snippet.setChecked(True)
        self.rb_snippet.toggled.connect(self.on_radio_changed)
        self.rb_manual.toggled.connect(self.on_radio_changed)
        radio_group = QtWidgets.QButtonGroup()
        radio_group.addButton(self.rb_snippet)
        radio_group.addButton(self.rb_manual)
        radio_layout.addWidget(self.rb_snippet)
        radio_layout.addWidget(self.rb_manual)
        layout.addLayout(radio_layout)

        # Snippet selection widgets
        self.snippet_combo = QtWidgets.QComboBox()
        for s in SNIPPETS:
            self.snippet_combo.addItem(s["name"], s["id"])
        self.snippet_combo.currentIndexChanged.connect(self.update_preview)
        self.snippet_content_box = QtWidgets.QTextEdit()
        self.snippet_content_box.setReadOnly(True)
        self.snippet_content_box.setMinimumHeight(40)
        self.snippet_start = QtWidgets.QLineEdit("0")
        self.snippet_start.setFixedWidth(50)
        self.snippet_end = QtWidgets.QLineEdit("10")
        self.snippet_end.setFixedWidth(50)
        self.snippet_start.textChanged.connect(self.update_preview)
        self.snippet_end.textChanged.connect(self.update_preview)
        snippet_layout = QtWidgets.QVBoxLayout()
        combo_layout = QtWidgets.QHBoxLayout()
        combo_layout.addWidget(QtWidgets.QLabel("Snippet:"))
        combo_layout.addWidget(self.snippet_combo)
        snippet_layout.addLayout(combo_layout)
        snippet_layout.addWidget(self.snippet_content_box)
        idx_layout = QtWidgets.QHBoxLayout()
        idx_layout.addWidget(QtWidgets.QLabel("Start:"))
        idx_layout.addWidget(self.snippet_start)
        idx_layout.addWidget(QtWidgets.QLabel("End:"))
        idx_layout.addWidget(self.snippet_end)
        snippet_layout.addLayout(idx_layout)
        self.snippet_panel = QtWidgets.QWidget()
        self.snippet_panel.setLayout(snippet_layout)

        # Manual input widgets
        self.manual_text = QtWidgets.QTextEdit()
        self.manual_panel = QtWidgets.QWidget()
        manual_layout = QtWidgets.QVBoxLayout()
        manual_layout.addWidget(QtWidgets.QLabel("Enter text:"))
        manual_layout.addWidget(self.manual_text)
        self.manual_panel.setLayout(manual_layout)
        self.manual_text.textChanged.connect(self.update_preview)

        # Preview and Start
        preview_layout = QtWidgets.QHBoxLayout()
        self.preview_label = QtWidgets.QLabel("Preview:")
        self.preview_text = QtWidgets.QTextEdit()
        self.preview_text.setReadOnly(True)
        self.btn_start = QtWidgets.QPushButton("Start")
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
        """Launch TypingDrillScreen with the selected snippet/manual text and indices."""
        print("Start button clicked!")
        # Robust import for both direct script and package usage
        try:
            print("Attempting to import from desktop_ui.typing_drill...")
            from desktop_ui.typing_drill import TypingDrillScreen
            print("Successfully imported TypingDrillScreen from desktop_ui.typing_drill")
        except ModuleNotFoundError as e:
            print(f"ModuleNotFoundError: {e}")
            print("Falling back to local import...")
            try:
                from typing_drill import TypingDrillScreen
                print("Successfully imported TypingDrillScreen from typing_drill")
            except ModuleNotFoundError as e:
                print(f"ERROR: Both import attempts failed! {e}")
                print("Cannot continue without TypingDrillScreen module")
                return

        try:
            print("Gathering parameters for TypingDrillScreen...")
            if self.rb_manual.isChecked():
                snippet_id = -1  # Use -1 to indicate manual text mode
                snippet_start = 0
                snippet_end = 0
                text = self.manual_text.toPlainText()
                print(f"Using manual text, length: {len(text)}, snippet_id: {snippet_id}")
            else:
                idx = self.snippet_combo.currentIndex()
                print(f"Snippet index selected: {idx}")
                snippet = SNIPPETS[idx]
                snippet_id = snippet["id"]
                try:
                    snippet_start = int(self.snippet_start.text())
                except ValueError:
                    print("Invalid start index, defaulting to 0")
                    snippet_start = 0
                try:
                    snippet_end = int(self.snippet_end.text())
                except ValueError:
                    print("Invalid end index, defaulting to content length")
                    snippet_end = len(snippet["content"])
                snippet_start = max(0, min(snippet_start, len(snippet["content"])))
                snippet_end = max(snippet_start, min(snippet_end, len(snippet["content"])))
                text = snippet["content"][snippet_start:snippet_end]
                print(f"Using snippet ID: {snippet_id}, start: {snippet_start}, end: {snippet_end}")
                print(f"Content length: {len(text)}")

            print("Creating TypingDrillScreen dialog...")
            dlg = TypingDrillScreen(
                snippet_id, snippet_start, snippet_end, text, parent=self
            )
            print("Showing TypingDrillScreen dialog...")
            dlg.exec_()
            print("TypingDrillScreen dialog closed.")
        except Exception as e:
            import traceback
            print(f"ERROR in on_start: {e}")
            print(traceback.format_exc())


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = DrillScreenTester()
    win.show()
    sys.exit(app.exec_())
