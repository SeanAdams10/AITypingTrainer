# Snippet Object Specification

## 1. Overview
A Snippet is a segment of text used for typing drills. Each snippet belongs to a Category and may be divided into parts for granular practice and analytics.

## 2. Data Model
- **snippet_id**: Integer (Primary Key, Optional for new snippets)
- **category_id**: Integer (Foreign Key to Category, Required)
- **snippet_name**: String (Unique within category, required, ASCII-only, max 128 chars, min 1 char)
- **content**: String (required)

Implemented as a Pydantic model with Field validation for Pydantic v2 compatibility.

## 3. Functional Requirements
- Snippets can be created, renamed, edited, and deleted
- Snippets are linked to categories
- Snippet names must be unique within their category

## 4. API Endpoints
API is implemented using GraphQL with the following operations:

**Queries**:
- `snippets(category_id: Int!)`: List all snippets for a category
- `snippet(snippet_id: Int!)`: Get a specific snippet by ID

**Mutations**:
- `createSnippet(category_id: Int!, snippet_name: String!, content: String!)`: Create a new snippet
- `editSnippet(snippet_id: Int!, snippet_name: String, content: String)`: Edit a snippet
- `deleteSnippet(snippet_id: Int!)`: Delete a snippet

All GraphQL operations are accessible via a single endpoint: `/api/graphql`

## 5. UI Requirements
- Snippet management available in both desktop (PyQt5) and web UIs
- Add/Edit/Delete dialogs must validate input and show clear errors
- Desktop UI implemented in `desktop_ui/snippet_scaffold.py` as a QtMainWindow
- List box displays all snippets with tooltips showing content previews
- Double-click to load a snippet for editing
- Status bar provides operation feedback
- Input validation prevents empty submissions

## 6. Testing
- Backend, API, and UI tests must cover all CRUD operations, validation, and error handling
- All tests must run on a clean DB and be independent

## 7. Security/Validation
- No SQL injection (parameterized queries)
- No sensitive data hardcoded
- All user input is validated and sanitized

---

## 8. API Implementation and Structure
- GraphQL API is implemented in `api/snippet_graphql.py` using Graphene and Flask
- The API is exposed via a Flask Blueprint (`snippet_graphql`)
- Schema defines types, queries, and mutations with proper validation
- All business logic (creation, update, deletion, DB access) is handled in `models/snippet.py`
- A single endpoint `/api/graphql` handles all operations
- Error handling and status codes follow GraphQL conventions
- Manager instance is retrieved from Flask `g` or app config for flexibility
- Type hints and docstrings document all components

## 9. Testing
- Unit tests for snippet model in `tests/core/test_snippet_model.py`
- GraphQL API tests in `tests/api/test_snippet_graphql.py` and `tests/api/test_snippet_api.py`
- Desktop UI tests in `tests/desktop_ui/test_snippet_ui.py`
- All tests use pytest with centralized fixtures in `tests/conftest.py`
- Fixtures provide temporary database and snippet manager instances
- Type safety ensured with proper type annotations throughout
- Tests validate both happy path and error handling scenarios
- No test uses the production DB; all tests are independent and parameterized
