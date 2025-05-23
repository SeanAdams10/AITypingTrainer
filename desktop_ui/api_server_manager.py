"""
API Server Manager for Desktop UI

This module provides functionality to check if the GraphQL API server
is running and automatically start it if needed.
"""

import os
import subprocess
import sys
import time
from typing import Optional

import requests


class APIServerManager:
    """
    Manages the Flask GraphQL API server for the desktop UI.

    This class provides methods to check if the server is running,
    start it if needed, and shut it down.
    """

    def __init__(self) -> None:
        """Initialize the API server manager."""
        self._server_process: Optional[subprocess.Popen] = None
        self._api_url: str = "http://localhost:5000/api/library_graphql"
        self._server_script_path: str = self._get_server_script_path()

    def _get_server_script_path(self) -> str:
        """
        Get the absolute path to the API server script.

        Returns:
            str: Absolute path to the run_library_api.py script
        """
        # Get the directory of the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to project root and then to api directory
        project_root = os.path.dirname(current_dir)
        return os.path.join(project_root, "api", "run_library_api.py")

    def is_server_running(self) -> bool:
        """
        Check if the GraphQL API server is already running.

        Returns:
            bool: True if server is running, False otherwise
        """
        try:
            # Try to connect to the server
            # Even if we get a 400 error (method not allowed), it means the server is running
            response = requests.get(self._api_url, timeout=2)
            return True
        except requests.exceptions.ConnectionError:
            # Connection refused means server isn't running
            return False
        except requests.exceptions.Timeout:
            # Timeout means server might be starting up or has issues
            return False
        except Exception:
            # Any other exception means server isn't running properly
            return False

    def start_server(self) -> bool:
        """
        Start the GraphQL API server as a background process.

        Returns:
            bool: True if server was started successfully, False otherwise
        """
        try:
            # Check if python is in PATH
            python_executable = sys.executable

            # Command to run the server
            cmd = [python_executable, self._server_script_path]

            # Start server as a separate process that won't die when the desktop app closes
            self._server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,  # This keeps it running independently
            )

            # Wait a moment for the server to start
            time.sleep(2)
            return True
        except Exception as e:
            print(f"Error starting server: {e}")
            return False

    def ensure_server_running(self) -> bool:
        """
        Ensure the GraphQL API server is running, starting it if needed.

        Returns:
            bool: True if server is running or was started successfully, False otherwise
        """
        if self.is_server_running():
            return True

        return self.start_server()

    def shutdown_server(self) -> None:
        """
        Shutdown the server if it was started by this manager.
        """
        if self._server_process:
            try:
                self._server_process.terminate()
                self._server_process = None
            except Exception as e:
                print(f"Error shutting down server: {e}")


if __name__ == "__main__":
    manager = APIServerManager()
    manager.ensure_server_running()
