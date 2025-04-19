# Drill Configuration Screen Specification

## 1. Overview

The Drill Configuration screen allows users to configure and launch typing drills by selecting a text category and snippet, specifying drill indices, and choosing to start a new drill or continue from the last session. This screen is available both as a modern web UI and a desktop UI, with identical functionality and a unified backend API. All code must be robust, testable, and adhere to strict quality, validation, and security standards.

---

## 2. Functional Requirements

### 2.1 Drill Setup Workflow

- **Category Selection:**
  - On load, fetch and display all categories from the `text_category` table.
  - Selecting a category loads its available snippets.

- **Snippet Selection:**
  - Selecting a snippet fetches its total length (sum of all snippet_parts) and the user's most recent session indices (if any) from the `practice_session` table.
  - If the snippet has been typed before:
    - The default mode is 'Continue from Last Position'.
    - The start index defaults to the previous session's end index plus 1.
    - The end index defaults to the minimum of the snippet length and the previous session's end index plus 1.
    - If the previous session's end index is greater than or equal to the snippet length, the start index defaults to 0 and the end index to 300 (or the snippet length, whichever is smaller).
  - If the snippet has not been typed before:
    - The default mode is 'Start from Beginning'.
    - The start index defaults to 0 and the end index to 300 (or the snippet length, whichever is smaller).

- **Drill Indices:**
  - Users can set the start and end indices for the drill.
  - Indices are validated to ensure they are within the snippet's length and logical (start < end).

- **Drill Mode:**
  - User can choose to start from the beginning or continue from the last session.
  - UI reflects the selected mode by updating indices accordingly.

- **Launch Drill:**
  - When ready, user launches the drill with the selected parameters.
  - Errors and validation issues are shown clearly in the UI.

### 2.2 Error Handling and Validation

- All user input is validated on both frontend and backend:
  - Indices must be integers, within snippet bounds, and start < end.
  - Category and snippet selections must be valid and present in the database.
- User receives clear error messages for any validation or system errors.

---

## 3. User Interface

---

## 4. API Implementation and Structure
- All Drill Configuration API endpoints are implemented in modular API files using Flask Blueprints:
  - `category_api.py` for category endpoints
  - `snippet_api.py` for snippet endpoints
  - `session_api.py` for session info endpoints (e.g., last session indices)
- Endpoints only handle request/response, validation, and error handling.
- All business logic (category/snippet/session retrieval and validation) is handled in `db/models/category.py`, `db/models/snippet.py`, and `db/models/practice_session.py`.
- Endpoints used:
  - `GET /api/categories` — fetch all categories
  - `GET /api/snippets?category_id=<id>` — fetch snippets for a category
  - `GET /api/session/info?snippet_id=<id>` — fetch last session indices and snippet length

## 5. Testing Practices
- Unit tests for all model and service logic
- API tests for all endpoints in `tests/test_category_api.py`, `tests/test_snippet_api.py`, and `tests/test_session_api.py`
- UI tests for drill configuration flow in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized

### 3.1 Web UI
- Responsive, modern design (see `drill_config.html`).
- Category dropdown, snippet dropdown, start/end index fields, mode buttons, and launch button.
- Uses RESTful API endpoints for all data.
- Accessible from the main menu.

### 3.2 Desktop UI
- Mirrors web UI functionality and layout.
- Invoked from the desktop main menu.
- Uses the same API/backend as the web UI.

---

## 4. API & Backend

- All business logic is encapsulated in service classes (e.g., `drill_config_service.py`).
- API endpoints for fetching categories, snippets, session info, and launching drills.
- Input validation and error handling at both API and backend layers.
- Dependency injection for database access to enable test mocks.

---

## 5. Testing

- **Test-Driven Development (TDD):**
  - All features are developed test-first.
  - Pytest is used exclusively for all tests.

- **Test Coverage:**
  - Unit tests for backend and service classes.
  - API tests for all endpoints.
  - Selenium (or equivalent) tests for web UI (page load, dropdowns, drill logic, validation, error handling).
  - Desktop UI tests (functional, using UI test frameworks).

- **Test Isolation:**
  - All tests use temporary databases and pytest fixtures for setup/teardown.
  - No test uses the production DB.
  - Tables are created using the app's own DB initialization logic, not raw SQL.

- **Test File Naming:**
  - Test files are placed in the `tests` folder and named after the functionality and layer, e.g.:
    - `test_drill_config_backend.py`
    - `test_drill_config_api.py`
    - `test_drill_config_web.py`
    - `test_desktop_drill_config.py`

---

## 6. Code Quality & Security

- All code follows PEP 8, is type-hinted, and uses Pydantic for data validation.
- All user input is validated and sanitized.
- Parameterized queries are used throughout.
- No sensitive data is hardcoded.
- All code is linted (`flake8`, `black`) before submission.

---

## 7. Error Handling

- User receives meaningful error messages for all validation and system errors.
- All exceptions are logged and surfaced appropriately in the UI.

---

## 8. Documentation

- All modules, classes, and functions have docstrings with type hints.
- README and inline documentation are updated with each significant change.

---

**This specification is up-to-date with the current drill configuration implementation and testing standards.**
