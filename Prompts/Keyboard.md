# Keyboard Object Specification

## 1. Overview
The `Keyboard` model represents a physical or virtual keyboard associated with a user in the AI Typing Trainer application. It is used for tracking user-specific keyboard layouts, preferences, and statistics.

## 2. Data Model
- `keyboard_id` (UUID, primary key): Unique identifier for the keyboard
- `user_id` (UUID, foreign key): The user who owns this keyboard
- `keyboard_name` (str): Name of the keyboard (ASCII, 1-64 chars, unique per user)
- `target_ms_per_keystroke` (int): Target milliseconds per keystroke for typing speed goal (50-5000, default 100)

## 3. Validation Rules
- All fields are required
- `keyboard_name` must be ASCII, 1-64 characters, and unique per user
- `user_id` must be a valid UUID and reference an existing user
- `target_ms_per_keystroke` must be an integer between 50 and 5000 (inclusive)

## 4. Database Table
The `keyboards` table is created by `DatabaseManager`:

| Column                 | Type    | Constraints                        |
|---------------------- |--------|------------------------------------|
| keyboard_id            | TEXT    | PRIMARY KEY, UUID                  |
| user_id                | TEXT    | NOT NULL, FK to users(user_id)     |
| keyboard_name          | TEXT    | NOT NULL                           |
| target_ms_per_keystroke | INTEGER | NOT NULL, DEFAULT 100              |

## 5. KeyboardManager
The `KeyboardManager` class provides CRUD operations for keyboards, including:
- Create, update, delete keyboard
- Get keyboard by ID
- List all keyboards for a user
- Enforces keyboard name uniqueness per user

## 6. Example Usage
```python
from db.database_manager import DatabaseManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager

db = DatabaseManager(":memory:")
db.init_tables()
keyboard_manager = KeyboardManager(db)

keyboard = Keyboard(user_id="...", keyboard_name="My Keyboard", target_ms_per_keystroke=120)
keyboard_manager.save_keyboard(keyboard)
```

## 7. Testing
- Use an in-memory database for tests
- Test all CRUD operations and validation rules
- Ensure keyboard name uniqueness per user is enforced
