"""ScaffoldRecreateNgramData UI form for recreating ngram data from session keystrokes.

This form provides an interface to find all practice sessions that don't have
corresponding ngram data and recreate the ngrams from their keystrokes.
"""

# Standard library imports
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional, cast
from uuid import UUID

# Third-party imports
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGroupBox,
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
from models.ngram import MAX_NGRAM_SIZE, MIN_NGRAM_SIZE, SpeedMode  # noqa: E402
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
            db_manager: Database manager for data operations.
            ngram_manager: N-gram manager for processing n-gram data.
        """
        super().__init__()
        self.db_manager = db_manager
        self.ngram_manager = ngram_manager

    def run(self) -> None:
        """Execute the n-gram data recreation process in a background thread."""
        try:
            result = self.recreate_ngram_data_with_progress()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def recreate_ngram_data_with_progress(self) -> Dict[str, int]:
        """Recreate ngram data for all sessions missing ngram data."""
        logger = logging.getLogger(__name__)
        logger.info("Starting recreate ngram data process")

        # Find all sessions that are missing speed OR error n-grams (either side)
        sessions = self.db_manager.fetchall(
            """
            WITH ngram_sessions AS (
                SELECT session_id FROM session_ngram_speed
                UNION
                SELECT session_id FROM session_ngram_errors
            ), distinct_sessions AS (
                SELECT DISTINCT session_id
                FROM ngram_sessions
            )
            SELECT DISTINCT ps.session_id, ps.start_time, ps.user_id, ps.keyboard_id
            FROM practice_sessions ps
            LEFT OUTER JOIN distinct_sessions ns
                ON ps.session_id = ns.session_id
            WHERE ns.session_id IS NULL
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
            session_id = cast(str, session["session_id"])  # rows are Mapping[str, object]
            start_time = session["start_time"]

            # Emit progress signal with session info
            session_info = f"Session {session_id[:8]}... - {start_time}"
            self.session_processed.emit(session_info, i, total_sessions)

            try:
                # Load keystrokes for this session
                keystrokes = self.db_manager.fetchall(
                    """
                    SELECT keystroke_char, expected_char, keystroke_time, is_error 
                    FROM session_keystrokes 
                    WHERE session_id = ? 
                    ORDER BY keystroke_time ASC
                    """,
                    (session_id,),
                )

                if not keystrokes:
                    logger.warning("No keystrokes found for session %s", session_id)
                    continue

                # Reconstruct expected_text from expected_char stream and build new Keystrokes
                expected_text = "".join(cast(str, ks_row["expected_char"]) for ks_row in keystrokes)

                def _parse_ts(v: object) -> datetime:  # local helper
                    if isinstance(v, datetime):
                        return v
                    try:
                        return datetime.fromisoformat(str(v))
                    except Exception:  # pragma: no cover
                        return datetime.strptime(str(v), "%Y-%m-%d %H:%M:%S.%f")

                # Build KeystrokeCollection instead of a plain list
                ks_objects = KeystrokeCollection()
                for idx, ks in enumerate(keystrokes):
                    ks_objects.add_keystroke(
                        Keystroke(
                            session_id=str(session_id),  # ensure str for model expectation
                            keystroke_char=cast(str, ks["keystroke_char"]),
                            expected_char=cast(str, ks["expected_char"]),
                            keystroke_time=_parse_ts(ks["keystroke_time"]),
                            is_error=bool(ks["is_error"]),
                            text_index=idx,
                        )
                    )

                # Analyze once, then selectively persist via new manager (filter sizes 2-5)
                spd, err = self.ngram_manager.analyze(
                    session_id=UUID(str(session_id)),
                    expected_text=expected_text,
                    keystrokes=ks_objects,
                    speed_mode=SpeedMode.NET,
                )
                spd = [s for s in spd if MIN_NGRAM_SIZE <= s.size <= MAX_NGRAM_SIZE]
                err = [e for e in err if MIN_NGRAM_SIZE <= e.size <= MAX_NGRAM_SIZE]

                # Determine which sides are already present for this session to avoid duplicates
                has_speed = self.db_manager.fetchone(
                    "SELECT 1 FROM session_ngram_speed WHERE session_id = ? LIMIT 1", (session_id,)
                )
                has_errors = self.db_manager.fetchone(
                    "SELECT 1 FROM session_ngram_errors WHERE session_id = ? LIMIT 1", (session_id,)
                )

                spd_to_persist = [] if has_speed else spd
                err_to_persist = [] if has_errors else err

                # If both already present (race/changed filter), skip persisting
                if not spd_to_persist and not err_to_persist:
                    logger.info(
                        "Session %s already has both speed and error ngrams; skipping", session_id
                    )
                    continue

                spd_count, err_count = self.ngram_manager.persist_all(
                    spd_to_persist, err_to_persist
                )
                total_ngrams_created += spd_count + err_count
                processed_sessions += 1

                logger.info(
                    "Processed session %s: %d ngrams created", session_id, spd_count + err_count
                )

            except Exception as e:  # pylint: disable=broad-except
                logger.error("Error processing session %s: %s", session_id, e)
                # Continue with next session rather than failing completely
                continue

        summary: Dict[str, int] = {
            "total_sessions": total_sessions,
            "processed_sessions": processed_sessions,
            "total_ngrams_created": total_ngrams_created,
        }

        logger.info(
            "Recreate ngram data completed: %d/%d sessions processed, %d total ngrams created",
            processed_sessions,
            total_sessions,
            total_ngrams_created,
        )

        return summary


