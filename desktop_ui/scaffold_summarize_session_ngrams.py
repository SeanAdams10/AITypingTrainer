"""ScaffoldSummarizeSessionNgrams UI form for triggering session ngram summarization.

This form provides a simple interface to run the SummarizeSessionNgrams method
from the NGramAnalyticsService.
"""

import os
import sys
from typing import Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from db.database_manager import ConnectionType, DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


class SummarizeWorker(QThread):
    """Worker thread for running SummarizeSessionNgrams in background."""

    finished = Signal(int)  # Signal with number of records inserted
    error = Signal(str)  # Signal with error message

    def __init__(self, analytics_service: NGramAnalyticsService) -> None:
        super().__init__()
        self.analytics_service = analytics_service

    def run(self) -> None:
        try:
            result = self.analytics_service.summarize_session_ngrams()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ScaffoldSummarizeSessionNgrams(QDialog):
    """UI form for triggering session ngram summarization.

    Provides a simple interface with a button to run the SummarizeSessionNgrams method
    and displays progress and results.
    """

    def __init__(
        self, db_path: Optional[str] = None, connection_type: ConnectionType = ConnectionType.CLOUD
    ) -> None:
        super().__init__()
        self.setWindowTitle("Summarize Session Ngrams")
        self.resize(600, 400)

        # Initialize database connection
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")

        self.db_manager = DatabaseManager(db_path, connection_type=connection_type)
        self.db_manager.init_tables()

        # Initialize services
        self.ngram_manager = NGramManager()
        self.analytics_service = NGramAnalyticsService(self.db_manager, self.ngram_manager)

        self.worker = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Session Ngram Summarization")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Description
        description = QLabel(
            "This tool summarizes ngram performance for all sessions that haven't been processed yet.\n"
            "It aggregates data from session_ngram_speed, session_ngram_errors, and session_keystrokes\n"
            "tables and inserts the results into session_ngram_summary."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Summarize button
        self.summarize_button = QPushButton("Summarize Ngrams")
        self.summarize_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; "
            "font-size: 14px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.summarize_button.clicked.connect(self.start_summarization)
        layout.addWidget(self.summarize_button)

        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(
            "background-color: #f5f5f5; border: 1px solid #ddd; padding: 5px;"
        )
        layout.addWidget(self.results_text)

        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #da190b; }"
        )
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def start_summarization(self) -> None:
        """Start the summarization process in a background thread."""
        self.summarize_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.results_text.clear()
        self.results_text.append("Starting session ngram summarization...")

        # Create and start worker thread
        self.worker = SummarizeWorker(self.analytics_service)
        self.worker.finished.connect(self.on_summarization_finished)
        self.worker.error.connect(self.on_summarization_error)
        self.worker.start()

    def on_summarization_finished(self, records_inserted: int) -> None:
        """Handle successful completion of summarization."""
        self.progress_bar.setVisible(False)
        self.summarize_button.setEnabled(True)

        self.results_text.append("\n✅ Summarization completed successfully!")
        self.results_text.append(
            f"📊 {records_inserted} records inserted into session_ngram_summary"
        )

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Session ngram summarization completed successfully!\n\n"
            f"{records_inserted} records were inserted into session_ngram_summary.",
        )

    def on_summarization_error(self, error_message: str) -> None:
        """Handle errors during summarization."""
        self.progress_bar.setVisible(False)
        self.summarize_button.setEnabled(True)

        self.results_text.append("\n❌ Error during summarization:")
        self.results_text.append(f"   {error_message}")

        # Show error message
        QMessageBox.critical(
            self,
            "Error",
            f"An error occurred during session ngram summarization:\n\n{error_message}",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Summarization is still running. Are you sure you want to close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.worker.terminate()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def launch_scaffold_summarize_session_ngrams() -> None:
    """Launch the ScaffoldSummarizeSessionNgrams application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = ScaffoldSummarizeSessionNgrams()
    window.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_scaffold_summarize_session_ngrams()
