# Database Viewer Screen Specification

## 1. Overview

The Database Viewer screen provides users with a safe, read-only interface to inspect the contents of the application's SQLite database tables. It is available as both a web UI and a desktop UI, both of which share identical functionality, design standards, and are backed by a unified API. All code and UI must be robust, testable, and adhere to strict quality, validation, and security standards.

---

## 2. Functional Requirements

### 2.1 Table Selection & Viewing

- **Table List:**
  - On load, fetch and display a list of all database tables (e.g., `categories`, `snippets`, `snippet_parts`, `practice_sessions`).
  - Table list is always up-to-date with the current database schema.

- **Table Data Display:**
  - Selecting a table displays its contents in a paginated, sortable, and scrollable grid.
  - Columns are dynamically generated from the table schema.
  - Large tables are paginated (e.g., 50 rows per page).
  - Column headers allow sorting (ascending/descending) by any column.

- **Data Safety:**
  - All data is strictly read-only—no editing, deleting, or inserting is permitted from this screen.
  - All SQL queries are parameterized and validated to prevent SQL injection.

- **Search & Filter:**
  - Users can filter results by column value (simple text match or dropdown for enums/booleans).
  - Search is case-insensitive and applies to all visible columns.

- **Export:**
  - Users can export the current table view (all or filtered rows) to CSV.

- **Error Handling:**
  - Clear error messages are shown for invalid queries, DB connection issues, or permission errors.

---

## 3. User Interface

### 3.1 Web UI
- Responsive, modern design.
- Table dropdown/list, data grid, pagination controls, search/filter bar, export button.
- Accessible from the main menu.
- Uses RESTful API endpoints for all data.

### 3.2 Desktop UI
- Mirrors web UI functionality and layout.
- Invoked from the desktop main menu.
- Uses the same API/backend as the web UI.

---

## 4. API & Backend

- All business logic is encapsulated in service classes (e.g., `DatabaseViewerService`).
- API endpoints for listing tables, fetching table data (with pagination, sorting, filtering), and exporting CSV.
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
  - Selenium (or equivalent) tests for web UI (table loading, pagination, sorting, filtering, export, error handling).
  - Desktop UI tests (functional, using UI test frameworks).

- **Test Isolation:**
  - All tests use temporary databases and pytest fixtures for setup/teardown.
  - No test uses the production DB.
  - Tables are created using the app's own DB initialization logic, not raw SQL.

- **Test File Naming:**
  - Test files are placed in the `tests` folder and named after the functionality and layer, e.g.:
    - `test_database_viewer_backend.py`
    - `test_database_viewer_api.py`
    - `test_database_viewer_web.py`
    - `test_database_viewer_desktop_ui.py`

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

**This specification is up-to-date with the current Database Viewer implementation and testing standards.**

---

## 9. API Implementation and Structure
- All Database Viewer API endpoints are implemented in `dbviewer_api.py` using a Flask Blueprint (`dbviewer_api`).
- Endpoints only handle request/response, validation, and error handling.
- All business logic (table listing, data retrieval, export, DB access) is handled in `services/DatabaseViewerService.py` and related model files.
- Endpoints:
  - `GET /api/dbviewer/tables`: List all tables
  - `GET /api/dbviewer/table?name=<table>&page=<n>&sort=<col>&filter=<expr>`: Fetch table data (with pagination, sorting, filtering)
  - `GET /api/dbviewer/export?name=<table>&filter=<expr>`: Export table data to CSV

## 10. Testing
- Unit tests for database viewer service and data logic
- API tests for all endpoints in `tests/test_dbviewer_api.py`
- UI tests for table viewing and export in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized
