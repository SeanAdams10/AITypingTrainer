# Keystroke Object Specification

## 1. Overview
A Keystroke records each key press during a typing session, including timing, correctness, and expected character. Used for detailed analytics and error reporting.

## 2. Data Model
- **keystroke_id**: Integer (Primary Key)
- **session_id**: String/UUID (Foreign Key to PracticeSession)
- **keystroke_time**: DateTime
- **keystroke_char**: String
- **expected_char**: String
- **is_correct**: Boolean
- **time_since_previous**: Integer (ms)

## 3. Functional Requirements
- Keystrokes are recorded in real time during drills
- Linked to sessions for analytics and error reporting

## 4. API Endpoints
- `POST /api/keystrokes`: Record a keystroke
- `GET /api/keystrokes?session_id=<id>`: List keystrokes for a session

## 5. UI Requirements
- Keystrokes are managed automatically by TypingDrill UIs
- Used for real-time feedback and post-drill analytics

## 6. Testing
- Backend, API, and UI tests must cover all keystroke recording and retrieval
- All tests must run on a clean DB and be independent

## 7. Security/Validation
- No SQL injection (parameterized queries)
- No sensitive data hardcoded
- All user input is validated and sanitized

---

## 8. API Implementation and Structure
- All Keystroke API endpoints are implemented in `keystroke_api.py` using a Flask Blueprint (`keystroke_api`).
- Endpoints only handle request/response, validation, and error handling.
- All business logic (creation, retrieval, DB access) is handled in `db/models/keystroke.py`.
- Endpoints:
  - `POST /api/keystrokes`: Record a keystroke
  - `GET /api/keystrokes?session_id=<id>`: List keystrokes for a session

## 9. Testing
- Unit tests for keystroke model logic
- API tests for all endpoints in `tests/test_keystroke_api.py`
- UI tests for keystroke tracking and feedback in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized
