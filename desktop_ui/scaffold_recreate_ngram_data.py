"""
ScaffoldRecreateNgramData UI form for recreating ngram data from session keystrokes.

This form provides an interface to find all practice sessions that don't have
corresponding ngram data and recreate the ngrams from their keystrokes.
"""

import os
import sys
from typing import Optional, List
from uuid import UUID

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox, QProgressBar, QTextEdit

from db.database_manager import ConnectionType, DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager_new import NGramManagerNew
from models.ngram_new import Keystroke as NewKeystroke, MIN_NGRAM_SIZE


class RecreateNgramWorker(QThread):
    """Worker thread for recreating ngram data in background."""

    finished = Signal(dict)  # Signal with result dictionary
    error = Signal(str)  # Signal with error message
    progress = Signal(str)  # Signal for progress updates
    session_processed = Signal(str, int, int)  # Signal for individual session progress

    def __init__(self, db_manager: DatabaseManager, ngram_manager: NGramManagerNew) -> None:
        super().__init__()
        self.db_manager = db_manager
        self.ngram_manager = ngram_manager

    def run(self) -> None:
        try:
            result = self.recreate_ngram_data_with_progress()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def recreate_ngram_data_with_progress(self) -> dict:
        """Recreate ngram data for all sessions missing ngram data."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Starting recreate ngram data process")

        # Find all sessions that don't appear in either ngram table
        sessions = self.db_manager.fetchall(
            """
            SELECT 
                ps.session_id,
                ps.start_time,
                ps.user_id,
                ps.keyboard_id
            FROM practice_sessions ps
            WHERE ps.session_id NOT IN (
                SELECT DISTINCT session_id FROM session_ngram_speed
                UNION
                SELECT DISTINCT session_id FROM session_ngram_errors
            )
            ORDER BY ps.start_time ASC
            """
        )

        if not sessions:
            logger.info("No sessions found to process")
            return {"total_sessions": 0, "processed_sessions": 0, "total_ngrams_created": 0}

        logger.info(f"Found {len(sessions)} sessions to process")
        total_sessions = len(sessions)

        processed_sessions = 0
        total_ngrams_created = 0

        for i, session in enumerate(sessions, 1):
            session_id = session["session_id"]
            start_time = session["start_time"]

            # Emit progress signal with session info
            session_info = f"Session {session_id[:8]}... - {start_time}"
            self.session_processed.emit(session_info, i, total_sessions)

            try:
                # Load keystrokes for this session
                keystrokes = self.db_manager.fetchall(
                    """
                    SELECT 
                        keystroke_char,
                        expected_char,
                        keystroke_time,
                        is_correct
                    FROM session_keystrokes 
                    WHERE session_id = ?
                    ORDER BY keystroke_time ASC
                    """,
                    (session_id,)
                )

                if not keystrokes:
                    logger.warning(f"No keystrokes found for session {session_id}")
                    continue

                # Reconstruct expected_text from expected_char stream and build new Keystrokes
                from datetime import datetime
                expected_text = "".join(ks_row["expected_char"] for ks_row in keystrokes)
                def _parse_ts(v: object) -> datetime:
                    if isinstance(v, datetime):
                        return v
                    return datetime.fromisoformat(str(v))

                ks_objects: List[NewKeystroke] = []
                for idx, ks in enumerate(keystrokes):
                    exp = ks["expected_char"]
                    act = ks["keystroke_char"]
                    ks_objects.append(
                        NewKeystroke(
                            timestamp=_parse_ts(ks["keystroke_time"]),
                            text_index=idx,
                            expected_char=exp,
                            actual_char=act,
                            correctness=(act == exp),
                        )
                    )

                # Analyze once, then persist via new manager (filter sizes 2-5)
                spd, err = self.ngram_manager.analyze(
                    session_id=UUID(session_id), expected_text=expected_text, keystrokes=ks_objects
                )
                spd = [s for s in spd if MIN_NGRAM_SIZE <= s.size <= 5]
                err = [e for e in err if MIN_NGRAM_SIZE <= e.size <= 5]

                spd_count, err_count = self.ngram_manager.persist_all(self.db_manager, spd, err)
                session_ngrams_created = spd_count + err_count

                total_ngrams_created += session_ngrams_created
                processed_sessions += 1

                logger.info(
                    f"Processed session {session_id}: {session_ngrams_created} ngrams created"
                )

            except Exception as e:
                logger.error(f"Error processing session {session_id}: {str(e)}")
                # Continue with next session rather than failing completely
                continue

        summary = {
            "total_sessions": total_sessions,
            "processed_sessions": processed_sessions,
            "total_ngrams_created": total_ngrams_created,
        }

        logger.info(
            f"Recreate ngram data completed: {processed_sessions}/{total_sessions} "
            f"sessions processed, {total_ngrams_created} total ngrams created"
        )

        return summary


class ScaffoldRecreateNgramData(QtWidgets.QWidget):
    """
    UI form for recreating ngram data from session keystrokes.

    Provides an interface with a button to run the recreate process
    and displays progress and results in real-time.
    """

    def __init__(
        self, db_path: Optional[str] = None, connection_type: ConnectionType = ConnectionType.CLOUD
    ) -> None:
        super().__init__()
        self.setWindowTitle("Recreate Ngram Data")
        self.resize(700, 500)

        # Initialize database connection
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")

        self.db_manager = DatabaseManager(db_path, connection_type=connection_type)
        self.db_manager.init_tables()

        # Initialize services
        self.ngram_manager = NGramManagerNew()
        self.analytics_service = NGramAnalyticsService(self.db_manager, self.ngram_manager)

        self.worker = None
        self.setup_ui()
        self.load_session_stats()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("Recreate Ngram Data")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Description
        description = QtWidgets.QLabel(
            "This tool finds all practice sessions that don't have corresponding "
            "ngram data and recreates the ngrams from their keystrokes. Sessions "
            "are processed from oldest to newest to maintain chronological order."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)

        # Stats section
        stats_group = QtWidgets.QGroupBox("Session Statistics")
        stats_layout = QtWidgets.QVBoxLayout(stats_group)
        
        self.stats_label = QtWidgets.QLabel("Loading session statistics...")
        self.stats_label.setStyleSheet(
            "padding: 10px; background-color: #f0f0f0; border-radius: 5px;"
        )
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Recreate button
        self.recreate_button = QtWidgets.QPushButton("Recreate Ngram Data")
        self.recreate_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; "
            "font-size: 14px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.recreate_button.clicked.connect(self.start_recreate)
        layout.addWidget(self.recreate_button)

        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(
            "background-color: #f5f5f5; border: 1px solid #ddd; padding: 5px;"
        )
        layout.addWidget(self.results_text)

        # Close button
        close_button = QtWidgets.QPushButton("Close")
        close_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #da190b; }"
        )
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def load_session_stats(self) -> None:
        """Load and display session statistics."""
        try:
            # Get total sessions
            total_sessions = self.db_manager.fetchone(
                "SELECT COUNT(*) as count FROM practice_sessions"
            )["count"]

            # Get sessions with ngram data
            sessions_with_ngrams = self.db_manager.fetchone(
                """
                SELECT COUNT(DISTINCT session_id) as count 
                FROM (
                    SELECT session_id FROM session_ngram_speed
                    UNION
                    SELECT session_id FROM session_ngram_errors
                )
                """
            )["count"]

            # Get sessions without ngram data
            sessions_without_ngrams = total_sessions - sessions_with_ngrams

            stats_text = (
                f"📊 Total practice sessions: {total_sessions}\n"
                f"✅ Sessions with ngram data: {sessions_with_ngrams}\n"
                f"❌ Sessions missing ngram data: {sessions_without_ngrams}"
            )

            self.stats_label.setText(stats_text)

            # Enable/disable button based on whether there's work to do
            self.recreate_button.setEnabled(sessions_without_ngrams > 0)
            if sessions_without_ngrams == 0:
                self.recreate_button.setText("No Sessions Need Processing")

        except Exception as e:
            self.stats_label.setText(f"Error loading statistics: {str(e)}")

    def start_recreate(self) -> None:
        """Start the recreate process in a background thread."""
        self.recreate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.results_text.clear()
        self.results_text.append("🚀 Starting ngram data recreation process...")
        self.results_text.append("=" * 60)

        # Create and start worker thread
        self.worker = RecreateNgramWorker(self.db_manager, self.ngram_manager)
        self.worker.finished.connect(self.on_recreate_finished)
        self.worker.error.connect(self.on_recreate_error)
        self.worker.session_processed.connect(self.on_session_processed)
        self.worker.start()

    def on_session_processed(self, session_info: str, current: int, total: int) -> None:
        """Handle individual session processing updates."""
        # Update progress bar
        progress_percentage = int((current / total) * 100)
        self.progress_bar.setValue(progress_percentage)
        
        # Add session info to text box
        self.results_text.append(f"[{current}/{total}] {session_info}")
        
        # Auto-scroll to bottom
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_recreate_finished(self, result: dict) -> None:
        """Handle successful completion of recreate process."""
        self.progress_bar.setValue(100)  # Ensure it shows 100% complete
        self.recreate_button.setEnabled(True)

        total_sessions = result.get("total_sessions", 0)
        processed_sessions = result.get("processed_sessions", 0)
        total_ngrams_created = result.get("total_ngrams_created", 0)

        self.results_text.append("\n" + "=" * 60)
        self.results_text.append("✅ Ngram data recreation completed successfully!")
        self.results_text.append(f"📊 Sessions processed: {processed_sessions}/{total_sessions}")
        self.results_text.append(f"📈 Total ngrams created: {total_ngrams_created}")

        # Refresh stats
        self.load_session_stats()

        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Ngram data recreation completed successfully!\n\n"
            f"• Sessions processed: {processed_sessions}/{total_sessions}\n"
            f"• Total ngrams created: {total_ngrams_created}",
        )

    def on_recreate_error(self, error_message: str) -> None:
        """Handle errors during recreate process."""
        self.progress_bar.setVisible(False)
        self.recreate_button.setEnabled(True)

        self.results_text.append("\n❌ Error during ngram recreation process:")
        self.results_text.append(f"   {error_message}")

        # Show error message
        QMessageBox.critical(
            self, "Error", f"An error occurred during ngram data recreation:\n\n{error_message}"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Ngram recreation process is still running. Are you sure you want to "
                "close? This will terminate the process and may leave data in an "
                "inconsistent state.",
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


def launch_scaffold_recreate_ngram_data() -> None:
    """Launch the ScaffoldRecreateNgramData application."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    window = ScaffoldRecreateNgramData()
    window.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_scaffold_recreate_ngram_data()
