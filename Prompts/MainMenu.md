# Main Menu Specification

## 1. Overview

The Main Menu provides a unified entry point to all major features of the AI Typing Trainer, both on the web and desktop UIs. It is designed for clarity, consistency, and accessibility, allowing users to quickly navigate to all core application areas. All menu actions are testable and must be implemented equivalently in both UI modes.

- The main menu uses PyQt5 for a modern, cross-platform UI.
- The main menu window is 100 pixels taller than previous versions and is centered on the screen at startup.
- Buttons change to a light grey background and black text when hovered over.
- The entry point for the desktop UI is now main_menu.py.
- All references to desktop_ui.py should be updated to main_menu.py.

---

## 2. Functional Requirements

### 2.1 Menu Layout & Navigation

- **Header:**
  - Displays the application title: "AI Typing Trainer".
  - Centered at the top of the menu.

- **Primary Actions:**
  - **Manage Your Library of Text**
    - Navigates to the Snippets Library management screen.
    - Allows category and snippet management through API integration (see Library.md).
    - Includes fallback to stub data if API is unavailable.
  - **Do a Typing Drill**
    - Opens the Drill Configuration screen for selecting a category/snippet and starting a typing drill.
  - **Practice Weak Points**
    - Opens the Weak Points practice workflow (future/optional; must show a placeholder if not implemented).
  - **View Progress Over Time**
    - Opens the Progress/Statistics dashboard (future/optional; must show a placeholder if not implemented).
  - **Data Management**
    - Opens the Data Management screen for advanced data operations (future/optional; must show a placeholder if not implemented).
  - **View DB Content**
    - Opens the Database Content Viewer for direct inspection of database tables (desktop: in-app window; web: `/db-viewer`).

- **Session & Application Controls:**
  - **Reset Session Details**
    - Button (web: form POST, desktop: button) to reset all session data.
    - Prompts for user confirmation before proceeding.
    - All session statistics and history are cleared.
  - **Quit Application**
    - Cleanly exits the application (desktop) or logs out/quits (web).

- **Layout & UX:**
  - All menu items are presented as clearly labeled, large buttons (Bootstrap `btn-lg` or equivalent desktop style).
  - Buttons are grouped logically with separators between main actions and session/app controls.
  - The menu is visually centered and responsive (web) or resizable (desktop).
  - All buttons are accessible via keyboard navigation and screen readers.
  - Preference for PyQt5 over tkinter for desktop UI just for testability.
-- screen should load up in the middle of the screen - at least 800x600 pixels in size
- Fonts should be consistent with the web UI - modern and clean look (e.g. sans-serif)


---

## 3. Implementation Notes

- **Consistency:**
  - Menu structure, order, and button labels must be identical between web and desktop.
  - All actions must be implemented as navigable routes (web) or callable methods (desktop).
  - Placeholder features (not yet implemented) must show a clear info dialog stating "Coming Soon" or similar.

- **Confirmation Dialogs:**
  - Reset Session Details must always prompt for confirmation before proceeding.
  - Quit Application must perform a clean shutdown.

- **Testability:**
  - All menu actions must be testable via pytest (main_menu.py + PyQt5 mocks; web: pytest + Selenium or equivalent).
  - Automated tests must cover:
    - Button presence and correct labeling.
    - Correct navigation or dialog on click.
    - Confirmation dialogs for destructive actions.
    - Accessibility (tab order, screen reader labels).

---

## 4. Validation & Error Handling

- All menu actions must be robust to backend/API failures, showing error dialogs if a feature cannot be loaded.
- Invalid or failed destructive actions (reset, quit) must show clear error messages and not leave the app in an inconsistent state.


---

## 6. Example Layout (Web)

```
+------------------------------------------+
|         AI Typing Trainer                |
|------------------------------------------|
| [Manage Your Library of Text]            |
| [Do a Typing Drill]                      |
| [Practice Weak Points]                   |
| [View Progress Over Time]                |
| [Data Management]                        |
| [View DB Content]                        |
|------------------------------------------|
| [Reset Session Details]                  |
| [Quit Application]                       |
+------------------------------------------+
```

---

## 7. References
- See [Library.md] for details on Library management functionality.
- See [DrillConfig.md] for drill configuration requirements.
- See [main_menu.py] and [menu.html] for current implementation.


## 6. Code Quality & Security

- All code follows PEP 8, is type-hinted, and uses Pydantic for data validation.
- All user input is validated and sanitized.
- Parameterized queries are used throughout.
- No sensitive data is hardcoded.
- All code is linted (`flake8`, `black`) before submission.

---

## 7. API Implementation and Structure
- All main menu actions that require backend interaction are implemented via modular API files using Flask Blueprints:
  - `category_api.py` and `snippet_api.py` for Library management
  - `session_api.py`, `keystroke_api.py`, `error_api.py`, and `ngram_api.py` for Typing Drill and session workflows
  - `dbviewer_api.py` for Database Content Viewer
- Each API file only handles request/response, validation, and error handling.
- All business logic and DB access are handled in models and service classes, not in the API files.
- Menu navigation triggers the appropriate API endpoints for each workflow, ensuring modularity and separation of concerns.

## 8. Testing Practices
- Unit tests for all backend models and services
- API tests for all modular endpoints
- UI tests for menu navigation and all downstream workflows in both web and desktop UIs
- All tests use pytest, pytest-mock, and proper fixtures for DB isolation
- No test uses the production DB; all tests are independent and parameterized
- all code is checked with mypy and pylint before submission.

---

## 7. Error Handling

- User receives meaningful error messages for all validation and system errors.
- All exceptions are logged and surfaced appropriately in the UI.
- Check that the session was written to the database in the database in all 5 tables listed above (practice_sessions, session_keystrokes, practice_session_errors, session_ngram_speed, session_ngram_errors) - if not, please show the user an error message.

---

## 8. Documentation

- All modules, classes, and functions have docstrings with type hints.
- README and inline documentation are updated with each significant change.

--

## 9. Security

- All user input is validated and sanitized.
- All database access is protected with parameterized queries.
- No sensitive data is hardcoded. 