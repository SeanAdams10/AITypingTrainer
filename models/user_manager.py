"""User Manager for CRUD operations.

Handles all DB access for users.
"""

from typing import List, Optional

from db.database_manager import DatabaseManager
from models.user import User


class UserValidationError(Exception):
    """Raised when a user record fails validation checks."""

    def __init__(self, message: str = "User validation failed") -> None:
        """Initialize the exception with an optional message."""
        self.message = message
        super().__init__(self.message)


class UserNotFound(Exception):
    """Raised when a requested user cannot be found in the database."""

    def __init__(self, message: str = "User not found") -> None:
        """Initialize the exception with an optional message."""
        self.message = message
        super().__init__(self.message)


class UserManager:
    """CRUD operations and queries for `User` objects via `DatabaseManager`."""

    def __init__(self, *, db_manager: DatabaseManager) -> None:
        """Create a new `UserManager` bound to the given database manager."""
        self.db_manager: DatabaseManager = db_manager

    def _validate_email_uniqueness(self, *, email_address: str, user_id: Optional[str] = None) -> None:
        """Ensure no other user has the same email address.

        Uses a case-insensitive check. When `user_id` is provided, it is excluded
        from the uniqueness check to support updates.
        """
        # Always use lowercase for email comparisons
        email_address_lower = email_address.lower()
        query = "SELECT 1 FROM users WHERE LOWER(email_address) = LOWER(?)"
        params = [email_address_lower]
        if user_id is not None:
            query += " AND user_id != ?"
            params.append(user_id)
        if self.db_manager.fetchone(query=query, params=tuple(params)):
            raise UserValidationError(f"Email address '{email_address}' must be unique.")

    def get_user_by_id(self, *, user_id: str) -> User:
        """Return a `User` by its UUID string or raise `UserNotFound`."""
        row = self.db_manager.fetchone(
            query="SELECT user_id, first_name, surname, email_address FROM users WHERE user_id = ?",
            params=(user_id,),
        )
        if not row:
            raise UserNotFound(f"User with ID {user_id} not found.")
        return User(
            user_id=str(row["user_id"]) if row["user_id"] is not None else None,
            first_name=str(row["first_name"]),
            surname=str(row["surname"]),
            email_address=str(row["email_address"]),
        )

    def get_user_by_email(self, *, email_address: str) -> User:
        """Return a `User` by email (case-insensitive) or raise `UserNotFound`."""
        # Use case-insensitive comparison for email retrieval
        query = (
            "SELECT user_id, first_name, surname, email_address FROM users "
            "WHERE LOWER(email_address) = LOWER(?)"
        )
        row = self.db_manager.fetchone(query=query, params=(email_address.lower(),))
        if not row:
            raise UserNotFound(f"User with email '{email_address}' not found.")
        return User(
            user_id=str(row["user_id"]) if row["user_id"] is not None else None,
            first_name=str(row["first_name"]),
            surname=str(row["surname"]),
            email_address=str(row["email_address"]),
        )

    def list_all_users(self) -> List[User]:
        """Return all users ordered by surname, then first name."""
        query = (
            "SELECT user_id, first_name, surname, email_address FROM users "
            "ORDER BY surname, first_name"
        )
        rows = self.db_manager.fetchall(query=query)
        return [
            User(
                user_id=str(row["user_id"]) if row["user_id"] is not None else None,
                first_name=str(row["first_name"]),
                surname=str(row["surname"]),
                email_address=str(row["email_address"]),
            )
            for row in rows
        ]

    def save_user(self, *, user: User) -> bool:
        """Insert or update the given user; returns True on success."""
        self._validate_email_uniqueness(email_address=user.email_address, user_id=user.user_id)
        if user.user_id and self.__user_exists(user_id=user.user_id):
            return self.__update_user(user=user)
        else:
            return self.__insert_user(user=user)

    def __user_exists(self, *, user_id: str) -> bool:
        """Return True if a user with the given ID exists."""
        row = self.db_manager.fetchone(query="SELECT 1 FROM users WHERE user_id = ?", params=(user_id,))
        return row is not None

    def __insert_user(self, *, user: User) -> bool:
        """Insert a new user row and return True."""
        self.db_manager.execute(
            query="INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
            params=(user.user_id, user.first_name, user.surname, user.email_address.lower()),
        )
        return True

    def __update_user(self, *, user: User) -> bool:
        """Update an existing user row and return True."""
        self.db_manager.execute(
            query="UPDATE users SET first_name = ?, surname = ?, email_address = ? WHERE user_id = ?",
            params=(user.first_name, user.surname, user.email_address.lower(), user.user_id),
        )
        return True

    def delete_user_by_id(self, *, user_id: str) -> bool:
        """Delete a user by ID; returns True if a row was deleted."""
        if not self.db_manager.fetchone(
            query="SELECT 1 FROM users WHERE user_id = ?",
            params=(user_id,),
        ):
            return False
        self.db_manager.execute(
            query="DELETE FROM users WHERE user_id = ?",
            params=(user_id,),
        )
        return True

    def delete_user(self, *, user_id: str) -> bool:
        """Alias for `delete_user_by_id` to satisfy existing call sites."""
        return self.delete_user_by_id(user_id=user_id)

    def delete_all_users(self) -> bool:
        """Delete all users and return True if any rows existed prior to deletion."""
        count_result = self.db_manager.fetchone(query="SELECT COUNT(*) FROM users")
        # Handle different result structures safely
        count = 0
        if count_result:
            if isinstance(count_result, dict):
                # Get the first value from the dict (COUNT(*) result)
                first_value = next(iter(count_result.values()), 0)
                count = int(str(first_value)) if first_value is not None else 0
            elif isinstance(count_result, (tuple, list)) and len(count_result) > 0:
                # Handle tuple/list result (e.g., (5,))
                count = int(str(count_result[0]))
            else:
                # Fallback for other result types
                count = int(str(count_result))

        self.db_manager.execute(query="DELETE FROM users")
        return count > 0
