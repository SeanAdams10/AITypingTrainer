# Snippet Object Specification

## 1. Overview
A Snippet is a segment of text used for typing drills. Each snippet belongs to a Category and is divided into parts for granular practice and analytics. Each part is limited to 500 characters maximum.

## 2. Data Model

### Database Schema

#### categories Table
- **category_id**: INTEGER PRIMARY KEY AUTOINCREMENT
- **category_name**: TEXT NOT NULL UNIQUE

#### snippets Table
- **snippet_id**: INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
- **category_id**: INTEGER NOT NULL (Foreign Key to categories.category_id)
- **snippet_name**: TEXT NOT NULL (ASCII-only, max 128 chars, min 1 char)
- Constraint: UNIQUE (category_id, snippet_name) - Ensures snippet names are unique within their category

#### snippet_parts Table
- **snippet_id**: INTEGER NOT NULL (Foreign Key to snippets.snippet_id)
- **part_number**: INTEGER NOT NULL (Sequential numbering starting at 1)
- **content**: TEXT NOT NULL (Contains up to 500 characters of snippet content)
- Constraint: PRIMARY KEY (snippet_id, part_number) - Composite primary key

Implemented as a Pydantic model with Field validation for Pydantic v2 compatibility. The SnippetModel combines metadata from the snippets table with content from the snippet_parts table for seamless usage.

## 3. Functional Requirements
- Snippets can be created, renamed, edited, and deleted
- Snippets are linked to categories
- Snippet names must be unique within their category
- **The system can determine the next starting index for a snippet for a given user and keyboard, using the latest session's `snippet_index_end` from the `practice_sessions` table. If the user has completed the snippet, the index wraps to 0.**
- **The SnippetManager provides a `get_starting_index(snippet_id, user_id, keyboard_id)` method that returns the next index to start typing for a given snippet, user, and keyboard. This is used to resume or continue drills from where the user last left off. If no session exists, it returns 0. If the last index is at or beyond the end of the snippet, it wraps to 0.**

## 4. API Endpoints
All Snippet management is handled via a unified GraphQL endpoint at `/api/graphql`.

**GraphQL Queries:**
- `snippets(category_id: Int!)`: List all snippets for a category
- `snippet(snippet_id: Int!)`: Get a specific snippet by ID
- `getStartingIndex(snippet_id: Int!, user_id: String!, keyboard_id: String!): Int!` — Returns the next starting index for a snippet for a user/keyboard (calls SnippetManager.get_starting_index)

**GraphQL Mutations:**
- `createSnippet(category_id: Int!, snippet_name: String!, content: String!)`: Create a new snippet
- `editSnippet(snippet_id: Int!, snippet_name: String, content: String)`: Edit a snippet
- `deleteSnippet(snippet_id: Int!)`: Delete a snippet

All validation is performed using Pydantic models and validators. Errors are surfaced as GraphQL error responses with clear, specific messages.

---

# Typing Games Documentation

The AI Typing Trainer includes interactive typing games designed to make practice engaging and fun. These games are accessible through the main menu → Games, and also directly from the typing drill interface.

## Space Invaders Typing Game

### Overview
A classic arcade-style typing game inspired by Space Invaders, where players destroy words by typing them correctly.

### Game Mechanics
- **8 rows of words** arranged in Space Invaders formation, center-aligned
- **Horizontal movement pattern**: Words move right until hitting screen edge (+2 character buffer), then drop down and reverse direction
- **Player character**: Green triangle at bottom center of screen
- **Targeting system**: Typing a letter targets the first word starting with that letter
- **Word destruction**: Complete words correctly to make them explode
- **Collision detection**: Game ends if any word reaches the player

### Scoring System
- **1 point per letter** typed correctly
- **Bonus points** equal to word length when word is completed
- Real-time score display in top-right corner

### Visual Design
- Classic arcade aesthetic with colorful graphics
- Different colors for typed vs. remaining letters in targeted words
- Explosion animations when words are destroyed
- Progress indicators and game state feedback

