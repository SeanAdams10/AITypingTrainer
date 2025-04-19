# Category Object Specification

## 1. Overview
A Category represents a logical grouping of text snippets for typing practice. Categories are used to organize content, enable targeted drills, and support reporting/analytics.

## 2. Data Model
- **category_id**: Integer (Primary Key)
- **category_name**: String (Unique, required, ASCII-only, max 64 chars)

## 3. Functional Requirements
- Categories can be created, renamed, and deleted.
- Deleting a category deletes all associated snippets and snippet parts.
- Category names must be unique and validated for ASCII and length.
- All validation errors (e.g., non-ASCII, too long, blank, duplicate) are surfaced to the API as HTTP 400 with a clear, specific error message.
- Attempting to create or rename a category to a non-ASCII, blank, too-long, or duplicate name will fail with a descriptive error.
- All endpoints use parameterized queries and centralized validation to prevent SQL injection and other attacks.

## 4. API Endpoints
- `GET /api/categories`: List all categories
- `POST /api/categories`: Create a new category
- `PUT /api/categories/<id>`: Rename a category
- `DELETE /api/categories/<id>`: Delete a category and all related snippets

## 5. UI Requirements
- Category management available in both desktop (PyQt5) and web UIs
- Add/Edit/Delete dialogs must validate input and show clear errors

## 6. Testing
- Backend, API, and UI tests must cover all CRUD operations, validation, and error handling
- All tests must run on a clean DB and be independent

## 7. Security/Validation
- No SQL injection (parameterized queries)
- No sensitive data hardcoded
- All user input is validated and sanitized

---

## 8. API Implementation and Structure
- All Category API endpoints are implemented in `category_api.py` using a Flask Blueprint (`category_api`).
- Endpoints only handle request/response, validation, and error handling.
- All business logic (creation, update, deletion, DB access) is handled in `db/models/category.py`.
- Endpoints:
  - `GET /api/categories`: List all categories
  - `POST /api/categories`: Create a new category
  - `PUT /api/categories/<id>`: Rename a category
  - `DELETE /api/categories/<id>`: Delete a category and all related snippets

## 9. Testing
- Unit tests for category model logic
- API tests for all endpoints in `tests/test_category_api.py`
- UI tests for category management in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized
- All tests (class, API) are independent, run on a clean DB, and comprehensively cover happy, edge, and destructive paths.
