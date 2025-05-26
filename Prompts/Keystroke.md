# Keystroke Object Specification

> **NOTE:** `session_id` is always an **integer** throughout the application and database. All APIs, models, and DB tables use integer session IDs. Any previous references to string/UUID session IDs are obsolete.

## 1. Overview
A Keystroke records each key press during a typing session, including timing, correctness, and expected character. Used for detailed analytics and error reporting.

## 2. Data Model
- **keystroke_id**: Integer (Primary Key)
- **session_id**: UUID String (Foreign Key to practice_sessions)
- **keystroke_time**: DateTime
- **keystroke_char**: String
- **expected_char**: String
- **is_correct**: Boolean

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

## 9. Database Structure
### 9.1 session_keystrokes Table
- **keystroke_id**: Integer (Primary Key)
- **session_id**: UUID String (Foreign Key to practice_sessions)
- **keystroke_time**: DateTime
- **keystroke_char**: String
- **expected_char**: String
- **is_correct**: Boolean

### 9.2 Error Tracking
- Errors are tracked directly in the session_keystrokes table using the is_correct field:
    - When is_correct = 1: The keystroke was typed correctly
    - When is_correct = 0: The keystroke represents an error

---

<!--
Code Review Summary:
- `Keystroke` (keystroke.py):
  - Classic Python class (not Pydantic) for keystroke events, with save, from_dict, to_dict, and batch methods.
  - Handles DB persistence, conversion, and error handling robustly.
  - Supports both single and batch operations, and error filtering.
- `KeystrokeManager` (keystroke_manager.py):
  - Handles all DB CRUD for keystrokes, including batch save/delete and per-session queries.
  - Uses parameterized queries, robust error handling, and supports deletion by session or all.
- `PracticeSessionKeystrokeManager` (practice_session_extensions.py):
  - Provides a higher-level interface for recording and retrieving keystrokes in the context of practice sessions.
  - Uses TypedDicts for type safety and clear structure.
  - Integrates with PracticeSessionManager and supports analytics.
-->

```mermaid
---
title: Keystroke Model and Manager UML
---
classDiagram
    class Keystroke {
        +int? keystroke_id
        +str session_id
        +datetime keystroke_time
        +str keystroke_char
        +str expected_char
        +bool is_correct
        +int? time_since_previous
        +save(db_manager) bool
        +to_dict() dict
        +from_dict(data: dict) Keystroke
        +save_many(session_id, keystrokes) bool
        +get_for_session(session_id) List~Keystroke~
        +get_errors_for_session(session_id) List~Keystroke~
        +delete_all_keystrokes(db) bool
    }
    class KeystrokeManager {
        -DatabaseManager db_manager
        +__init__(db_manager)
        +add_keystroke(keystroke) bool
        +save_keystrokes(session_id, keystrokes) bool
        +delete_keystrokes_by_session(session_id) bool
        +delete_all() bool
        +count_keystrokes_per_session(session_id) int
    }
    class PracticeSessionKeystrokeManager {
        -DatabaseManager db_manager
        +__init__(db_manager)
        +record_keystroke(...)
        +get_keystrokes_for_session(session_id) list
    }
    KeystrokeManager --> Keystroke : manages 1..*
    KeystrokeManager --> DatabaseManager : uses
    PracticeSessionKeystrokeManager --> DatabaseManager : uses
    PracticeSessionKeystrokeManager --> KeystrokeManager : uses
```
