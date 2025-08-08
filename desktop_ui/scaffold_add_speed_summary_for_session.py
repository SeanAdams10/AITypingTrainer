"""
ScaffoldAddSpeedSummaryForSession UI form for triggering speed summary for a specific session.

This form provides an interface to run the AddSpeedSummaryForSession method
from the NGramAnalyticsService for a specific session ID.
"""

import os
import sys
from typing import Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox, QProgressBar, QTextEdit, QLineEdit

from db.database_manager import ConnectionType, DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager_new import NGramManagerNew


class AddSpeedSummaryWorker(QThread):
    """Worker thread for running AddSpeedSummaryForSession in background."""
    
    finished = Signal(dict)  # Signal with result dictionary
    error = Signal(str)      # Signal with error message
    
    def __init__(self, analytics_service: NGramAnalyticsService, session_id: str):
        super().__init__()
        self.analytics_service = analytics_service
        self.session_id = session_id
    
    def run(self):
        try:
            result = self.analytics_service.add_speed_summary_for_session(self.session_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ScaffoldAddSpeedSummaryForSession(QtWidgets.QWidget):
    """
    UI form for triggering speed summary for a specific session.
    
    Provides an interface with session ID input and a button to run the 
    AddSpeedSummaryForSession method and displays progress and results.
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.LOCAL
    ) -> None:
        super().__init__()
        self.setWindowTitle("Add Speed Summary For Session")
        self.resize(600, 500)
        
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
        self.load_recent_sessions()
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title
        title = QtWidgets.QLabel("Add Speed Summary For Session")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Description
        description = QtWidgets.QLabel(
            "This tool calculates decaying average performance for a specific session using the last 20 sessions.\n"
            "It updates ngram_speed_summary_curr (merge) and ngram_speed_summary_hist (insert)."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(description)
        
        # Session ID input
        session_layout = QtWidgets.QHBoxLayout()
        session_label = QtWidgets.QLabel("Session ID:")
        session_label.setStyleSheet("font-weight: bold;")
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Enter session ID...")
        session_layout.addWidget(session_label)
        session_layout.addWidget(self.session_input)
        layout.addLayout(session_layout)
        
        # Recent sessions dropdown
        recent_layout = QtWidgets.QHBoxLayout()
        recent_label = QtWidgets.QLabel("Recent Sessions:")
        recent_label.setStyleSheet("font-weight: bold;")
        self.recent_sessions_combo = QtWidgets.QComboBox()
        self.recent_sessions_combo.currentTextChanged.connect(self.on_session_selected)
        recent_layout.addWidget(recent_label)
        recent_layout.addWidget(self.recent_sessions_combo)
        layout.addLayout(recent_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Process button
        self.process_button = QtWidgets.QPushButton("Process Session")
        self.process_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; padding: 10px; font-size: 14px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #1976D2; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.process_button.clicked.connect(self.start_processing)
        layout.addWidget(self.process_button)
        
        # Results text area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; padding: 5px;")
        layout.addWidget(self.results_text)
        
        # Close button
        close_button = QtWidgets.QPushButton("Close")
        close_button.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; padding: 8px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #da190b; }"
        )
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
    
    def load_recent_sessions(self):
        """Load recent sessions into the dropdown."""
        try:
            sessions = self.db_manager.fetchall(
                """
                SELECT session_id, start_time, ms_per_keystroke 
                FROM practice_sessions 
                ORDER BY start_time DESC 
                LIMIT 20
                """
            )
            
            self.recent_sessions_combo.addItem("Select a session...", "")
            for session in sessions:
                display_text = f"{session['session_id'][:8]}... ({session['start_time']}) - {session['ms_per_keystroke']:.1f}ms"
                self.recent_sessions_combo.addItem(display_text, session['session_id'])
                
        except Exception as e:
            self.results_text.append(f"Error loading sessions: {str(e)}")
    
    def on_session_selected(self, text):
        """Handle session selection from dropdown."""
        current_data = self.recent_sessions_combo.currentData()
        if current_data:
            self.session_input.setText(current_data)
    
    def start_processing(self):
        """Start the processing in a background thread."""
        session_id = self.session_input.text().strip()
        if not session_id:
            QMessageBox.warning(self, "Warning", "Please enter a session ID.")
            return
        
        self.process_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.results_text.clear()
        self.results_text.append(f"Processing session: {session_id}")
        
        # Create and start worker thread
        self.worker = AddSpeedSummaryWorker(self.analytics_service, session_id)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.start()
    
    def on_processing_finished(self, result: dict):
        """Handle successful completion of processing."""
        self.progress_bar.setVisible(False)
        self.process_button.setEnabled(True)
        
        hist_inserted = result.get('hist_inserted', 0)
        curr_updated = result.get('curr_updated', 0)
        
        self.results_text.append(f"\n✅ Processing completed successfully!")
        self.results_text.append(f"📊 {curr_updated} records updated in ngram_speed_summary_curr")
        self.results_text.append(f"📈 {hist_inserted} records inserted into ngram_speed_summary_hist")
        
        # Show success message
        QMessageBox.information(
            self,
            "Success",
            f"Speed summary processing completed successfully!\n\n"
            f"• {curr_updated} records updated in current summary\n"
            f"• {hist_inserted} records inserted into history"
        )
    
    def on_processing_error(self, error_message: str):
        """Handle errors during processing."""
        self.progress_bar.setVisible(False)
        self.process_button.setEnabled(True)
        
        self.results_text.append(f"\n❌ Error during processing:")
        self.results_text.append(f"   {error_message}")
        
        # Show error message
        QMessageBox.critical(
            self,
            "Error",
            f"An error occurred during speed summary processing:\n\n{error_message}"
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "Processing is still running. Are you sure you want to close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.terminate()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def launch_scaffold_add_speed_summary_for_session():
    """Launch the ScaffoldAddSpeedSummaryForSession application."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    window = ScaffoldAddSpeedSummaryForSession()
    window.show()
    
    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_scaffold_add_speed_summary_for_session()
