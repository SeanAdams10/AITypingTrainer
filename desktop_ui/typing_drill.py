"""
Desktop Typing Drill Screen for AI Typing Trainer (PyQt5 Version)
Displays a typing drill for a snippet, limited to the specified start and end indices.
"""
from PyQt5 import QtWidgets, QtGui
import requests
import json
from typing import Callable, Optional, Any

class TypingDrillWindow(QtWidgets.QDialog):
    def __init__(self, parent, snippet_id: int, start_index: int, end_index: int, on_finish: Optional[Callable[..., Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Typing Drill")
        self.setMinimumSize(800, 600)
        self.resize(900, 600)
        self.center_on_screen()
        self.snippet_id = snippet_id
        self.start_index = start_index
        self.end_index = end_index
        self.on_finish = on_finish
        self.session_id = None
        self.text_to_type = ""
        self.completed = False
        self._build_ui()
        self._fetch_session_and_snippet()

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def _fetch_session_and_snippet(self):
        # Fetch session and snippet info from backend
        try:
            response = requests.post(
                "http://127.0.0.1:5000/start-drill",
                json={
                    "snippet_id": self.snippet_id,
                    "start_index": self.start_index,
                    "end_index": self.end_index,
                    "as_json": True
                },
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                self.text_to_type = data["text"][self.start_index:self.end_index]
                self.text_widget.setPlainText(self.text_to_type)
                self.title.setText(f"Typing Drill for Snippet {self.snippet_id}")
                self.snippet_label.setText(f"Snippet: {data.get('snippet_name', '')}")
                self.range_label.setText(f"Range: {self.start_index} to {self.end_index}")
                self.error_label.setVisible(False)
            else:
                self.error_label.setText(f"Error fetching snippet: {response.text}")
                self.error_label.setVisible(True)
        except Exception as e:
            self.error_label.setText(f"Network error: {e}")
            self.error_label.setVisible(True)

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.title = QtWidgets.QLabel("Typing Drill")
        self.title.setFont(QtGui.QFont("Helvetica", 16, QtGui.QFont.Bold))
        layout.addWidget(self.title)
        self.snippet_label = QtWidgets.QLabel("")
        self.snippet_label.setFont(QtGui.QFont("Helvetica", 12))
        layout.addWidget(self.snippet_label)
        self.range_label = QtWidgets.QLabel("")
        self.range_label.setFont(QtGui.QFont("Helvetica", 11))
        layout.addWidget(self.range_label)
        # Text to type
        self.text_widget = QtWidgets.QTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setFont(QtGui.QFont("Consolas", 13))
        self.text_widget.setStyleSheet("background: #f8f9fa;")
        layout.addWidget(self.text_widget)
        # Typing input
        self.input_widget = QtWidgets.QTextEdit()
        self.input_widget.setFont(QtGui.QFont("Consolas", 13))
        self.input_widget.setFocus()
        layout.addWidget(self.input_widget)
        # Action buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.finish_btn = QtWidgets.QPushButton("Finish")
        self.finish_btn.clicked.connect(self._finish)
        btn_layout.addWidget(self.finish_btn)
        self.retry_btn = QtWidgets.QPushButton("Retry")
        self.retry_btn.clicked.connect(self._retry)
        self.retry_btn.setVisible(False)
        btn_layout.addWidget(self.retry_btn)
        self.continue_btn = QtWidgets.QPushButton("Continue")
        self.continue_btn.clicked.connect(self._continue)
        self.continue_btn.setVisible(False)
        btn_layout.addWidget(self.continue_btn)
        self.menu_btn = QtWidgets.QPushButton("Menu")
        self.menu_btn.clicked.connect(self._menu)
        self.menu_btn.setVisible(False)
        btn_layout.addWidget(self.menu_btn)
        layout.addLayout(btn_layout)
        # Stats label (hidden until completion)
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setVisible(False)
        layout.addWidget(self.stats_label)
        # Error label
        self.error_label = QtWidgets.QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        # Placeholder for special character display enhancement
        # TODO: visually distinguish tab, enter, space, underscore in self.text_widget

    def _finish(self):
        if self.completed:
            return
        user_text = self.input_widget.toPlainText()
        expected_text = self.text_to_type
        # Compute stats (WPM, accuracy, errors)
        wpm, accuracy, errors = self._calculate_stats(user_text, expected_text)
        # Send stats and keystrokes to backend
        stats = {
            "wpm": wpm,
            "accuracy": accuracy,
            "errors": errors,
            "expected_chars": len(expected_text),
            "actual_chars": len(user_text),
            # Add more stats as needed
        }
        keystrokes = self._collect_keystrokes(user_text, expected_text)
        try:
            response = requests.post(
                "http://127.0.0.1:5000/end-session",
                json={
                    "session_id": self.session_id,
                    "stats": stats,
                    "keystrokes": keystrokes,
                    "analyze_ngrams": True,
                },
                timeout=10,
            )
            if response.status_code == 200:
                result = response.json()
                ngram_text = ""
                if "ngram_results" in result:
                    ngram_text = f"\nN-gram analysis: {json.dumps(result['ngram_results'])}"
                self.stats_label.setText(
                    f"<b>Completed!</b>\nWPM: {wpm:.2f} | Accuracy: {accuracy:.2f}% | Errors: {errors}{ngram_text}"
                )
                self.stats_label.setVisible(True)
                self.error_label.setVisible(False)
            else:
                self.error_label.setText(f"Error submitting results: {response.text}")
                self.error_label.setVisible(True)
        except Exception as e:
            self.error_label.setText(f"Network error: {e}")
            self.error_label.setVisible(True)
        self.input_widget.setReadOnly(True)
        self.finish_btn.setEnabled(False)
        self.retry_btn.setVisible(True)
        self.continue_btn.setVisible(True)
        self.menu_btn.setVisible(True)
        self.completed = True

    def _retry(self):
        self.input_widget.setReadOnly(False)
        self.input_widget.clear()
        self.input_widget.setFocus()
        self.stats_label.setVisible(False)
        self.finish_btn.setEnabled(True)
        self.retry_btn.setVisible(False)
        self.continue_btn.setVisible(False)
        self.menu_btn.setVisible(False)
        self.completed = False

    def _continue(self):
        if self.on_finish:
            self.on_finish()
        self.accept()

    def _menu(self):
        self.reject()

    def _calculate_stats(self, user_text: str, expected_text: str):
        # Simple WPM, accuracy, error calculation (to be improved)
        # In a real implementation, track start/end time and keystrokes
        words = user_text.split()
        wpm = len(words) / 1  # Placeholder: 1 minute
        correct = sum(1 for a, b in zip(user_text, expected_text) if a == b)
        total = max(len(expected_text), 1)
        accuracy = (correct / total) * 100
        errors = sum(1 for a, b in zip(user_text, expected_text) if a != b) + abs(len(user_text) - len(expected_text))
        return wpm, accuracy, errors

    def _collect_keystrokes(self, user_text: str, expected_text: str):
        # Placeholder for keystroke collection logic. In a real app, log each key event.
        # Here, just return a list of dicts for each char typed.
        keystrokes = []
        for i, char in enumerate(user_text):
            expected = expected_text[i] if i < len(expected_text) else ''
            keystrokes.append({
                "char": char,
                "expected": expected,
                "is_correct": char == expected,
                # Add more fields as needed (timestamp, error_type, etc.)
            })
        return keystrokes
