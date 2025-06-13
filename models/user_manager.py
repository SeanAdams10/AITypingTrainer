"""
User Manager for CRUD operations.
Handles all DB access for users.
"""

from typing import List, Optional

from db.database_manager import DatabaseManager
from models.user import User


class UserValidationError(Exception):
    def __init__(self, message: str = "User validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class UserNotFound(Exception):
    def __init__(self, message: str = "User not found") -> None:
        self.message = message
        super().__init__(self.message)


class UserManager:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager: DatabaseManager = db_manager

    def _validate_email_uniqueness(self, email_address: str, user_id: Optional[str] = None) -> None:
        query = "SELECT 1 FROM users WHERE email_address = ?"
        params = [email_address]
        if user_id is not None:
            query += " AND user_id != ?"
            params.append(user_id)
        if self.db_manager.execute(query, tuple(params)).fetchone():
            raise UserValidationError(f"Email address '{email_address}' must be unique.")

    def get_user_by_id(self, user_id: str) -> User:
        row = self.db_manager.execute(
            "SELECT user_id, first_name, surname, email_address FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise UserNotFound(f"User with ID {user_id} not found.")
        return User(user_id=row[0], first_name=row[1], surname=row[2], email_address=row[3])

    def get_user_by_email(self, email_address: str) -> User:
        row = self.db_manager.execute(
            "SELECT user_id, first_name, surname, email_address FROM users WHERE email_address = ?",
            (email_address,),
        ).fetchone()
        if not row:
            raise UserNotFound(f"User with email '{email_address}' not found.")
        return User(user_id=row[0], first_name=row[1], surname=row[2], email_address=row[3])

    def list_all_users(self) -> List[User]:
        rows = self.db_manager.execute(
            "SELECT user_id, first_name, surname, email_address FROM users ORDER BY surname, first_name"
        ).fetchall()
        return [
            User(user_id=row[0], first_name=row[1], surname=row[2], email_address=row[3])
            for row in rows
        ]

    def save_user(self, user: User) -> bool:
        self._validate_email_uniqueness(user.email_address, user.user_id)
        if self.__user_exists(user.user_id):
            return self.__update_user(user)
        else:
            return self.__insert_user(user)

    def __user_exists(self, user_id: str) -> bool:
        row = self.db_manager.execute(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row is not None

    def __insert_user(self, user: User) -> bool:
        self.db_manager.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user.user_id, user.first_name, user.surname, user.email_address),
        )
        return True

    def __update_user(self, user: User) -> bool:
        self.db_manager.execute(
            "UPDATE users SET first_name = ?, surname = ?, email_address = ? WHERE user_id = ?",
            (user.first_name, user.surname, user.email_address, user.user_id),
        )
        return True

    def delete_user_by_id(self, user_id: str) -> bool:
        if not self.db_manager.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone():
            return False
        self.db_manager.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,),
        )
        return True

    def delete_user(self, user_id: str) -> bool:
        return self.delete_user_by_id(user_id)

    def delete_all_users(self) -> bool:
        count = self.db_manager.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.db_manager.execute("DELETE FROM users")
        return count > 0
