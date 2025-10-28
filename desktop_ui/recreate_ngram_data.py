"""RecreateNgramData UI form for recreating ngram data from session keystrokes.

This form provides an interface to find all practice sessions that don't have
corresponding ngram data and recreate the ngrams from their keystrokes.
"""

# Standard library imports
import logging
import os
import sys
from typing import Dict, Optional

# Third-party imports
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

# Local imports (after sys.path adjustment)
# Ensure project root on sys.path so `db` and `models` resolve when run directly
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from db.database_manager import ConnectionType, DatabaseManager  # noqa: E402
from models.keystroke import Keystroke  # noqa: E402
from models.keystroke_collection import KeystrokeCollection  # noqa: E402
# Removed unused imports: MAX_NGRAM_SIZE, MIN_NGRAM_SIZE  # noqa: E402
from models.ngram_analytics_service import NGramAnalyticsService  # noqa: E402
from models.ngram_manager import NGramManager  # noqa: E402


class RecreateNgramWorker(QThread):
    """Worker thread for recreating ngram data in background."""

    finished = Signal(dict)  # Signal with result dictionary
    error = Signal(str)  # Signal with error message
    progress = Signal(str)  # Signal with progress updates
    session_processed = Signal(str, int, int)  # Signal for individual session progress

    def __init__(self, db_manager: DatabaseManager, ngram_manager: NGramManager) -> None:
        """Initialize the worker thread with DB and n-gram managers.

        Args:
            db_manager: Database manager instance for data access.
            ngram_manager: N-gram manager for processing n-grams.
        """
        super().__init__()
        self.db_manager = db_manager
        self.ngram_manager = ngram_manager
        self.logger = logging.getLogger(__name__)

    def run(self) -> None:
        """Execute the ngram recreation process and emit results or errors."""
        try:
            result = self.recreate_ngram_data_with_progress()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def recreate_ngram_data_with_progress(self) -> Dict[str, int]:
        """Recreate ngram data for all sessions with progress reporting.

        Returns:
            Dict containing counts of sessions processed and ngrams created.
        """
        self.logger.info("Starting ngram data recreation process")
        self.progress.emit("Starting ngram data recreation process...")

        # Get all sessions that need ngram data recreation
        sessions_query = """
            SELECT DISTINCT ps.session_id, ps.start_time, ps.content
            FROM practice_sessions ps
            LEFT JOIN session_ngram_speed sns ON ps.session_id = sns.session_id
            WHERE sns.session_id IS NULL
            ORDER BY ps.start_time ASC
        """

        sessions = self.db_manager.fetchall(query=sessions_query)
        if not sessions:
            self.progress.emit("No sessions found that need ngram data recreation.")
            return {"sessions_processed": 0, "ngrams_created": 0}

        total_sessions = len(sessions)
        self.progress.emit(f"Found {total_sessions} sessions to process")

        sessions_processed = 0
        total_ngrams_created = 0

        for i, session in enumerate(sessions, 1):
            session_id = str(session["session_id"])
            start_time = session["start_time"]
            content = session["content"] or ""  # Expected text for the session

            # Emit per-session progress
            progress_msg = f"Processing session {session_id} (started: {start_time})"
            self.session_processed.emit(progress_msg, i, total_sessions)

            try:
                # Get keystrokes for this session
                keystrokes_query = """
                    SELECT keystroke_char, expected_char, keystroke_time, is_error, text_index
                    FROM session_keystrokes
                    WHERE session_id = %s
                    ORDER BY text_index ASC
                """
                keystroke_rows = self.db_manager.fetchall(query=keystrokes_query, params=(session_id,))

                if not keystroke_rows:
                    self.progress.emit(f"No keystrokes found for session {session_id}")
                    continue

                # Convert to Keystroke objects
                keystrokes = []
                for row in keystroke_rows:
                    keystroke = Keystroke(
                        session_id=session_id,
                        keystroke_char=str(row["keystroke_char"]),
                        expected_char=str(row["expected_char"]),
                        keystroke_time=row["keystroke_time"],  # Already datetime from DB
                        is_error=bool(row["is_error"]),
                        text_index=int(row["text_index"]),
                    )
                    keystrokes.append(keystroke)

                # Create KeystrokeCollection
                keystroke_collection = KeystrokeCollection()
                for keystroke in keystrokes:
                    keystroke_collection.add_keystroke(keystroke=keystroke)

                # Generate and save ngrams using the correct NGramManager method
                try:
                    # Use the high-level workflow API that handles all ngram sizes
                    from uuid import UUID
                    speed_ngrams, error_ngrams = self.ngram_manager.analyze(
                        session_id=UUID(session_id),
                        expected_text=content,
                        keystrokes=keystroke_collection
                    )
                    
                    # Persist the ngrams
                    speed_count, error_count = self.ngram_manager.persist_all(
                        speed=speed_ngrams, errors=error_ngrams
                    )
                    session_ngrams_created = speed_count + error_count

                except Exception as ngram_error:
                    error_msg = f"Error processing ngrams for session {session_id}: {ngram_error}"
                    self.logger.warning(error_msg)
                    session_ngrams_created = 0

                sessions_processed += 1
                total_ngrams_created += session_ngrams_created

                self.logger.info(
                    f"Processed session {session_id}: {session_ngrams_created} ngrams created"
                )

            except Exception as e:
                error_msg = f"Error processing session {session_id}: {str(e)}"
                self.logger.error(error_msg)
                self.progress.emit(error_msg)
                # Continue with next session rather than failing completely

        summary = {
            "sessions_processed": sessions_processed,
            "ngrams_created": total_ngrams_created,
        }

        self.logger.info(f"Ngram data recreation completed: {summary}")
        completion_msg = (
            f"Completed processing {sessions_processed} sessions. "
            f"Created {total_ngrams_created} ngrams total."
        )
        self.progress.emit(completion_msg)

        return summary


