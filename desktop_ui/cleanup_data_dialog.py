"""CleanupDataDialog UI for managing data cleanup and regeneration operations.

This dialog provides options to:
- Delete all derived data (ngrams, analytics, summaries)
- Recreate ngrams from session keystrokes
- Recreate session summaries
- Recreate ngram statistics
"""

import os
import sys
from typing import Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from db.database_manager import ConnectionType, DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


class CleanupDataDialog(QDialog):
    """Dialog for managing data cleanup and regeneration operations.

    Provides a centralized interface for cleaning up derived data
    and regenerating it using various scaffold tools.
    """

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget] = None,
        db_path: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.CLOUD,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clean Up Data")
        self.setModal(True)
        self.resize(600, 500)

        # Initialize database connection
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "typing_data.db")

        self.db_manager = DatabaseManager(db_path, connection_type=connection_type)
        self.db_manager.init_tables()

        # Initialize services
        self.ngram_manager = NGramManager(self.db_manager)
        self.analytics_service = NGramAnalyticsService(self.db_manager, self.ngram_manager)

        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Data Cleanup and Regeneration")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        description = QLabel(
            "This tool provides options to clean up derived data and regenerate it from "
            "source data. Use these tools carefully as they will delete existing "
            "analytics and summary data."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666; text-align: center;")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        # Delete Operations Group
        delete_group = QGroupBox("Delete Operations")
        delete_layout = QVBoxLayout(delete_group)

        # Delete all derived data button
        self.delete_all_button = QPushButton("Delete All Derived Data")
        self.delete_all_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 10px; "
            "font-size: 14px; border-radius: 5px; margin: 5px; }"
            "QPushButton:hover { background-color: #da190b; }"
        )
        self.delete_all_button.clicked.connect(self.delete_all_derived_data)
        delete_layout.addWidget(self.delete_all_button)

        delete_info = QLabel(
            "⚠️ This will delete ALL derived data including:\n"
            "• All ngram data (session_ngram_speed, session_ngram_errors)\n"
            "• All analytics data (ngram_speed_hist, ngram_speed_summary_*)\n"
            "• All session summaries (session_ngram_summary)"
        )
        delete_info.setStyleSheet("color: #d32f2f; font-size: 12px; margin: 5px; padding: 5px;")
        delete_layout.addWidget(delete_info)

        layout.addWidget(delete_group)

        # Regeneration Operations Group
        regen_group = QGroupBox("Regeneration Operations")
        regen_layout = QVBoxLayout(regen_group)

        # Recreate ngrams button
        self.recreate_ngrams_button = QPushButton("Recreate Ngrams")
        self.recreate_ngrams_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 10px; "
            "font-size: 14px; border-radius: 5px; margin: 5px; }"
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self.recreate_ngrams_button.clicked.connect(self.recreate_ngrams)
        regen_layout.addWidget(self.recreate_ngrams_button)

        # Recreate session summaries button
        self.recreate_summaries_button = QPushButton("Recreate Session Summaries")
        self.recreate_summaries_button.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; padding: 10px; "
            "font-size: 14px; border-radius: 5px; margin: 5px; }"
            "QPushButton:hover { background-color: #F57C00; }"
        )
        self.recreate_summaries_button.clicked.connect(self.recreate_session_summaries)
        regen_layout.addWidget(self.recreate_summaries_button)

        # Recreate ngram stats button
        self.recreate_stats_button = QPushButton("Recreate Ngram Statistics")
        self.recreate_stats_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; "
            "font-size: 14px; border-radius: 5px; margin: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        self.recreate_stats_button.clicked.connect(self.recreate_ngram_stats)
        regen_layout.addWidget(self.recreate_stats_button)

        regen_info = QLabel(
            "ℹ️ Regeneration operations will:\n"
            "• Process data from oldest to newest sessions\n"
            "• Show progress and results in real-time\n"
            "• Skip sessions that already have the required data"
        )
        regen_info.setStyleSheet("color: #1976D2; font-size: 12px; margin: 5px; padding: 5px;")
        regen_layout.addWidget(regen_info)

        layout.addWidget(regen_group)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.setStyleSheet(
            "QPushButton { background-color: #757575; color: white; padding: 8px 20px; "
            "border-radius: 5px; margin: 10px; }"
            "QPushButton:hover { background-color: #616161; }"
        )
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def delete_all_derived_data(self) -> None:
        """Delete all derived data after user confirmation."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete All Derived Data",
            "⚠️ WARNING: This will permanently delete ALL derived data including:\n\n"
            "• All ngram data (session_ngram_speed, session_ngram_errors)\n"
            "• All analytics data (ngram_speed_hist, ngram_speed_summary_*)\n"
            "• All session summaries (session_ngram_summary)\n\n"
            "This operation cannot be undone. Are you sure you want to continue?\n\n"
            "You can regenerate this data using the regeneration tools below.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete ngram data via new manager
                self.ngram_manager.delete_all_ngrams()
                ngram_success = True

                # Delete analytics data
                analytics_success = self.analytics_service.delete_all_analytics_data()

                if ngram_success and analytics_success:
                    QMessageBox.information(
                        self,
                        "Success",
                        "✅ All derived data has been successfully deleted.\n\n"
                        "You can now use the regeneration tools to recreate the data.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Partial Success",
                        "⚠️ Some data deletion operations may have failed.\n"
                        "Please check the logs for details.",
                    )

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"❌ An error occurred while deleting derived data:\n\n{str(e)}"
                )

    def recreate_ngrams(self) -> None:
        """Launch the recreate ngrams scaffold screen."""
        try:
            from desktop_ui.scaffold_recreate_ngram_data import ScaffoldRecreateNgramData

            dialog = ScaffoldRecreateNgramData(
                db_path=self.db_manager.db_path, connection_type=self.db_manager.connection_type
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"❌ Failed to launch recreate ngrams tool:\n\n{str(e)}"
            )

    def recreate_session_summaries(self) -> None:
        """Launch the session summaries scaffold screen."""
        try:
            from desktop_ui.scaffold_summarize_session_ngrams import ScaffoldSummarizeSessionNgrams

            dialog = ScaffoldSummarizeSessionNgrams(
                db_path=self.db_manager.db_path, connection_type=self.db_manager.connection_type
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"❌ Failed to launch session summaries tool:\n\n{str(e)}"
            )

    def recreate_ngram_stats(self) -> None:
        """Launch the ngram stats catchup scaffold screen."""
        try:
            from desktop_ui.scaffold_catchup_speed_summary import ScaffoldCatchupSpeedSummary

            dialog = ScaffoldCatchupSpeedSummary(
                db_path=self.db_manager.db_path, connection_type=self.db_manager.connection_type
            )
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"❌ Failed to launch ngram stats tool:\n\n{str(e)}"
            )


def launch_cleanup_data_dialog(parent: Optional[QtWidgets.QWidget] = None) -> None:
    """Launch the CleanupDataDialog."""
    dialog = CleanupDataDialog(parent)
    dialog.exec()


if __name__ == "__main__":
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    launch_cleanup_data_dialog()

    if app is not None:
        app.exec()
