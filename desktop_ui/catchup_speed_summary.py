"""CatchupSpeedSummary UI form for triggering speed summary catchup for all sessions.

This form provides an interface to run the CatchupSpeedSummary method
from the NGramAnalyticsService to process all sessions from oldest to newest.
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
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from db.database_manager import DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


class CatchupWorker(QThread):
    """Worker thread for running CatchupSpeedSummary in background."""

    finished = Signal(dict)  # Signal with result dictionary
    error = Signal(str)  # Signal with error message
    progress = Signal(str)  # Signal for progress updates
    session_processed = Signal(str, int, int)  # per-session progress (info, current, total)

    def __init__(self, *, analytics_service: NGramAnalyticsService) -> None:
        """Initialize the worker with the analytics service."""
        super().__init__()
        self.analytics_service = analytics_service

    def run(self) -> None:
        """Execute the catchup process and emit results or errors."""
        try:
            result = self.catchup_speed_summary_with_progress()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def catchup_speed_summary_with_progress(self) -> dict[str, int]:
        """Modified version of catchup_speed_summary that emits progress signals."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Starting CatchupSpeedSummary process")

        # Get all sessions ordered from oldest to newest
        db = self.analytics_service.db
        assert db is not None
        sessions = db.fetchall(
            (
                """
                SELECT 
                    ps.session_id,
                    ps.start_time,
                    ps.ms_per_keystroke as session_avg_speed
                FROM practice_sessions ps
                LEFT OUTER JOIN ngram_speed_summary_hist
                     ON ps.session_id = ngram_speed_summary_hist.session_id
                WHERE ngram_speed_summary_hist.session_id IS NULL
                ORDER BY ps.start_time ASC
                """
            )
        )

        if not sessions:
            self.progress.emit("No sessions found that need speed summary processing.")
            return {"sessions_processed": 0, "curr_updated": 0, "hist_inserted": 0}

        total_sessions = len(sessions)
        self.progress.emit(f"Found {total_sessions} sessions to process")

        curr_updated = 0
        hist_inserted = 0

        for i, session in enumerate(sessions, 1):
            session_id: str = str(session["session_id"])  # Ensure string type
            start_time = session["start_time"]
            session_avg_speed = session["session_avg_speed"]

            # Emit per-session progress
            progress_msg = (
                f"Processing session {session_id} "
                f"(started: {start_time}, avg: {session_avg_speed:.1f} ms/key)"
            )
            self.session_processed.emit(progress_msg, i, total_sessions)

            try:
                # Process this specific session
                result = self.analytics_service.add_speed_summary_for_session(session_id=session_id)
                curr_updated += result.get("curr_updated", 0)
                hist_inserted += result.get("hist_inserted", 0)

                logger.info(f"Processed session {session_id}: {result}")

            except Exception as e:
                error_msg = f"Error processing session {session_id}: {str(e)}"
                logger.error(error_msg)
                self.progress.emit(error_msg)
                # Continue with next session rather than failing completely

        summary = {
            "sessions_processed": total_sessions,
            "curr_updated": curr_updated,
            "hist_inserted": hist_inserted,
        }

        logger.info(f"CatchupSpeedSummary completed: {summary}")
        self.progress.emit(
            f"Completed processing {total_sessions} sessions. "
            f"Updated {curr_updated} current records, inserted {hist_inserted} historical records."
        )

        return summary


