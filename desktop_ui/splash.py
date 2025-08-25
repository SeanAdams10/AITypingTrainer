"""splash.py

AI Typing Trainer Splash Screen
- Shows splash with large title and status label
- Starts GraphQL server asynchronously
- Polls server and displays snippet count in a message box.

Updated to use PySide6 instead of PyQt5.
"""

import sys
from typing import Optional

from pydantic import BaseModel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QVBoxLayout, QWidget

# Import real server manager and client
try:
    from .api_server_manager import APIServerManager
    from .graphql_client import GraphQLClient
except ImportError:
    from api_server_manager import APIServerManager
    from graphql_client import GraphQLClient

# --- Configuration ---
GRAPHQL_URL = "http://localhost:5000/api/library_graphql"


class SplashConfig(BaseModel):
    graphql_url: str = GRAPHQL_URL
    poll_interval_ms: int = 500
    max_retries: int = 20


# Remove GraphQLServerThread (no longer needed)


class SplashScreen(QWidget):
    """Splash screen for AI Typing Trainer.

    - Frameless, no minimize/close, centered, stays on top.
    - Starts and polls GraphQL server via APIServerManager.
    - Queries snippet count via GraphQLClient.
    - Retains dummy/test mode for tests.
    """

    def __init__(self, graphql=None, config: Optional[SplashConfig] = None) -> None:
        super().__init__()
        self.setWindowTitle("AI Typing Trainer")
        self.setFixedSize(400, 200)
        # Splash look: frameless, no minimize/close, stays on top
        self.setWindowFlags(
            Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        # Set white background and subtle grey border
        self.setStyleSheet(
            "background-color: white; border-radius: 10px; border: 1.5px solid #d0d0d0;"
        )
        # Center on screen
        self._center_on_screen()
        self.config = config or SplashConfig()
        layout = QVBoxLayout()
        self.title_label = QLabel("AI Typing")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "font-size: 36px; font-weight: bold; color: #222;"
        )
        layout.addWidget(self.title_label)
        self.status_label = QLabel("Starting up GraphQL")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 18px; color: #444;")
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.graphql = graphql
        self._init_startup()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = screen_geometry.center().x() - self.width() // 2
            y = screen_geometry.center().y() - self.height() // 2
            self.move(x, y)

    # Class variable to keep track of the API server manager globally
    _api_server_manager = None

    def _init_startup(self) -> None:
        if self.graphql:
            # For testing: use injected dummy GraphQL
            self._poll_graphql()
        else:
            # Real mode: use APIServerManager and GraphQLClient
            # Use the class-level server manager if it exists, otherwise create a new one
            if SplashScreen._api_server_manager is None:
                SplashScreen._api_server_manager = APIServerManager()

            self.api_server_manager = SplashScreen._api_server_manager
            self.graphql_client = GraphQLClient()
            self.status_label.setText("Starting up GraphQL")
            self._start_and_poll_server()

    def _start_and_poll_server(self) -> None:
        # Start server if not running
        if not self.api_server_manager.is_server_running():
            self.status_label.setText("Starting GraphQL server...")
            started = self.api_server_manager.start_server()
            if not started:
                self.status_label.setText("GraphQL failed to start.")
                return

            # Give the server a moment to fully initialize
            import time

            time.sleep(2)

        # Poll for availability
        self.retries = 0
        self._try_poll_real()

    def _try_poll_real(self) -> None:
        try:
            # Try a trivial query
            resp = self.graphql_client.query("{ __typename }")
            if resp and "data" in resp:
                self.status_label.setText("GraphQL Running")
                QTimer.singleShot(300, self.check_graphql_and_show_count)
                return
        except Exception as e:
            # More detailed error logging for debugging
            print(f"GraphQL polling error: {str(e)}")

        self.retries += 1
        if self.retries < self.config.max_retries:
            QTimer.singleShot(self.config.poll_interval_ms, self._try_poll_real)
        else:
            # If we've exceeded retry attempts, try restarting the server
            if self.api_server_manager and not self.graphql:
                self.status_label.setText("Restarting GraphQL server...")
                self.api_server_manager.shutdown_server()  # Shutdown any failed instance
                started = self.api_server_manager.start_server()
                if started:
                    self.retries = 0
                    QTimer.singleShot(
                        2000, self._try_poll_real
                    )  # Retry after 2 seconds
                    return

            self.status_label.setText("GraphQL failed to start.")

    def _start_graphql_server(self) -> None:
        self.status_label.setText("Starting up GraphQL")
        self.server_thread = GraphQLServerThread()
        self.server_thread.started_signal.connect(self._poll_graphql)
        self.server_thread.start()

    def _poll_graphql(self) -> None:
        # For test/dummy mode only
        self.retries = 0
        self._try_poll()

    def _try_poll(self) -> None:
        # For test/dummy mode only
        if self.graphql:
            running = self.graphql.is_running()
        else:
            running = False
        if running:
            self.status_label.setText("GraphQL Running")
            QTimer.singleShot(300, self.check_graphql_and_show_count)
        else:
            self.retries += 1
            if self.retries < self.config.max_retries:
                QTimer.singleShot(self.config.poll_interval_ms, self._try_poll)
            else:
                self.status_label.setText("GraphQL failed to start.")

    def check_graphql_and_show_count(self) -> None:
        """Check if GraphQL is running and show snippet count.
        
        If GraphQL is not running, updates status. If running, fetches snippet 
        count and shows message box.
        """
        count = 0
        error = None
        running = True
        if self.graphql:
            # Dummy/test mode
            try:
                running = self.graphql.is_running()
            except Exception as e:
                running = False
                error = str(e)
            if not running:
                self.status_label.setText("GraphQL failed to start.")
                return
            try:
                count = self.graphql.get_snippet_count()
            except Exception as e:
                error = str(e)
        else:
            # Real mode: use GraphQLClient
            try:
                resp = self.graphql_client.query("{ allSnippets { id } }")
                if resp and "data" in resp and "allSnippets" in resp["data"]:
                    count = len(resp["data"]["allSnippets"])
                else:
                    running = False
                    error = "GraphQL response missing data."
            except Exception as e:
                running = False
                error = str(e)
            if not running:
                self.status_label.setText("GraphQL failed to start.")
                return
        if error:
            QMessageBox.warning(
                self, "Error", f"Could not fetch snippet count: {error}"
            )
        else:
            QMessageBox.information(
                self, "Snippets", f"There are {count} snippets in the database."
            )


def ensure_graphql_server_running() -> bool:
    """Utility function to ensure the GraphQL server is running.

    Can be called from other parts of the application.

    Returns:
        bool: True if server is running, False otherwise
    """
    if SplashScreen._api_server_manager is None:
        SplashScreen._api_server_manager = APIServerManager()

    return SplashScreen._api_server_manager.ensure_server_running()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    sys.exit(app.exec_())