### Word List
48 space-themed words including: energy, missile, power, beam, suit, armor, plasma, wave, ice, spazer, charge, morph, ball, bomb, spring, space, jump, high, screw, attack, speed, booster, gravity, varia, phazon, dark, light, echo, scan, visor, thermal, x-ray, combat, grapple, boost, spider, wall, double, shine, spark, shinespark, dash, run, walk, crouch, aim, lock, target, enemy.

### Technical Implementation
- Built with PySide6 and custom QPainter graphics
- 20 FPS animation using QTimer
- Real-time keyboard input handling
- Smart word targeting algorithm
- Proper game state management (running/won/lost)

---

## Metroid Typing Game

### Overview
A Metroid-inspired typing game where words float in from screen edges toward the center, requiring quick and accurate typing to survive.

### Game Mechanics
- **Central player position**: User represented at center of screen
- **Converging word movement**: Words spawn from random edges and move slowly toward center
- **Multi-word targeting**: Typing highlights matching letters in ALL words that start with the typed prefix
- **Precise completion**: Only complete, correctly typed words are destroyed
- **Speed progression**: Movement speed increases by 10% every 10 words completed
- **Collision ending**: Game ends when any word reaches the center (player)

### Scoring System
**Exponential per-letter scoring**:
- 1st letter: 1 point
- 2nd letter: 1.5 points  
- 3rd letter: 2.25 points (1.5²)
- 4th letter: 3.375 points (1.5³)
- And so on...

Example: The word "the" = 1 + 1.5 + 2.25 = 4.75 points

### Visual Design
- **Metroid aesthetic**: Clean line-drawing style
- **White background** with black-outlined word boxes
- **Orange highlighting** for letters being typed
- **Explosion animations** with radiating spark effects when words are destroyed
- **Real-time counters**: Speed multiplier (left) and Score (right)

### Game Progression
- **Base speed**: 1.0 (very slow initial movement)
- **Speed increases**: +10% every 10 words completed
- **Win condition**: Complete 50 words
- **Lose condition**: Any word reaches the center
- **Word spawning**: Continuous spawning from random screen edges
- **Maximum words**: Limited to 12 words on screen simultaneously

### Word List
80+ Metroid-themed words including: energy, missile, power, beam, suit, armor, plasma, wave, ice, spazer, charge, morph, ball, bomb, spring, space, jump, high, screw, attack, speed, booster, gravity, varia, phazon, dark, light, echo, scan, visor, thermal, x-ray, combat, grapple, boost, spider, wall, double, shine, spark, shinespark, dash, run, walk, crouch, aim, lock, target, enemy, pirate, metroid, chozo, ancient, ruins, temple, sanctuary, artifact, key, door, elevator, save, station, map, room, corridor, shaft, tunnel, chamber, core, reactor, engine, computer, terminal, data, log, research, science, experiment, specimen, sample, analysis.

### Technical Implementation
- Built with PySide6 and custom QPainter graphics
- 20 FPS animation using QTimer
- Advanced word movement algorithms with edge detection
- Real-time multi-word highlighting system
- Exponential scoring calculations
- Dynamic speed progression system

---

## Games Menu Integration

### Access Points
1. **Main Menu**: Click "Games" button to open Games Menu
2. **Typing Drill**: Click "🎮 Games" button during practice sessions

### Games Menu Features
- Modern UI design consistent with main application
- Game selection with descriptions
- Easy navigation back to main menu
- Future game placeholders for expansion

### Navigation Flow
```
Main Menu → Games Menu → Select Game → Play → Return to Menu
Typing Drill → Games Menu → Select Game → Play → Return to Drill
```

### Future Expansion
The games menu is designed to accommodate additional typing games:
- **Speed Racer**: High-speed typing challenges
- **Word Puzzle**: Solve puzzles by typing
- Additional game types as requested

---

## 5. UI Requirements
- Snippet management available in both desktop (PyQt5/PySide6) and web UIs
- Add/Edit/Delete dialogs must validate input and show clear errors
- Desktop UI implemented in `desktop_ui/snippet_scaffold.py` as a QtMainWindow
- List box displays all snippets with tooltips showing content previews
- Double-click to load a snippet for editing
- Status bar provides operation feedback
- Input validation prevents empty submissions
- **When starting a typing drill, the UI queries the next starting index for the selected snippet, user, and keyboard, and pre-fills the drill start index accordingly.**

