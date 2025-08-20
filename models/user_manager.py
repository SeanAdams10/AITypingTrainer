"""User Manager for CRUD operations.
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
        # Always use lowercase for email comparisons
        email_address_lower = email_address.lower()
        query = "SELECT 1 FROM users WHERE LOWER(email_address) = LOWER(?)"
        params = [email_address_lower]
        if user_id is not None:
            query += " AND user_id != ?"
            params.append(user_id)
        if self.db_manager.fetchone(query, tuple(params)):
            raise UserValidationError(f"Email address '{email_address}' must be unique.")

    def get_user_by_id(self, user_id: str) -> User:
        row = self.db_manager.fetchone(
            "SELECT user_id, first_name, surname, email_address FROM users WHERE user_id = ?",
            (user_id,),
        )
        if not row:
            raise UserNotFound(f"User with ID {user_id} not found.")
        return User(
            user_id=row["user_id"],
            first_name=row["first_name"],
            surname=row["surname"],
            email_address=row["email_address"]
        )

    def get_user_by_email(self, email_address: str) -> User:
        # Use case-insensitive comparison for email retrieval
        query = (
            "SELECT user_id, first_name, surname, email_address FROM users "
            "WHERE LOWER(email_address) = LOWER(?)"
        )
        row = self.db_manager.fetchone(query, (email_address.lower(),))
        if not row:
            raise UserNotFound(f"User with email '{email_address}' not found.")
        return User(
            user_id=row["user_id"],
            first_name=row["first_name"],
            surname=row["surname"],
            email_address=row["email_address"]
        )

    def list_all_users(self) -> List[User]:
        query = (
            "SELECT user_id, first_name, surname, email_address FROM users "
            "ORDER BY surname, first_name"
        )
        rows = self.db_manager.fetchall(query)
        return [
            User(
                user_id=row["user_id"],
                first_name=row["first_name"],
                surname=row["surname"],
                email_address=row["email_address"]
            )
            for row in rows
        ]

    def save_user(self, user: User) -> bool:
        self._validate_email_uniqueness(user.email_address, user.user_id)
        if self.__user_exists(user.user_id):
            return self.__update_user(user)
        else:
            return self.__insert_user(user)

    def __user_exists(self, user_id: str) -> bool:
        row = self.db_manager.fetchone(
            "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
        )
        return row is not None

    def __insert_user(self, user: User) -> bool:
        self.db_manager.execute(
            "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            (user.user_id, user.first_name, user.surname, user.email_address.lower()),
        )
        return True

    def __update_user(self, user: User) -> bool:
        self.db_manager.execute(
            "UPDATE users SET first_name = ?, surname = ?, email_address = ? WHERE user_id = ?",
            (user.first_name, user.surname, user.email_address.lower(), user.user_id),
        )
        return True

    def delete_user_by_id(self, user_id: str) -> bool:
        if not self.db_manager.fetchone(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,),
        ):
            return False
        self.db_manager.execute(
            "DELETE FROM users WHERE user_id = ?",
            (user_id,),
        )
        return True

    def delete_user(self, user_id: str) -> bool:
        return self.delete_user_by_id(user_id)

    def delete_all_users(self) -> bool:
        count_result = self.db_manager.fetchone("SELECT COUNT(*) FROM users")
        # Handle different result structures safely
        if count_result:
            # Handle both dict and other result types
            if isinstance(count_result, dict):
                # Get the first value from the dict (COUNT(*) result)
                count = next(iter(count_result.values()), 0)
            else:
                # Fallback for other result types
                count = int(count_result) if count_result else 0
        else:
            count = 0
        self.db_manager.execute("DELETE FROM users")
        return count > 0