class RecreateNgramData(QDialog):
    """UI form for recreating ngram data from session keystrokes.

    Provides an interface with a button to run the recreate process
    and displays progress and results in real-time.
    """

    def __init__(
        self, 
        db_manager: Optional[DatabaseManager] = None,
        db_path: Optional[str] = None, 
        connection_type: ConnectionType = ConnectionType.CLOUD
    ) -> None:
        """Initialize the dialog and underlying services.

        Args:
            db_manager: Optional DatabaseManager instance (preferred when called from UI).
            db_path: Optional path to the SQLite database file. Only used when db_manager is None.
            connection_type: Database connection type (local or cloud). 
                Only used when db_manager is None.
        """
        super().__init__()
        self.setWindowTitle("Recreate Ngram Data")
        self.resize(700, 500)

        # Use provided DatabaseManager or create new one for standalone usage
        if db_manager is not None:
            self.db_manager = db_manager
        else:
            # Initialize database connection for standalone usage
            if db_path is None:
                db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")

            self.db_manager = DatabaseManager(connection_type=connection_type, debug_util=None)
            self.db_manager.init_tables()

        # Initialize services
        self.ngram_manager = NGramManager(db_manager=self.db_manager)
        self.analytics_service = NGramAnalyticsService(db=self.db_manager, ngram_manager=self.ngram_manager)

        # Worker thread holder
        self.worker: Optional[RecreateNgramWorker] = None
        self.setup_ui()
        self.load_session_stats()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Recreate Ngram Data")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Description
        description = QLabel(
            "This tool finds all practice sessions that don't have corresponding "
            "ngram data and recreates the ngrams from their keystrokes. "
            "This is useful for recovering from data corruption or migrating data."
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
        button_layout = QVBoxLayout()

        self.start_button = QPushButton("Start Recreation Process")
        self.start_button.clicked.connect(self.start_recreation)
        self.start_button.setStyleSheet("font-weight: bold; padding: 10px;")
        button_layout.addWidget(self.start_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def load_session_stats(self) -> None:
        """Load and display session statistics."""
        try:
            # Get count of sessions needing ngram data recreation
            unprocessed_count = self.db_manager.fetchone(
                query="""
                SELECT COUNT(DISTINCT ps.session_id) as count
                FROM practice_sessions ps
                LEFT JOIN session_ngram_speed sns ON ps.session_id = sns.session_id
                WHERE sns.session_id IS NULL
                """
            )

            # Get total session count
            total_count = self.db_manager.fetchone(
                query="SELECT COUNT(*) as count FROM practice_sessions"
            )

            unprocessed = unprocessed_count["count"] if unprocessed_count else 0
            total = total_count["count"] if total_count else 0

            self.session_stats.setText(
                f"Sessions needing ngram data: {unprocessed} / {total} total sessions"
            )

            if unprocessed == 0:
                self.start_button.setText("All Sessions Have Ngram Data")
                self.start_button.setEnabled(False)

        except Exception as e:
            self.session_stats.setText(f"Error loading statistics: {str(e)}")

    def start_recreation(self) -> None:
        """Start the recreation process in a background thread."""
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.warning(self, "Process Running", "Recreation process is already running.")
            return

        # Disable start button and show progress
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.session_progress.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress initially
        self.log_output.clear()
        self.log_output.append("Starting ngram data recreation process...")

        # Create and start worker thread
        self.worker = RecreateNgramWorker(self.db_manager, self.ngram_manager)
        self.worker.finished.connect(self.on_recreation_finished)
        self.worker.error.connect(self.on_recreation_error)
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

    def on_recreation_finished(self, result: Dict[str, int]) -> None:
        """Handle successful completion of recreation process."""
        self.progress_bar.setVisible(False)
        self.session_progress.setVisible(False)
        self.start_button.setEnabled(True)

        # Show completion message
        sessions_processed = result.get("sessions_processed", 0)
        ngrams_created = result.get("ngrams_created", 0)

        completion_msg = (
            f"Ngram data recreation completed successfully!\n\n"
            f"Sessions processed: {sessions_processed}\n"
            f"Ngrams created: {ngrams_created}"
        )

        QMessageBox.information(self, "Process Complete", completion_msg)
        self.log_output.append(f"\n✅ {completion_msg.replace(chr(10), ' ')}")

        # Reload statistics
        self.load_session_stats()

    def on_recreation_error(self, error_message: str) -> None:
        """Handle errors during recreation process."""
        self.progress_bar.setVisible(False)
        self.session_progress.setVisible(False)
        self.start_button.setEnabled(True)

        QMessageBox.critical(
            self, "Process Error", f"Recreation process failed:\n\n{error_message}"
        )
        self.log_output.append(f"\n❌ Error: {error_message}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.worker is not None and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Process Running",
                "Recreation process is still running. Are you sure you want to close?",
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


def launch_recreate_ngram_data() -> None:
    """Launch the RecreateNgramData application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = RecreateNgramData()
    dialog.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_recreate_ngram_data()