class ScaffoldRecreateNgramData(QDialog):
    """UI form for recreating ngram data from session keystrokes.

    Provides an interface with a button to run the recreate process
    and displays progress and results in real-time.
    """

    def __init__(
        self, db_path: Optional[str] = None, connection_type: ConnectionType = ConnectionType.CLOUD
    ) -> None:
        """Initialize the dialog, DB connection, and related services.

        Args:
            db_path: Optional path to the SQLite database file.
            connection_type: Database connection type (local or cloud).
        """
        super().__init__()
        self.setWindowTitle("Recreate Ngram Data")
        self.resize(700, 500)

        # Initialize database connection
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")

        self.db_manager = DatabaseManager(db_path, connection_type=connection_type)
        self.db_manager.init_tables()

        # Initialize services
        self.ngram_manager = NGramManager(self.db_manager)
        self.analytics_service = NGramAnalyticsService(self.db_manager, self.ngram_manager)

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
            "ngram data and recreates the ngrams from their keystrokes. Sessions "
            "are processed from oldest to newest to maintain chronological order."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)

        # Stats section
        stats_group = QGroupBox("Session Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("Loading session statistics...")
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
        self.recreate_button = QPushButton("Recreate Ngram Data")
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
            ("background-color: #f5f5f5; border: 1px solid #ddd; padding: 5px;")
        )
        layout.addWidget(self.results_text)

        # Close button
        close_button = QPushButton("Close")
        close_button.setStyleSheet(
            (
                "QPushButton { "
                "background-color: #f44336; "
                "color: white; "
                "padding: 8px; "
                "border-radius: 5px; "
                "} "
                "QPushButton:hover { background-color: #da190b; }"
            )
        )
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def load_session_stats(self) -> None:
        """Load and display session statistics."""
        try:
            # Get total sessions
            total_row = self.db_manager.fetchone(
                """
                SELECT COUNT(*) AS count 
                FROM practice_sessions
                """
            )
            total_count = total_row.get("count") if total_row else None
            total_sessions = int(cast(int, total_count)) if total_count is not None else 0

            # Get sessions with ngram data
            sessions_row = self.db_manager.fetchone(
                """
                WITH ngram_sessions AS (
                    SELECT session_id FROM session_ngram_speed
                    UNION
                    SELECT session_id FROM session_ngram_errors
                )
                SELECT COUNT(DISTINCT ns.session_id) AS count 
                FROM ngram_sessions ns
                INNER JOIN practice_sessions ps
                    ON ps.session_id = ns.session_id
                """
            )
            ses_count = sessions_row.get("count") if sessions_row else None
            sessions_with_ngrams = int(cast(int, ses_count)) if ses_count is not None else 0

            # Get sessions without ngram data
            sessions_without_row = self.db_manager.fetchone(
                """
                WITH ngram_sessions AS (
                    SELECT session_id FROM session_ngram_speed
                    UNION
                    SELECT session_id FROM session_ngram_errors
                )
                SELECT COUNT(DISTINCT ps.session_id) AS count 
                FROM practice_sessions ps
                LEFT OUTER JOIN ngram_sessions ns
                    ON ps.session_id = ns.session_id
                WHERE ns.session_id IS NULL
                """
            )
            without_count = sessions_without_row.get("count") if sessions_without_row else None
            sessions_without_ngrams = (
                int(cast(int, without_count)) if without_count is not None else 0
            )

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
        worker = self.worker
        assert worker is not None
        worker.finished.connect(self.on_recreate_finished)
        worker.error.connect(self.on_recreate_error)
        worker.session_processed.connect(self.on_session_processed)
        worker.start()

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

    def on_recreate_finished(self, result: Dict[str, int]) -> None:
        """Handle successful completion and present a summary to the user."""
        self.progress_bar.setValue(100)
        self.recreate_button.setEnabled(True)
        total_sessions = int(result.get("total_sessions", 0))
        processed_sessions = int(result.get("processed_sessions", 0))
        total_ngrams_created = int(result.get("total_ngrams_created", 0))
        self.results_text.append("\n" + "=" * 60)
        self.results_text.append("✅ Ngram data recreation completed successfully!")
        self.results_text.append(
            f"📊 Sessions processed: {processed_sessions}/{total_sessions}"  # noqa: E501
        )
        self.results_text.append(f"📈 Total ngrams created: {total_ngrams_created}")
        self.load_session_stats()
        QMessageBox.information(
            self,
            "Success",
            (
                "Ngram data recreation completed successfully!\n\n"
                f"• Sessions processed: {processed_sessions}/{total_sessions}\n"
                f"• Total ngrams created: {total_ngrams_created}"
            ),
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
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = ScaffoldRecreateNgramData()
    dialog.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_scaffold_recreate_ngram_data()
