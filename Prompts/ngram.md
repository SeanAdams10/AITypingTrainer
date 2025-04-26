# N-Gram Analysis Specification

## 1. Overview

The ngram_analyzer provides detailed analysis of typing session keystrokes to identify speed bottlenecks and error-prone character sequences (n-grams, n=2–10). It writes results to unified `session_ngram_speed` and `session_ngram_error` tables. Analysis is triggered both automatically at the end of every typing session and on demand (via a UI button on the main menu). All logic is testable at class, API, UI, and desktop levels, using pytest and appropriate test frameworks.

---

## 2. Functional Requirements

### 2.1 N-Gram Analysis Scope
- **N-Gram Sizes:** Analyze n-grams for n = 2 through 10.
- **Data Source:** Operates on keystroke data from completed typing sessions.
- **Trigger Points:**
  - Automatically at the end of every typing session (e.g., in Typing Drill logic).
  - On demand via a temporary button in the main menu UI.
- **Tables Updated:**
  - `session_ngram_speed` (for correct n-grams and timing)
  - `session_ngram_error` (for n-grams ending in an error)
- **Filtering:**
  - Exclude any n-gram containing whitespace in any position.
  - Only include n-grams with valid timing data (speed) and/or errors (error table).

### 2.2 N-Gram Speed Analysis
- For each n-gram (n=2–10) in a session:
  - If all keystrokes are correct and timing is valid (time_since_previous > 0 and < 5000 ms), record in `session_ngram_speed`.
  - Store: session_id, ngram_size, ngram_id, ngram_time, ngram_text.

### 2.3 N-Gram Error Analysis
- For each n-gram (n=2–10) in a session:
  - If the last character is incorrect, record in `session_ngram_error`.
  - Store: session_id, ngram_size, ngram_id, ngram_time, ngram_text.

### 2.4 Practice Snippet Generation
- Generate practice snippets based on slowest or most error-prone n-grams.
- Practice snippets are stored in the `Practice Snippets` category.
- Snippet text highlights n-grams and includes example words containing them (if available) from the words table

### 2.5 API and UI Integration
- API endpoint to trigger n-gram analysis for a session or on demand.
- UI button (temporary, main menu) triggers on-demand analysis.
- Automatic invocation at session end.

---

## 3. Validation & Security
- N-grams must not contain whitespace.
- All database input is parameterized to prevent SQL injection.
- All user-facing actions provide clear feedback on success or failure.

---

## 4. API Implementation and Structure
- All N-Gram analysis API endpoints are implemented in `ngram_api.py` using a Flask Blueprint (`ngram_api`).
- Endpoints only handle request/response, validation, and error handling.
- All business logic for analysis, DB access, and snippet generation is handled in `db/models/ngram_analyzer.py` and related model files.
- Endpoints:
  - `GET /api/ngrams?session_id=<id>`: List n-gram analysis results for a session
  - `POST /api/ngram/analyze`: Trigger n-gram analysis for a session or on demand

## 5. Testing
- Unit tests for n-gram analyzer and snippet generation logic
- API tests for all endpoints in `tests/test_ngram_api.py`
- UI tests for n-gram analysis and practice snippet generation in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized

## 6. Test Cases

### 4.1 Class-Level Tests
- **Test n-gram extraction:**
  - Given keystrokes, verify correct n-gram extraction for n=2–10.
  - Ensure whitespace-containing n-grams are excluded.
- **Test speed/error table writing:**
  - Verify correct entries for both speed and error tables under various keystroke scenarios.
- **Test snippet generation:**
  - Verify generated practice snippets contain expected n-grams and words.
- **Test table creation:**
  - Ensure analyzer creates required tables if missing.

### 4.2 API-Level Tests
- **Trigger analysis endpoint:**
  - POST valid keystrokes/session_id, assert correct DB updates.
  - POST with invalid/insufficient data, assert graceful failure.
- **Snippet generation endpoint:**
  - Request new snippet for slow/error n-grams, verify DB and response.

### 4.3 Web UI-Level Tests
- **Main menu button:**
  - Clicking triggers analysis and shows feedback.
- **Session end integration:**
  - Completing a typing session triggers analysis automatically.
- **Practice snippet display:**
  - Generated snippets appear in the correct category and are viewable.

### 4.4 Desktop UI-Level Tests
- **Button triggers analysis:**
  - Temporary main menu button triggers analysis and displays result.
- **Session end triggers analysis:**
  - Typing drill completion triggers analysis.
- **Practice snippet integration:**
  - Generated snippets are accessible in the desktop UI.

---

## 5. Test Automation & Isolation
- All tests use pytest and pytest-mock/selenium where appropriate.
- All tests use temporary databases, initialized via the database manager’s `initialize_database` method—never the production DB.
- Temporary assets (files, folders) are created using pytest fixtures and cleaned up after each test.
- All tests are independent and order-agnostic.
- Tests are named and organized as:
  - `test_ngram_backend.py`
  - `test_ngram_api.py`
  - `test_ngram_web.py`
  - `test_ngram_desktop.py`

---

## 6. Error Handling & Feedback
- All errors are logged with context.
- User is notified of analysis or snippet generation failures via the UI.

---

## 7. Documentation
- This document (`Prompts/ngram.md`) is the canonical specification for all n-gram analysis and testing requirements.
- All code and tests should reference this document for expected behaviors, validation, and test coverage.
