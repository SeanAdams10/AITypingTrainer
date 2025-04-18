import os
import subprocess
import sys
import time
import requests
try:
    from PyQt5 import QtWidgets, QtCore
except ImportError:
    # Allow IDE/mypy/pylint to pass if PyQt5 is not installed in some environments
    QtWidgets = None  # type: ignore
    QtCore = None  # type: ignore

"""
AI Typing Trainer launcher and splash screen for desktop and backend startup.
"""

# --- CONFIG ---
"""
AI Typing Trainer launcher and splash screen for desktop and backend startup.
"""

BACKEND_SCRIPT = "app.py"
DESKTOP_UI_SCRIPT = "desktop_ui/main_menu.py"
BACKEND_URL = "http://127.0.0.1:5000/api/categories"
BACKEND_STARTUP_TIMEOUT = 20  # seconds
BACKEND_POLL_INTERVAL = 0.5  # seconds

class SplashScreen(QtWidgets.QWidget):
    """Splash screen shown during backend initialization."""
    # pylint: disable=c-extension-no-member
    def __init__(self):
        """Initialize the splash screen UI."""
        super().__init__()
        self.setWindowTitle("AI Typing Trainer - Initializing")
        # Set splash to 840 x 400
        self.setFixedSize(840, 400)
        # Remove all window controls (no close, minimize, maximize)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel("Initializing...")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        font = self.label.font()
        font.setPointSize(18)
        self.label.setFont(font)
        layout.addWidget(self.label)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress)
        self.setLayout(layout)
        self.show()
        QtWidgets.QApplication.processEvents()

    def update_status(self, msg):
        """
        Update the splash screen status label.
        """
        self.label.setText(msg)
        QtWidgets.QApplication.processEvents()

    def close_splash(self):
        """
        Close the splash screen.
        """
        self.close()

def start_backend():
    """
    Start the backend server using the current Python interpreter.
    """
    # Use sys.executable for correct Python interpreter
    return subprocess.Popen([
        sys.executable, BACKEND_SCRIPT
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def poll_backend(timeout=BACKEND_STARTUP_TIMEOUT):
    """Poll the backend until it is available or timeout is reached."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(BACKEND_URL, timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(BACKEND_POLL_INTERVAL)
    return False

def validate_database():
    """Try API call to fetch categories (DB access via API)."""
    try:
        r = requests.get(BACKEND_URL, timeout=5)
        if r.status_code == 200:
            return True, ""
        return False, f"API responded with status {r.status_code}"
    except requests.RequestException as ex:
        return False, str(ex)

def launch_desktop_ui():
    """
    Launch the desktop UI as a subprocess.
    """
    subprocess.Popen([sys.executable, DESKTOP_UI_SCRIPT], cwd=os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main entry point for launching the splash, backend, and desktop UI."""
    app = QtWidgets.QApplication(sys.argv)
    splash = SplashScreen()
    splash.update_status("Starting backend API service...")
    backend_proc = start_backend()
    time.sleep(1)   

    splash.update_status("Waiting for backend API to become available...")    
    if not poll_backend():
        backend_proc.terminate()
        splash.update_status("Backend API failed to start.")
        time.sleep(2)
        splash.close_splash()
        return
    time.sleep(1)

    splash.update_status("Backend API is up. Validating database...")
    ok, msg = validate_database()
    if not ok:
        backend_proc.terminate()
        splash.update_status(f"Database error: {msg}")
        time.sleep(2)
        splash.close_splash()
        return
    time.sleep(1)

    splash.update_status("Launching AI Typing Trainer UI...")
    # Wait for 2 seconds before proceeding, without freezing the UI
    time.sleep(2)
    QtCore.QTimer.singleShot(2000, splash.close_splash)
    launch_desktop_ui()

if __name__ == "__main__":
    main()
