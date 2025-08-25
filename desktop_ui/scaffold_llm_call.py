"""Scaffold dialog to exercise LLM n-gram word generation APIs."""

from __future__ import annotations

import os
import sys
import traceback
from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Add the parent directory to sys.path to ensure models can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from models.llm_ngram_service import LLMMissingAPIKeyError, LLMNgramService  # noqa: E402

try:  # noqa: E402
    from desktop_ui.api_key_dialog import APIKeyDialog
except Exception:  # pragma: no cover
    APIKeyDialog = None  # type: ignore


class ScaffoldLLMCallDialog(QDialog):
    """Minimal scaffold to test an LLM call.

    - One text entry box for the prompt (editable)
    - One result box where the result content is displayed (read-only)

    It loads the default prompt from Prompts/ngram_words_prompt.txt if available.
    Uses OPENAI_API_KEY from environment to initialize the service.
    Calls either the word-count or max-length API with sensible defaults.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize widgets and wire up signals."""
        super().__init__(parent)
        self.setWindowTitle("LLM Call Scaffold")
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # Prompt label and editor
        layout.addWidget(QLabel("Prompt:"))
        self.prompt_edit = QTextEdit(self)
        self.prompt_edit.setPlaceholderText("Enter or edit the prompt to send to the LLM...")
        self.prompt_edit.setAcceptRichText(False)
        self.prompt_edit.setFontFamily("Consolas")
        layout.addWidget(self.prompt_edit, 3)

        # Buttons row
        btn_row = QHBoxLayout()
        self.btn_load_default = QPushButton("Load Default Prompt", self)
        self.btn_run = QPushButton("Run LLM Call", self)
        self.btn_close = QPushButton("Close", self)
        btn_row.addWidget(self.btn_load_default)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        # Result label and viewer
        layout.addWidget(QLabel("Result:"))
        self.result_view = QTextEdit(self)
        self.result_view.setReadOnly(True)
        self.result_view.setAcceptRichText(False)
        self.result_view.setFontFamily("Consolas")
        layout.addWidget(self.result_view, 2)

        # Wire signals
        self.btn_load_default.clicked.connect(self._load_default_prompt)
        self.btn_run.clicked.connect(self._run_llm_call)
        self.btn_close.clicked.connect(self.close)

        # Try to load default prompt on open
        self._load_default_prompt()

    def _prompt_path(self) -> str:
        root = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(root, "Prompts", "ngram_words_prompt.txt")

    def _load_default_prompt(self) -> None:
        path = self._prompt_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                template = f.read()
            # Use a small default formatting for preview purposes
            example_prompt = template.format(
                ngrams=repr(["th", "ing"]),
                allowed_chars=repr("abcdefghijklmnopqrstuvwxyz"),
                max_length=400,
            )
            self.prompt_edit.setPlainText(example_prompt)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Prompt Failed",
                f"Failed to load default prompt from:\n{path}\n\n{e}",
            )

    def _resolve_api_key(self) -> Optional[str]:
        """Retrieve API key via env vars or APIKeyDialog (Option A)."""
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OpenAPI_Key")
        if api_key and api_key.strip():
            return api_key.strip()
        if APIKeyDialog is not None:
            return APIKeyDialog.get_api_key(parent=self, key_type="openai")
        return None

    def _run_llm_call(self) -> None:
        self.result_view.clear()
        user_prompt = self.prompt_edit.toPlainText().strip()
        if not user_prompt:
            QMessageBox.information(self, "No Prompt", "Please enter a prompt to send.")
            return

        api_key = self._resolve_api_key()
        if not api_key:
            QMessageBox.critical(
                self,
                "Missing API Key",
                (
                    "No OpenAI API key found. Set environment variable OPENAI_API_KEY or "
                    "configure it via the API Key dialog."
                ),
            )
            return

        try:
            service = LLMNgramService(api_key=api_key)
        except LLMMissingAPIKeyError as e:
            QMessageBox.critical(self, "API Key Error", str(e))
            return
        except Exception as e:  # constructor can fail if SDK missing
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize LLM service.\n\n{e}\n\n{traceback.format_exc()}",
            )
            return

        # Provide sensible defaults for required args
        ngrams: List[str] = ["th", "ing"]
        allowed_chars = "abcdefghijklmnopqrstuvwxyz"
        max_length = 400

        try:
            # Prefer word-count API if available, else fall back to string-based
            if hasattr(service, "get_words_with_ngrams_by_wordcount"):
                words = service.get_words_with_ngrams_by_wordcount(  # type: ignore[attr-defined]
                    ngrams=ngrams,
                    allowed_chars=allowed_chars,
                    target_word_count=max_length // 5 or 1,
                )
                self.result_view.setPlainText(" ".join(words))
            else:
                result = service.get_words_with_ngrams(
                    ngrams=ngrams,
                    allowed_chars=allowed_chars,
                    max_length=max_length,
                )
                self.result_view.setPlainText(result)
        except Exception as e:
            QMessageBox.critical(
                self,
                "LLM Call Failed",
                f"An error occurred while calling the LLM.\n\n{e}\n\n{traceback.format_exc()}",
            )


def open_scaffold_llm_call(parent: Optional[QWidget] = None) -> None:
    """Open the scaffold dialog modally."""
    dlg = ScaffoldLLMCallDialog(parent)
    # exec() creates a modal dialog by default
    dlg.exec()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    # Create QApplication instance for standalone execution
    app = QApplication(sys.argv)
    # Open the scaffold dialog
    open_scaffold_llm_call()
    # Not needed since exec() is modal, but good practice
    sys.exit(0)