class CatchupSpeedSummary(QDialog):
    """UI form for triggering speed summary catchup for all sessions.

    Provides an interface with a button to run the CatchupSpeedSummary method
    and displays progress and results in real-time.
    """

    def __init__(self, *, db_manager: DatabaseManager) -> None:
        """Initialize the dialog and underlying services.

        Args:
            db_manager: DatabaseManager instance (required).
        """
        super().__init__()
        self.setWindowTitle("Catchup Speed Summary")
        self.resize(700, 600)

        # Use provided DatabaseManager
        self.db_manager = db_manager

        # Initialize services
        self.ngram_manager = NGramManager(db_manager=self.db_manager)
        self.analytics_service = NGramAnalyticsService(self.db_manager, self.ngram_manager)

        # Worker thread holder
        self.worker: Optional[CatchupWorker] = None

        # Build UI and load stats
        self.setup_ui()
        self.load_session_stats()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Speed Summary Catchup")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Description
        description = QLabel(
            "This tool processes all sessions that don't have speed summary data, "
            "from oldest to newest. It updates current speed summaries and creates "
            "historical records for comprehensive speed tracking."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(description)

        # Session statistics
        self.session_stats = QLabel("Loading session statistics...")
        self.session_stats.setStyleSheet("font-weight: bold; margin: 10px;")
        layout.addWidget(self.session_stats)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Per-session progress label
        self.session_progress = QLabel("")
        self.session_progress.setVisible(False)
        self.session_progress.setStyleSheet("font-size: 12px; color: #666; margin: 5px;")
        layout.addWidget(self.session_progress)

        # Log output
        log_label = QLabel("Processing Log:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        self.log_output.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10px;")
        layout.addWidget(self.log_output)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Catchup Process")
        self.start_button.clicked.connect(self.start_catchup)
        self.start_button.setStyleSheet("font-weight: bold; padding: 10px;")
        button_layout.addWidget(self.start_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def load_session_stats(self) -> None:
        """Load and display session statistics."""
        try:
            # Get count of sessions needing processing
            unprocessed_count = self.db_manager.fetchone(
                """
                SELECT COUNT(*) as count
                FROM practice_sessions ps
                LEFT OUTER JOIN ngram_speed_summary_hist
                     ON ps.session_id = ngram_speed_summary_hist.session_id
                WHERE ngram_speed_summary_hist.session_id IS NULL
                """
            )

            # Get total session count
            total_count = self.db_manager.fetchone(
                "SELECT COUNT(*) as count FROM practice_sessions"
            )

            unprocessed = unprocessed_count["count"] if unprocessed_count else 0
            total = total_count["count"] if total_count else 0

            self.session_stats.setText(
                f"Sessions needing processing: {unprocessed} / {total} total sessions"
            )

            if unprocessed == 0:
                self.start_button.setText("All Sessions Processed")
                self.start_button.setEnabled(False)

        except Exception as e:
            self.session_stats.setText(f"Error loading statistics: {str(e)}")

    def start_catchup(self) -> None:
        """Start the catchup process in a background thread."""
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", "Catchup process is already running.")
            return

        # Disable start button and show progress
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.session_progress.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress initially
        self.log_output.clear()
        self.log_output.append("Starting catchup process...")

        # Create and start worker thread
        self.worker = CatchupWorker(analytics_service=self.analytics_service)
        self.worker.finished.connect(self.on_catchup_finished)
        self.worker.error.connect(self.on_catchup_error)
        self.worker.progress.connect(self.on_progress_update)
        self.worker.session_processed.connect(self.on_session_processed)
        self.worker.start()

    def on_session_processed(self, info: str, current: int, total: int) -> None:
        """Handle per-session progress updates."""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.session_progress.setText(f"({current}/{total}) {info}")
        self.log_output.append(f"[{current}/{total}] {info}")

    def on_progress_update(self, message: str) -> None:
        """Handle general progress updates."""
        self.log_output.append(message)

    def on_catchup_finished(self, result: dict[str, int]) -> None:
        """Handle successful completion of catchup process."""
        self.progress_bar.setVisible(False)
        self.session_progress.setVisible(False)
        self.start_button.setEnabled(True)

        # Show completion message
        sessions_processed = result.get("sessions_processed", 0)
        curr_updated = result.get("curr_updated", 0)
        hist_inserted = result.get("hist_inserted", 0)

        completion_msg = (
            f"Catchup process completed successfully!\n\n"
            f"Sessions processed: {sessions_processed}\n"
            f"Current records updated: {curr_updated}\n"
            f"Historical records inserted: {hist_inserted}"
        )

        QMessageBox.information(self, "Process Complete", completion_msg)
        self.log_output.append(f"\n✅ {completion_msg.replace(chr(10), ' ')}")

        # Reload statistics
        self.load_session_stats()

    def on_catchup_error(self, error_message: str) -> None:
        """Handle errors during catchup process."""
        self.progress_bar.setVisible(False)
        self.session_progress.setVisible(False)
        self.start_button.setEnabled(True)

        QMessageBox.critical(self, "Process Error", f"Catchup process failed:\n\n{error_message}")
        self.log_output.append(f"\n❌ Error: {error_message}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.worker is not None and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Process Running",
                "Catchup process is still running. Are you sure you want to close?",
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


def launch_catchup_speed_summary() -> None:
    """Launch the CatchupSpeedSummary application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Create DatabaseManager for standalone usage
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")
    db_manager = DatabaseManager(db_path)
    db_manager.init_tables()

    window = CatchupSpeedSummary(db_manager=db_manager)
    window.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_catchup_speed_summary()
