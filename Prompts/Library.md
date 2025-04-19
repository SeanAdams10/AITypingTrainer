# Snippets Library Specification

## 1. Overview

The Snippets Library enables users to manage text categories and snippets through both a modern web UI and a desktop UI. Both interfaces share identical functionality, leverage a unified API/backend, and are fully testable with pytest (including Selenium or any other web testing framework for web UI). All database operations use dependency injection for testability and follow robust validation, error handling, and security standards.

---

## 2. Functional Requirements

### 2.1 Categories Management

- **Display:**  
  - On load, fetch and display all categories from the `text_category` table.
  - Selecting a category loads its snippets in the adjacent pane.

- **Add Category:**  
  - Opens a modal for category name input.
  - On confirmation, validates and inserts a new record into `text_category` with a unique `category_id`.

- **Edit Category:**  
  - Opens a modal with the current name pre-filled.
  - On confirmation, validates and updates the category name in `text_category`.

- **Delete Category:**  
  - Prompts for confirmation.
  - Deletes the category and all associated snippets and snippet parts from `text_category`, `text_snippets`, and `snippet_parts`.

- **Validation:**  
  - Category names must:
    - Be non-null, non-blank, and ≤ 50 ASCII characters.
    - Be unique.
  - User receives clear warnings if validation fails.

---

### 2.2 Snippets Management

- **Display:**  
  - Selecting a category loads its snippets from `text_snippets` by `category_id`.
  - The main library_manager.py window opens in fullscreen (maximized) mode by default for maximum workspace.

- **Add Snippet:**  
  - Modal for snippet name and text.
  - The Add Snippet dialog is always shown fullscreen (maximized) by default for both desktop and web UIs.
  - On confirmation:
    - Validates input.
    - Inserts into `text_snippets` (unique `snippet_id`, `snippet_name`).
    - Splits text into ≤1000 character parts, inserts into `snippet_parts` with unique `part_id` and sequential `part_number`.

- **Edit Snippet:**  
  - Opens a modal for editing snippet name, text, and category (including moving the snippet to a different category).
  - The Edit Snippet dialog is always shown fullscreen (maximized) by default for both desktop and web UIs.
  - Every time the snippet text field loses focus, validation is triggered for non-ASCII characters. If any non-ASCII character is found, the user is warned, focus is immediately returned to the text box, and the first non-ASCII character is highlighted for correction. The user cannot proceed until all non-ASCII characters are removed.
  - On confirmation:
    - Updates `snippet_parts` and allows moving to another category by updating the `category_id` of the snippet record.

- **Delete Snippet:**  
  - Deletes the snippet and all its parts from `text_snippets` and `snippet_parts`.

- **Validation:**  
  - Snippet names must:
    - Be non-null, non-blank, contain alphanumeric characters, ≤ 50 ASCII characters, and be unique.
  - Snippet text:
    - Must contain only ASCII (US keyboard) characters.
    - Double spaces collapse to one; ≥3 line breaks collapse to two.
    - User is warned and invalid input is highlighted.

---

### 2.3 Search Functionality

- **Snippets Search:**  
  - Real-time, case-insensitive filtering of snippets by name within the selected category.

---

### 2.4 View Snippet

- **View Modal:**  
  - Displays all parts of the selected snippet in order.

---

## 3. User Interface

### 3.1 Web UI

- Accessible from the main menu (`menu.html`).
- Responsive, modern design.
- Category list (left), snippets pane (right), modals for add/edit/view.
- Uses RESTful API endpoints for all operations.

### 3.2 Desktop UI

- Invoked from the desktop main menu (`desktop_ui.py`).
- Mirrors web UI functionality and layout.
- Uses the same API/backend as the web UI.

---

## 4. API & Backend

- All business logic is in service classes (e.g., `library_service.py`).
- API endpoints for CRUD operations on categories and snippets.
- Input validation and error handling at both API and backend layers.
- Uses dependency injection for database access to enable test mocks.

---

## 5. Testing

- **Test-Driven Development (TDD):**  
  - All features are test-first.
  - Pytest is used exclusively for all tests.

- **Test Coverage:**  
  - Unit tests for backend and service classes.
  - API tests for all endpoints.
  - Selenium tests for web UI (page load, CRUD, validation, search, view).
  - Desktop UI tests (functional, using UI test frameworks).

- **Test Isolation:**  
  - All tests use temporary databases and pytest fixtures for setup/teardown.
  - No test uses the production DB.
  - Tables are created using the app's own DB initialization logic, not raw SQL.

---

## 6. API Implementation and Structure
- All Category API endpoints are implemented in `category_api.py` using a Flask Blueprint (`category_api`).
- All Snippet API endpoints are implemented in `snippet_api.py` using a Flask Blueprint (`snippet_api`).
- Endpoints only handle request/response, validation, and error handling.
- All business logic (creation, update, deletion, DB access) is handled in `db/models/category.py`, `db/models/snippet.py`, and `db/models/practice_generator.py`.
- Endpoints:
  - `GET /api/categories`, `POST /api/categories`, `PUT /api/categories/<id>`, `DELETE /api/categories/<id>`
  - `GET /api/snippets?category_id=<id>`, `GET /api/snippets/<snippet_id>`, `POST /api/create-practice-snippet`

## 7. Testing Practices
- Unit tests for all model and service logic
- API tests for all endpoints in `tests/test_category_api.py` and `tests/test_snippet_api.py`
- UI tests for category and snippet management in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized

- **Test File Naming:**
  - Test files are placed in the `tests` folder and named after the functionality and layer, e.g.:
    - `test_library_backend.py`
    - `test_library_api.py`
    - `test_library_web.py`
    - `test_library_desktop.py`

---

## 6. Code Quality & Security

- All code follows PEP 8, is type-hinted, and uses Pydantic for data validation.
- All user input is validated and sanitized.
- Parameterized queries are used throughout.
- No sensitive data is hardcoded.
- All code is linted (flake8, black) before submission.

---

## 7. Error Handling

- User receives meaningful error messages for all validation and system errors.
- All exceptions are logged and surfaced appropriately in the UI.

---

## 8. Documentation

- All modules, classes, and functions have docstrings with type hints.
- README and inline documentation are updated with each significant change.

---

**This specification is up-to-date with the current implementation and testing standards.**
