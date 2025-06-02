<!-- filepath: d:\OneDrive\Documents\SeanDev\AITypingTrainer\Prompts\Session.md -->
# Session Object Specification

## 1. Overview
A Session records a user's typing practice, including timing, correctness, and analytics. All business logic and validation are in `Session` (`models/session.py`). All DB and aggregate logic are in `SessionManager` (`models/session_manager.py`).

## 2. Data Model

### Database Schema

#### practice_sessions Table
- **session_id**: TEXT PRIMARY KEY (UUID string)
- **snippet_id**: TEXT NOT NULL (Foreign Key to snippets.snippet_id)
- **snippet_index_start**: INTEGER NOT NULL
- **snippet_index_end**: INTEGER NOT NULL
- **content**: TEXT NOT NULL
- **start_time**: DATETIME NOT NULL
- **end_time**: DATETIME NOT NULL
- **actual_chars**: INTEGER NOT NULL
- **errors**: INTEGER NOT NULL

## 3. Functional Requirements
- Sessions are created, updated, and retrieved via SessionManager.
- All business logic, validation, and computed properties are in the Session model.
- All DB operations are parameterized and handled by SessionManager.
- Sessions are validated for UUID, time, indices, and error logic.
- All computed metrics (WPM, CPM, efficiency, etc.) are properties, not stored fields.
- All validation is performed using Pydantic models and validators.
- All code uses type hints and docstrings for clarity and safety.

## 4. Computed Properties (Session)
- **expected_chars**: snippet_index_end - snippet_index_start
- **total_time**: (end_time - start_time).total_seconds()
- **efficiency**: actual_chars / expected_chars
- **correctness**: (actual_chars - errors) / actual_chars
- **accuracy**: correctness * efficiency
- **session_wpm**: (actual_chars / 5) / (total_time / 60)
- **session_cpm**: actual_chars / (total_time / 60)

## 5. API Endpoints
All session management is handled via a unified GraphQL endpoint at `/api/graphql`.

**GraphQL Queries:**
- `sessions(snippet_id: Int!)`: List all sessions for a snippet
- `session(session_id: String!)`: Get a specific session by ID

**GraphQL Mutations:**
- `createSession(data: SessionInput!)`: Create a new session
- `updateSession(session_id: String!, data: SessionInput!)`: Update a session
- `deleteSession(session_id: String!)`: Delete a session

All validation errors are surfaced as GraphQL error responses with clear, specific messages.

## 6. UI Requirements
- Session analytics and management available in both desktop (PyQt5) and web UIs
- Session details, metrics, and summaries are shown in the UI
- Add/Edit/Delete dialogs must validate input and show clear errors

## 7. Testing
- Backend, API, and UI tests must cover all CRUD operations, validation, and error handling
- All tests must run on a clean DB and be independent
- All computed properties and business rules are tested

## 8. Security/Validation
- No SQL injection (parameterized queries)
- No sensitive data hardcoded
- All user input is validated and sanitized

## 9. Code Quality, Testing, and Security Standards
- All code is formatted with Black and follows PEP 8 style guidelines.
- Linting is enforced with flake8; all lint errors are fixed before merging.
- All code uses type hints and Pydantic for validation.
- All tests use pytest and pytest fixtures for setup/teardown, with DB isolation.
- No test uses the production DB; all tests are independent and parameterized.
- All Session CRUD operations, validation, and error handling are covered by backend, API, and UI tests.
- No sensitive data is hardcoded. All user input is validated and sanitized.
- All database operations use parameterized queries for security.

---

## 10. API Implementation and Structure
- All Session API operations are implemented in `api/session_api.py` and `api/session_graphql.py` using Graphene and Flask.
- The GraphQL schema defines types, queries, and mutations with proper validation.
- All business logic (creation, update, deletion, DB access) is handled in `models/session.py` and `models/session_manager.py`.
- The unified endpoint `/api/graphql` handles all operations.
- Error handling and status codes follow GraphQL conventions.
- Type hints and docstrings document all components.

---

## 11. UML Class Diagram (Refreshed May 2025)

```mermaid
---
title: Session Model and Manager UML
---
classDiagram
    class Session {
        +str session_id
        +int snippet_id
        +int snippet_index_start
        +int snippet_index_end
        +str content
        +datetime start_time
        +datetime end_time
        +int actual_chars
        +int errors
        +int expected_chars
        +float total_time
        +float efficiency
        +float correctness
        +float accuracy
        +float session_wpm
        +float session_cpm
        +from_dict(data: dict) Session
        +from_row(row: Mapping) Session
        +to_dict() dict
        +get_summary() str
    }
    class SessionManager {
        -DatabaseManager db_manager
        +__init__(db_manager)
        +create_session(data: dict) Session
        +get_session_by_id(session_id: str) Session
        +list_sessions_for_snippet(snippet_id: int) List~Session~
        +save_session(session: Session) str
        +delete_all() bool
    }
    SessionManager --> Session : manages 1..*
    SessionManager --> DatabaseManager : uses
```
