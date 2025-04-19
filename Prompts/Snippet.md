# Snippet Object Specification

## 1. Overview
A Snippet is a segment of text used for typing drills. Each snippet belongs to a Category and may be divided into parts for granular practice and analytics.

## 2. Data Model
- **snippet_id**: Integer (Primary Key)
- **category_id**: Integer (Foreign Key to Category)
- **snippet_name**: String (Unique within category, required, ASCII-only, max 128 chars)
- **content**: String (required)

## 3. Functional Requirements
- Snippets can be created, renamed, edited, and deleted
- Snippets are linked to categories
- Snippet names must be unique within their category

## 4. API Endpoints
- `GET /api/snippets?category_id=<id>`: List all snippets for a category
- `POST /api/snippets`: Create a new snippet
- `PUT /api/snippets/<id>`: Edit snippet name/content
- `DELETE /api/snippets/<id>`: Delete a snippet

## 5. UI Requirements
- Snippet management available in both desktop (PyQt5) and web UIs
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
- All Snippet API endpoints are implemented in `snippet_api.py` using a Flask Blueprint (`snippet_api`).
- Each endpoint only handles request/response, validation, and error handling.
- All business logic (creation, update, deletion, DB access) is handled in `db/models/snippet.py` and `db/models/practice_generator.py`.
- Endpoints:
  - `GET /api/snippets?category_id=<id>`: List all snippets for a category
  - `GET /api/snippets/<snippet_id>`: Get details for a specific snippet
  - `POST /api/create-practice-snippet`: Auto-generate a practice snippet

## 9. Testing
- Unit tests for snippet model and generator logic
- API tests for all endpoints in `tests/test_snippet_api.py`
- UI tests for snippet management in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized
