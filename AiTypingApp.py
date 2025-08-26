"""AI Typing Trainer Application Entry Point.

This module serves as the main entry point for the AI Typing Trainer application.
It handles:
- Displaying a splash screen during startup
- Starting and verifying the GraphQL API server
- Starting and verifying the web server
- Launching both desktop UI and web UI main menus

All operations follow robust error handling with clear user feedback.
"""

import os
import subprocess
import sys
import time
import webbrowser
from typing import List, Optional

import requests
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QDesktopWidget,
    QDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

# Import desktop_ui components
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from desktop_ui.main_menu import MainMenuWindow

# Constants
API_SERVER_URL = "http://localhost:5000/api/library_graphql"
WEB_SERVER_URL = "http://localhost:3000"
API_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "api", "run_library_api.py"
)


class ServerWorker(QThread):
    """Worker thread for running servers asynchronously."""

    status_update = pyqtSignal(str)
    server_started = pyqtSignal(bool)

    def __init__(
        self,
        server_type: str,
        script_path: Optional[str] = None,
        cwd: Optional[str] = None,
        npm_command: Optional[List[str]] = None,
    ) -> None:
        """Initialize the server worker.

        Args:
            server_type: Type of server ("api" or "web")
            script_path: Path to the Python script to run (for API server)
            cwd: Current working directory for the process
            npm_command: Command to run for npm-based servers (for web server)
        """
        super().__init__()
        self.server_type = server_type
        self.script_path = script_path
        self.cwd = cwd if cwd else os.path.dirname(os.path.abspath(__file__))
        self.npm_command = npm_command
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False

    def run(self) -> None:
        """Run the server process."""
        try:
            if self.server_type == "api" and self.script_path:
                self.status_update.emit("Starting GraphQL API server...")

                # Get Python executable path
                python_exe = sys.executable

                # Start the API server process
                self.process = subprocess.Popen(
                    [python_exe, self.script_path],
                    cwd=self.cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Wait a bit before checking
                time.sleep(2)

                # Check if the API server is running
                try:
                    response = requests.post(
                        API_SERVER_URL, json={"query": "{__schema{types{name}}}"}
                    )
                    if response.status_code == 200:
                        self.is_running = True
                        self.status_update.emit("GraphQL API server running")
                        self.server_started.emit(True)
                    else:
                        self.status_update.emit(
                            f"API server returned status {response.status_code}"
                        )
                        self.server_started.emit(False)
                except requests.RequestException:
                    self.status_update.emit("Waiting for API server...")
                    # Keep trying for a few more seconds
                    for _ in range(10):
                        time.sleep(1)
                        try:
                            response = requests.post(
                                API_SERVER_URL,
                                json={"query": "{__schema{types{name}}}"},
                            )
                            if response.status_code == 200:
                                self.is_running = True
                                self.status_update.emit("GraphQL API server running")
                                self.server_started.emit(True)
                                return
                        except requests.RequestException:
                            pass

                    self.status_update.emit("Failed to start GraphQL API server")
                    self.server_started.emit(False)

            elif self.server_type == "web" and self.npm_command:
                self.status_update.emit("Starting web server...")

                # Start the web server process
                self.process = subprocess.Popen(
                    self.npm_command,
                    cwd=self.cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=True,
                )

                # Wait for web server to start
                time.sleep(3)

                # Check if web server is running
                for _ in range(15):  # Try for about 15 seconds
                    try:
                        response = requests.get(WEB_SERVER_URL, timeout=1)
                        if response.status_code == 200:
                            self.is_running = True
                            self.status_update.emit("Web server running")
                            self.server_started.emit(True)
                            return
                    except requests.RequestException:
                        pass

                    self.status_update.emit("Waiting for web server...")
                    time.sleep(1)

                self.status_update.emit("Failed to start web server")
                self.server_started.emit(False)

        except Exception as e:
            self.status_update.emit(f"Error: {str(e)}")
            self.server_started.emit(False)

    def stop(self) -> None:
        """Stop the server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

            self.is_running = False


class SplashScreen(QDialog):
    """Splash screen dialog that displays during application startup.
    Shows status updates while servers are being initialized.
    """

    def __init__(self) -> None:
        """Initialize the splash screen dialog."""
        super().__init__()

        # Remove window borders and title bar
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setModal(True)

        # Set size and position
        self.setFixedSize(500, 300)
        self.center_on_screen()

        # Set up the UI
        self.setup_ui()

        # Initialize server status
        self.api_server_running = False
        self.web_server_running = False

        # Create server workers
        self.api_worker = ServerWorker(server_type="api", script_path=API_SCRIPT_PATH)
        self.api_worker.status_update.connect(self.update_status)
        self.api_worker.server_started.connect(self.api_server_status)

        self.web_worker = ServerWorker(
            server_type="web",
            cwd=os.path.dirname(os.path.abspath(__file__)),
            npm_command=["npm", "start"],
        )
        self.web_worker.status_update.connect(self.update_status)
        self.web_worker.server_started.connect(self.web_server_status)

        # Start initialization sequence
        self.start_initialization()

    def setup_ui(self) -> None:
        """Set up the splash screen UI elements."""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Set background color
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        # Title label
        title_label = QLabel("AI Typing")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 28, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(title_label)

        # Add spacer
        layout.addSpacing(40)

        # Status label
        self.status_label = QLabel("Starting up...")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("Arial", 14)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet("color: #cccccc;")
        layout.addWidget(self.status_label)

        # Add spacer
        layout.addSpacing(40)

        # Progress indicator (just a label for now)
        self.progress_label = QLabel("Please wait...")
        self.progress_label.setAlignment(Qt.AlignCenter)
        progress_font = QFont("Arial", 12)
        self.progress_label.setFont(progress_font)
        self.progress_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.progress_label)

        # Add a horizontal line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555555;")
        layout.addWidget(line)

        # Version label
        version_label = QLabel("Version 1.0.0")
        version_label.setAlignment(Qt.AlignRight)
        version_font = QFont("Arial", 10)
        version_label.setFont(version_font)
        version_label.setStyleSheet("color: #888888;")
        layout.addWidget(version_label)

        self.setLayout(layout)

    def center_on_screen(self) -> None:
        """Center the splash screen on the monitor."""
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            int((screen.width() - size.width()) / 2),
            int((screen.height() - size.height()) / 2),
        )

    def start_initialization(self) -> None:
        """Start the initialization sequence."""
        # Show the splash screen for 1 second
        QTimer.singleShot(1000, self.check_api_server)

    def check_api_server(self) -> None:
        """Check if the GraphQL API server is already running."""
        self.update_status("Checking if GraphQL API server is running...")

        try:
            response = requests.post(
                API_SERVER_URL, json={"query": "{__schema{types{name}}}"}, timeout=2
            )
            if response.status_code == 200:
                self.update_status("GraphQL API server is already running")
                self.api_server_running = True
                # Move to web server check
                QTimer.singleShot(500, self.check_web_server)
            else:
                # Start the API server
                self.api_worker.start()
        except requests.RequestException:
            # API server is not running, start it
            self.api_worker.start()

    def api_server_status(self, success: bool) -> None:
        """Handle API server status updates."""
        self.api_server_running = success
        if success:
            # Move to web server check
            QTimer.singleShot(500, self.check_web_server)
        else:
            self.update_status("Failed to start GraphQL API server. Please check logs.")
            # Show error and exit
            QTimer.singleShot(3000, self.close)

    def check_web_server(self) -> None:
        """Check if the web server is already running."""
        self.update_status("Checking if web server is running...")

        try:
            response = requests.get(WEB_SERVER_URL, timeout=2)
            if response.status_code == 200:
                self.update_status("Web server is already running")
                self.web_server_running = True
                # All servers are running, finalize
                QTimer.singleShot(500, self.finalize_startup)
            else:
                # Start the web server
                self.web_worker.start()
        except requests.RequestException:
            # Web server is not running, start it
            self.web_worker.start()

    def web_server_status(self, success: bool) -> None:
        """Handle web server status updates."""
        self.web_server_running = success
        if success:
            # All servers are running, finalize
            QTimer.singleShot(500, self.finalize_startup)
        else:
            self.update_status("Failed to start web server. Please check logs.")
            # Show error but continue with desktop UI only
            QMessageBox.warning(
                None,
                "Web Server Error",
                "Could not start the web server. Desktop UI will still be available.",
            )
            QTimer.singleShot(1000, self.finalize_startup)

    def finalize_startup(self) -> None:
        """Final steps before showing the main menu."""
        self.update_status("Almost there...")

        # Wait a moment for visual effect
        QTimer.singleShot(1000, self.launch_main_menu)

    def launch_main_menu(self) -> None:
        """Launch the main menu screens."""
        # Launch Web UI in browser if available
        if self.web_server_running:
            try:
                webbrowser.open(WEB_SERVER_URL)
            except Exception as e:
                print(f"Error opening web browser: {e}")

        # Signal the main app to show the desktop menu
        self.accept()

    def update_status(self, message: str) -> None:
        """Update the status message on the splash screen."""
        self.status_label.setText(message)
        QApplication.processEvents()


class AiTypingApp:
    """Main application class for AI Typing Trainer.
    Handles application startup, server initialization, and UI display.
    """

    def __init__(self) -> None:
        """Initialize the application."""
        self.app = QApplication(sys.argv)

        # Set application-wide font
        QFontDatabase.addApplicationFont("./assets/fonts/Roboto-Regular.ttf")
        self.app.setFont(QFont("Roboto", 10))

        # Initialize servers and main window
        self.main_window: Optional[MainMenuWindow] = None
        self.api_worker: Optional[ServerWorker] = None
        self.web_worker: Optional[ServerWorker] = None

    def start(self) -> int:
        """Start the application.

        Returns:
            int: Application exit code
        """
        # Show splash screen
        splash = SplashScreen()
        result = splash.exec_()

        if result == QDialog.Accepted:
            # Create and show the main menu window
            self.main_window = MainMenuWindow()
            self.main_window.show()

            # Store references to server workers to keep them alive
            self.api_worker = splash.api_worker
            self.web_worker = splash.web_worker

            # Run the application
            return self.app.exec_()
        else:
            # Splash screen was rejected, exit
            return 1

    def cleanup(self) -> None:
        """Clean up resources before exiting."""
        # Stop server processes
        if self.api_worker:
            self.api_worker.stop()

        if self.web_worker:
            self.web_worker.stop()


if __name__ == "__main__":
    # Create and start the application
    app = AiTypingApp()
    exit_code = app.start()

    # Clean up before exiting
    app.cleanup()

    # Exit with the appropriate code
    sys.exit(exit_code)
