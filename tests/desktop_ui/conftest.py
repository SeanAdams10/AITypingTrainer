import pytest
import subprocess
import time
import requests

BACKEND_URL = "http://127.0.0.1:5000/api/categories"

@pytest.fixture(scope="session", autouse=True)
def flask_backend():
    """
    Launch the Flask backend in test mode (in-memory DB) for UI tests.
    Ensures the backend is started only once per test session and is shut down at the end.
    """
    # Start backend with test DB (ensure app.py supports test DB via env var or CLI)
    proc = subprocess.Popen([
        "python", "-m", "AITypingTrainer.app", "--test-db"
    ])
    # Wait for backend to be ready
    for _ in range(40):
        try:
            r = requests.get(BACKEND_URL)
            if r.status_code in (200, 404):
                break
        except Exception:
            pass
        time.sleep(0.25)
    else:
        proc.terminate()
        raise RuntimeError("Flask backend did not start in time")
    yield
    proc.terminate()
    proc.wait()
