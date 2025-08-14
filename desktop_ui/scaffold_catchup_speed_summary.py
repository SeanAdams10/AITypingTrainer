"""
ScaffoldCatchupSpeedSummary UI form for triggering speed summary catchup for all sessions.

This form provides an interface to run the CatchupSpeedSummary method
from the NGramAnalyticsService to process all sessions from oldest to newest.
"""

import os
import sys
from typing import Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox, QProgressBar, QTextEdit

from db.database_manager import ConnectionType, DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


class CatchupWorker(QThread):
    """Worker thread for running CatchupSpeedSummary in background."""

    finished = Signal(dict)  # Signal with result dictionary
    error = Signal(str)  # Signal with error message
    progress = Signal(str)  # Signal for progress updates
    session_processed = Signal(str, int, int)  # Signal for individual session progress (session_info, current, total)

    def __init__(self, analytics_service: NGramAnalyticsService):
        super().__init__()
        self.analytics_service = analytics_service

    def run(self):
        try:
            result = self.catchup_speed_summary_with_progress()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def catchup_speed_summary_with_progress(self) -> dict:
        """Modified version of catchup_speed_summary that emits progress signals."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Starting CatchupSpeedSummary process")

        # Get all sessions ordered from oldest to newest
        sessions = self.analytics_service.db.fetchall(
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

        if not sessions:
            logger.info("No sessions found to process")
            return {"total_sessions": 0, "total_hist_inserted": 0, "total_curr_updated": 0}

        logger.info(f"Found {len(sessions)} sessions to process")
        total_sessions = len(sessions)

        total_hist_inserted = 0
        total_curr_updated = 0
        processed_sessions = 0

        for i, session in enumerate(sessions, 1):
            session_id = session["session_id"]
            start_time = session["start_time"]
            avg_speed = session["session_avg_speed"]

            # Emit progress signal with session info
            session_info = f"Session {session_id[:8]}... - {start_time} - {avg_speed:.2f}ms"
            self.session_processed.emit(session_info, i, total_sessions)

            try:
                # Call AddSpeedSummaryForSession
                result = self.analytics_service.add_speed_summary_for_session(session_id)

                hist_inserted = result["hist_inserted"]
                curr_updated = result["curr_updated"]

                total_hist_inserted += hist_inserted
                total_curr_updated += curr_updated
                processed_sessions += 1

            except Exception as e:
                logger.error(f"Error processing session {session_id}: {str(e)}")
                # Continue with next session rather than failing completely
                continue

        summary = {
            "total_sessions": len(sessions),
            "processed_sessions": processed_sessions,
            "total_hist_inserted": total_hist_inserted,
            "total_curr_updated": total_curr_updated,
        }

        logger.info(
            f"CatchupSpeedSummary completed: {processed_sessions}/{len(sessions)} "
            f"sessions processed, "
            f"{total_curr_updated} total curr updates, {total_hist_inserted} total hist inserts"
        )

        return summary


class ScaffoldCatchupSpeedSummary(QtWidgets.QDialog):
    """
    UI form for triggering speed summary catchup for all sessions.

    Provides an interface with a button to run the CatchupSpeedSummary method
    and displays progress and results in real-time.
    """

    def __init__(
        self, db_path: Optional[str] = None, connection_type: ConnectionType = ConnectionType.CLOUD
    ) -> None:
        super().__init__()
        self.setWindowTitle("Catchup Speed Summary")
        self.resize(700, 600)

        # Initialize database connection
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")

        self.db_manager = DatabaseManager(db_path, connection_type=connection_type)
        self.db_manager.init_tables()

        # Initialize services
        self.ngram_manager = NGramManager(self.db_manager)
        self.analytics_service = NGramAnalyticsService(self.db_manager, self.ngram_manager)

        self.worker = None
        self.setup_ui()
        self.load_session_stats()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("Speed Summary Catchup")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Description
        description = QtWidgets.QLabel(
            "This tool processes all sessions from oldest to newest to catch up speed summaries.\n"
            "It calls AddSpeedSummaryForSession for each session and logs progress with record counts.\n"
            "This may take a while for large datasets."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)

        # Session statistics
        self.stats_label = QtWidgets.QLabel("Loading session statistics...")
        self.stats_label.setStyleSheet("margin: 10px; font-weight: bold; color: #333;")
        layout.addWidget(self.stats_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Catchup button
        self.catchup_button = QtWidgets.QPushButton("Catchup Now")
        self.catchup_button.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 12px; font-size: 14px; border-radius: 5px; font-weight: bold; }"
            "QPushButton:hover { background-color: #F57C00; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.catchup_button.clicked.connect(self.start_catchup)
        layout.addWidget(self.catchup_button)

        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(
            "background-color: #f5f5f5; border: 1px solid #ddd; padding: 5px; font-family: 'Courier New', monospace;"
        )
        layout.addWidget(self.results_text)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()

        # Clear log button
        clear_button = QtWidgets.QPushButton("Clear Log")
        clear_button.setStyleSheet(
            "QPushButton { background-color: #9E9E9E; color: white; padding: 8px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #757575; }"
        )
        clear_button.clicked.connect(self.results_text.clear)
        button_layout.addWidget(clear_button)

        # Close button
        close_button = QtWidgets.QPushButton("Close")
        close_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #da190b; }"
        )
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def load_session_stats(self):
        """Load and display session statistics."""
        try:
            # Get total sessions
            total_sessions = self.db_manager.fetchone(
                "SELECT COUNT(*) as count FROM practice_sessions"
            )
            total_count = total_sessions["count"] if total_sessions else 0

            # Get date range
            date_range = self.db_manager.fetchone(
                "SELECT MIN(start_time) as earliest, MAX(start_time) as latest FROM practice_sessions"
            )

            if date_range and date_range["earliest"]:
                earliest = date_range["earliest"]
                latest = date_range["latest"]
                self.stats_label.setText(
                    f"📊 Found {total_count} sessions to process\n"
                    f"📅 Date range: {earliest} to {latest}"
                )
            else:
                self.stats_label.setText("📊 No sessions found in database")
                self.catchup_button.setEnabled(False)

        except Exception as e:
            self.stats_label.setText(f"❌ Error loading session statistics: {str(e)}")
            self.catchup_button.setEnabled(False)

    def start_catchup(self):
        """Start the catchup process in a background thread."""
        reply = QMessageBox.question(
            self,
            "Confirm Catchup",
            "This process may take a long time for large datasets.\n\n"
            "Are you sure you want to start the speed summary catchup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.catchup_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)  # Determinate progress (0-100%)
        self.progress_bar.setValue(0)
        self.results_text.clear()
        self.results_text.append("🚀 Starting speed summary catchup process...")
        self.results_text.append("=" * 60)

        # Create and start worker thread
        self.worker = CatchupWorker(self.analytics_service)
        self.worker.finished.connect(self.on_catchup_finished)
        self.worker.error.connect(self.on_catchup_error)
        self.worker.session_processed.connect(self.on_session_processed)
        self.worker.start()

    def on_session_processed(self, session_info: str, current: int, total: int):
        """Handle individual session processing updates."""
        # Update progress bar
        progress_percentage = int((current / total) * 100)
        self.progress_bar.setValue(progress_percentage)
        
        # Add session info to text box
        self.results_text.append(f"[{current}/{total}] {session_info}")
        
        # Auto-scroll to bottom
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_catchup_finished(self, result: dict):
        """Handle successful completion of catchup."""
        self.progress_bar.setValue(100)  # Ensure it shows 100% complete
        self.catchup_button.setEnabled(True)

        total_sessions = result.get("total_sessions", 0)
        processed_sessions = result.get("processed_sessions", 0)
        total_curr_updated = result.get("total_curr_updated", 0)
        total_hist_inserted = result.get("total_hist_inserted", 0)

        self.results_text.append("\n" + "=" * 60)
        self.results_text.append("✅ Catchup process completed successfully!")
        self.results_text.append(f"📊 Sessions processed: {processed_sessions}/{total_sessions}")
        self.results_text.append(f"📈 Total current records updated: {total_curr_updated}")
        self.results_text.append(f"📋 Total history records inserted: {total_hist_inserted}")

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Speed summary catchup completed successfully!\n\n"
            f"• Sessions processed: {processed_sessions}/{total_sessions}\n"
            f"• Current records updated: {total_curr_updated}\n"
            f"• History records inserted: {total_hist_inserted}",
        )

    def on_catchup_error(self, error_message: str):
        """Handle errors during catchup."""
        self.progress_bar.setVisible(False)
        self.catchup_button.setEnabled(True)

        self.results_text.append("\n❌ Error during catchup process:")
        self.results_text.append(f"   {error_message}")

        # Show error message
        QMessageBox.critical(
            self, "Error", f"An error occurred during speed summary catchup:\n\n{error_message}"
        )

    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Catchup process is still running. Are you sure you want to close?\n\n"
                "This will terminate the process and may leave data in an inconsistent state.",
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


def launch_scaffold_catchup_speed_summary():
    """Launch the ScaffoldCatchupSpeedSummary application."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    window = ScaffoldCatchupSpeedSummary()
    window.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_scaffold_catchup_speed_summary()