## 6. Testing
- Backend, API, and UI tests must cover all CRUD operations, validation, and error handling
- All tests must run on a clean DB and be independent
- **Tests for get_startting_index cover scenarios with no sessions, with sessions, wrap-around, and multiple users/keyboards.**

## 7. Security/Validation
- No SQL injection (parameterized queries)
- No sensitive data hardcoded
- All user input is validated and sanitized

## 8. Code Quality, Testing, and Security Standards
- All code is formatted with Black and follows PEP 8 style guidelines.
- Linting is enforced with flake8; all lint errors are fixed before merging.
- All code uses type hints and Pydantic for validation.
- All tests use pytest and pytest fixtures for setup/teardown, with DB isolation.
- No test uses the production DB; all tests are independent and parameterized.
- All Snippet CRUD operations, validation, and error handling are covered by backend, API, and UI tests.
- No sensitive data is hardcoded. All user input is validated and sanitized.
- All database operations use parameterized queries for security.

---

## 9. API Implementation and Structure
- GraphQL API is implemented in `api/snippet_graphql.py` using Graphene and Flask
- The API is exposed via a Flask Blueprint (`snippet_graphql`)
- Schema defines types, queries, and mutations with proper validation
- All business logic (creation, update, deletion, DB access) is handled in `models/snippet.py`
- A single endpoint `/api/graphql` handles all operations
- Error handling and status codes follow GraphQL conventions
- Manager instance is retrieved from Flask `g` or app config for flexibility
- Type hints and docstrings document all components
- **The `SnippetManager` provides a `get_starting_index(snippet_id, user_id, keyboard_id)` method to determine the next starting index for a snippet for a user and keyboard, based on the latest session.**

## 10. Testing
- Unit tests for snippet model in `tests/core/test_snippet_model.py`
- GraphQL API tests in `tests/api/test_snippet_graphql.py` and `tests/api/test_snippet_api.py`
- Desktop UI tests in `tests/desktop_ui/test_snippet_ui.py`
- All tests use pytest with centralized fixtures in `tests/conftest.py`
- Fixtures provide temporary database and snippet manager instances
- Type safety ensured with proper type annotations throughout
- Tests validate both happy path and error handling scenarios
- No test uses the production DB; all tests are independent and parameterized

<!--
Code Review Summary:
- `Snippet` (snippet.py):
  - Pydantic model with strong validation for all fields (ASCII, length, SQLi, integer checks).
  - Uses custom validators for name/content, and provides from_dict/to_dict helpers.
  - Enforces uniqueness and security at the model and manager level.
- `SnippetManager` (snippet_manager.py):
  - Handles all CRUD for snippets, including splitting content into parts (max 500 chars).
  - Validates with Pydantic, checks for uniqueness, and handles DB errors robustly.
  - Methods for create, get by id/name, list by category, search, update, delete, and summary.
  - Uses parameterized queries and logs errors.
  - Follows good separation of concerns and error handling.
-->

```mermaid
---
title: Snippet Model and Manager UML
---
classDiagram
    class Snippet {
        +str snippet_id
        +str category_id
        +str snippet_name
        +str content
        +from_dict(data: dict) Snippet
        +to_dict() dict
    }
    class SnippetManager {
        -DatabaseManager db
        +__init__(db_manager: DatabaseManager)
        +save_snippet(snippet: Snippet) bool
        +get_snippet_by_id(snippet_id) Snippet
        +get_snippet_by_name(snippet_name, category_id) Snippet
        +list_snippets_by_category(category_id) List~Snippet~
        +search_snippets(query, category_id) List~Snippet~
        +delete_snippet(snippet_id) bool
        +snippet_exists(category_id, snippet_name, exclude_snippet_id) bool
        +get_all_snippets_summary() List~dict~
        +get_starting_index(snippet_id, user_id, keyboard_id) int
    }
    SnippetManager --> Snippet : manages 1..*
    SnippetManager --> DatabaseManager : uses
```
