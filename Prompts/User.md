# User Object Specification

## 1. Overview
The `User` model represents a registered user of the AI Typing Trainer application. It is used for authentication, personalization, and tracking user-specific data.

## 2. Data Model
- `user_id` (UUID, primary key): Unique identifier for the user
- `first_name` (str): User's first name (ASCII, 1-64 chars)
- `surname` (str): User's surname (ASCII, 1-64 chars)
- `email_address` (str): User's email address (ASCII, 5-128 chars, must contain '@' and '.')

## 3. Validation Rules
- All fields are required
- Names and email must be ASCII only
- Email must be unique in the database
- Email must contain '@' and '.'
- Names must be 1-64 characters
- Email must be 5-128 characters

## 4. Database Table
The `users` table is created by `DatabaseManager`:

| Column         | Type   | Constraints         |
|---------------|--------|--------------------|
| user_id       | TEXT   | PRIMARY KEY, UUID  |
| first_name    | TEXT   | NOT NULL           |
| surname       | TEXT   | NOT NULL           |
| email_address | TEXT   | NOT NULL, UNIQUE   |

## 5. UserManager
The `UserManager` class provides CRUD operations for users, including:
- Create, update, delete user
- Get user by ID or email
- List all users
- Enforces email uniqueness

## 6. Example Usage
```python
from db.database_manager import DatabaseManager
from models.user import User
from models.user_manager import UserManager

db = DatabaseManager(":memory:")
db.init_tables()
user_manager = UserManager(db)

user = User(first_name="Alice", surname="Smith", email_address="alice@example.com")
user_manager.save_user(user)
```

## 7. Testing
- Use an in-memory database for tests
- Test all CRUD operations and validation rules
- Ensure email uniqueness is enforced
