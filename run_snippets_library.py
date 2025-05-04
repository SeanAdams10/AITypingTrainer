"""
Combined runner for the Snippets Library - launches both Desktop and Web UIs.
This script starts the API server, Desktop UI, and optionally the Web UI.
"""
import os
import sys
import argparse
import subprocess
import time
import webbrowser
from typing import List, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("SnippetsLibraryRunner")

class SnippetsLibraryRunner:
    """
    Main runner class for Snippets Library that manages all components.
    Handles starting and stopping the API server, Desktop UI, and Web UI.
    """
    def __init__(self) -> None:
        """Initialize the runner with default paths and configurations."""
        self.project_dir = Path(__file__).parent.absolute()
        self.api_script = self.project_dir / "api" / "run_library_api.py"
        self.desktop_ui_script = self.project_dir / "desktop_ui" / "library_main.py"
        self.processes: List[subprocess.Popen] = []

    def start_api_server(self) -> Optional[subprocess.Popen]:
        """
        Start the GraphQL API server.
        
        Returns:
            Optional[subprocess.Popen]: Process object for the API server, or None if startup fails
        """
        logger.info("Starting API server...")
        
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.api_script)],
                cwd=str(self.project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(process)
            
            # Wait for the server to start (max 5 seconds)
            start_time = time.time()
            while time.time() - start_time < 5:
                if process.poll() is not None:  # Process has terminated
                    stdout, stderr = process.communicate()
                    logger.error(f"API server failed to start: {stderr}")
                    return None
                
                # Check if stdout contains indication that server is running
                output = process.stdout.readline() if process.stdout else ""
                if output and "Running on" in output:
                    logger.info("API server started successfully")
                    return process
                
                time.sleep(0.1)
                
            logger.info("API server starting (continuing without confirmation)")
            return process
            
        except Exception as e:
            logger.error(f"Error starting API server: {e}")
            return None

    def start_desktop_ui(self) -> Optional[subprocess.Popen]:
        """
        Start the PyQt5 desktop UI.
        
        Returns:
            Optional[subprocess.Popen]: Process object for the desktop UI, or None if startup fails
        """
        logger.info("Starting Desktop UI...")
        
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.desktop_ui_script)],
                cwd=str(self.project_dir)
            )
            self.processes.append(process)
            logger.info("Desktop UI started")
            return process
        except Exception as e:
            logger.error(f"Error starting Desktop UI: {e}")
            return None

    def start_web_ui(self) -> Optional[subprocess.Popen]:
        """
        Start the React Web UI using npm.
        
        Returns:
            Optional[subprocess.Popen]: Process object for the web server, or None if startup fails
        """
        logger.info("Starting Web UI (npm start)...")
        
        try:
            process = subprocess.Popen(
                ["npm", "start"],
                cwd=str(self.project_dir),
                shell=True
            )
            self.processes.append(process)
            
            # Wait a bit for the dev server to start, then open the browser
            time.sleep(3)
            webbrowser.open("http://localhost:3000")
            
            logger.info("Web UI started - opening browser at http://localhost:3000")
            return process
        except Exception as e:
            logger.error(f"Error starting Web UI: {e}")
            return None

    def run(self, include_web: bool = False) -> None:
        """
        Run all components of the Snippets Library.
        
        Args:
            include_web (bool): Whether to include the web UI in addition to desktop UI
        """
        # Start API server first
        api_process = self.start_api_server()
        if not api_process:
            logger.error("Failed to start API server, exiting")
            self.cleanup()
            return
        
        # Give the API server a moment to initialize
        time.sleep(1)
        
        # Start Desktop UI
        desktop_process = self.start_desktop_ui()
        if not desktop_process:
            logger.warning("Failed to start Desktop UI")
        
        # Start Web UI if requested
        if include_web:
            web_process = self.start_web_ui()
            if not web_process:
                logger.warning("Failed to start Web UI")
        
        # Wait for the desktop UI to finish (it's the main interface)
        try:
            if desktop_process:
                desktop_process.wait()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Terminate all started processes."""
        logger.info("Cleaning up processes...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=2)
            except Exception:
                try:
                    process.kill()
                except Exception as e:
                    logger.error(f"Failed to kill process: {e}")


def main() -> None:
    """Parse command line arguments and run the Snippets Library."""
    parser = argparse.ArgumentParser(description="Run the Snippets Library (Desktop and/or Web UI)")
    parser.add_argument(
        "--web", 
        action="store_true", 
        help="Include the web UI (requires npm/Node.js)"
    )
    args = parser.parse_args()
    
    runner = SnippetsLibraryRunner()
    runner.run(include_web=args.web)


if __name__ == "__main__":
    main()
