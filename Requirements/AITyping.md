# AI Typing Trainer Startup & Unified Launcher Specification

## 1. Overview

The AI Typing Trainer unified launcher (`ai_typing.py`) provides a robust, user-friendly, and testable startup process for the entire application on the desktop. It ensures all backend services and the database are available before launching the main desktop UI, and gives clear feedback to the user at each step. The startup UI is implemented with PySide6 for consistency and automated testability.

---

## 2. Functional Requirements

### 2.1 Startup Process

- **Splash/Status UI:**
  - On launch, show a PySide6-based splash/status window with live status updates and an indeterminate progress bar.
  - The splash window must be exactly 2x the original width and height (original: 420x120px; new: 840x240px).
  - The splash window must have **no window controls**: no close, minimize, maximize, or system menu (use `Qt.FramelessWindowHint`).
  - The window remains visible until all checks are complete.

- **Backend API Startup:**
  - Launch the backend API (Flask server, `app.py`) in a subprocess using the same Python interpreter as the launcher.
  - Display status: "Starting backend API service..."

- **Backend Health Check:**
  - Poll the backend API endpoint (e.g., `/api/library/categories`) until it is available, with a configurable timeout and retry interval.
  - Display status: "Waiting for backend API to become available..."
  - If the backend fails to start, show a detailed error dialog and do not proceed to UI launch.

- **Database Validation:**
  - Once the API is up, validate database connectivity by making an API call that requires DB access.
  - Display status: "Validating database connection..."
  - If validation fails, show a detailed error dialog and do not proceed.

- **UI Launch:**
  - If all checks succeed, close the splash/status window and launch the main desktop UI (`desktop_ui.py`).
  - Display status: "Launching AI Typing Trainer UI..."

- **Error Handling:**
  - All errors are presented to the user via PySide6 dialogs with clear, actionable messages.
  - If any step fails, the backend subprocess is terminated and the desktop UI is not launched.

---

## 3. UI/UX Requirements

- **Splash/Status Window:**
  - Uses PySide6 for the UI.
  - Shows the current step/status and a progress bar.
  - Window is fixed size (840x240), centered, and **cannot be closed, minimized, or maximized** by the user during startup (no window controls, no system menu).
  - All status updates are visible to the user in real time.

- **Error Dialogs:**
  - Use `QMessageBox.critical` for errors.
  - Provide detailed, user-friendly error messages and troubleshooting hints.

- **Consistency:**
  - The look and feel of the splash/status window matches other PySide6-based screens in the application.

---

## 4. Implementation & Testability

---

## 5. API Implementation and Structure
- The unified launcher (`ai_typing.py`) starts the backend API server via `app.py`, which only registers blueprints for modular API files (e.g., `category_api.py`, `snippet_api.py`, etc.).
- All API endpoints are organized by object in their own files using Flask Blueprints.
- Each API file only handles request/response, validation, and error handling.
- All business logic and DB access are handled in models and service classes, not in the API files.
- The launcher checks backend and DB readiness by polling API endpoints (e.g., `/api/categories`).

## 6. Testing Practices
- Unit tests for launcher logic, backend API, and models/services
- Integration tests for startup sequence and error handling
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized

- **PySide6 is required** for all UI elements in the startup process.
- **Backend API** must be started in a subprocess and health-checked via HTTP requests.
- **Database validation** should be performed via an API call, not direct DB access from the launcher.
- **Automated tests** (pytest + pytest-qt or similar) must be able to:
  - Simulate backend startup success/failure.
  - Simulate database validation success/failure.
  - Verify correct status messages and error dialogs are shown.
  - Ensure the backend subprocess is terminated on failure.

---

## 5. Non-Functional Requirements

- **Performance:**
  - The entire startup process should complete (in the success case) within 30 seconds.
- **Robustness:**
  - All subprocesses are managed and cleaned up to prevent orphaned processes.
- **User Feedback:**
  - The user is never left wondering about the application's status; all progress and errors are clearly communicated.
- **Portability:**
  - The launcher works on Windows and other platforms supported by PySide6 and Python subprocess.

---

## 6. Example User Flow

1. User double-clicks `ai_typing.py` or launches it from the terminal.
2. Splash/status window appears: "Starting backend API service..."
3. Status updates: "Waiting for backend API to become available..."
4. Status updates: "Validating database connection..."
5. Status updates: "Launching AI Typing Trainer UI..."
6. Splash closes, main desktop UI appears.
7. If any error occurs, a detailed dialog is shown and the process exits cleanly.

---

## 7. Extensibility & Maintenance

- The launcher should be easy to extend for additional pre-flight checks (e.g., config validation, network checks).
- All status messages and error dialogs should be easy to update for future UX improvements.

---

**This specification is up-to-date with current implementation and testability standards, and is modeled after the robust approach used for the Snippets Library.**
