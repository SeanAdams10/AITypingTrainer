"""
UserSettings Manager for CRUD operations.
Handles all DB access for user settings.
"""

from typing import List, Optional, Union

from db.database_manager import DatabaseManager
from models.user_setting import UserSetting


class UserSettingValidationError(Exception):
    """Exception raised when user setting validation fails.

    This exception is raised for validation errors such as invalid format
    or if a key that is not unique is attempted to be used for a user.
    """

    def __init__(self, message: str = "User setting validation failed") -> None:
        self.message = message
        super().__init__(self.message)


class UserSettingNotFound(Exception):
    """Exception raised when a requested user setting cannot be found.

    This exception is raised when attempting to access, modify or delete
    a user setting that does not exist in the database.
    """

    def __init__(self, message: str = "User setting not found") -> None:
        self.message = message
        super().__init__(self.message)


class UserSettingsManager:
    """
    Manager for CRUD operations on UserSetting, using DatabaseManager for DB access.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize UserSettingsManager with a DatabaseManager instance.
        """
        self.db_manager: DatabaseManager = db_manager
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """
        Ensure the user_settings table exists in the database.
        """
        self.db_manager.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_setting_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value_store TEXT NOT NULL,
                value_type TEXT NOT NULL,
                UNIQUE(user_id, setting_key)
            )
            """
        )

    def _validate_key_uniqueness(
        self, user_id: str, setting_key: str, user_setting_id: Optional[str] = None
    ) -> None:
        """
        Validate setting key is unique for the specified user.
        This complements the Pydantic model's format validation.

        Args:
            user_id: The ID of the user.
            setting_key: The setting key to validate.
            user_setting_id: The ID of the setting being updated, if any.

        Raises:
            UserSettingValidationError: If the key is not unique for the user.
        """
        query = "SELECT 1 FROM user_settings WHERE user_id = ? AND setting_key = ?"
        params = [user_id, setting_key]
        if user_setting_id is not None:
            query += " AND user_setting_id != ?"
            params.append(user_setting_id)

        if self.db_manager.execute(query, tuple(params)).fetchone():
            raise UserSettingValidationError(
                f"Setting key '{setting_key}' must be unique for user ID '{user_id}'."
            )

    def get_user_setting_by_key(self, user_id: str, setting_key: str) -> UserSetting:
        """
        Retrieve a single user setting by user ID and setting key.
        Args:
            user_id: The ID of the user.
            setting_key: The key of the setting to retrieve.
        Returns:
            UserSetting: The user setting with the specified key.
        Raises:
            UserSettingNotFound: If no setting exists with the specified key for the user.
        """
        row = self.db_manager.execute(
            """
            SELECT user_setting_id, user_id, setting_key, setting_value_store, value_type 
            FROM user_settings 
            WHERE user_id = ? AND setting_key = ?
            """,
            (user_id, setting_key),
        ).fetchone()

        if not row:
            raise UserSettingNotFound(
                f"Setting with key '{setting_key}' not found for user ID '{user_id}'."
            )

        # Convert the stored value based on type
        setting_value = self._convert_stored_value(row[3], row[4])

        return UserSetting(
            user_setting_id=row[0],
            user_id=row[1],
            setting_key=row[2],
            setting_value=setting_value,
            value_type=row[4],
        )

    def get_all_user_settings(self, user_id: str) -> List[UserSetting]:
        """
        List all settings for a specific user.
        Args:
            user_id: The ID of the user.
        Returns:
            List[UserSetting]: All settings for the specified user, ordered by setting key.
        """
        rows = self.db_manager.execute(
            """
            SELECT user_setting_id, user_id, setting_key, setting_value_store, value_type 
            FROM user_settings 
            WHERE user_id = ? 
            ORDER BY setting_key
            """,
            (user_id,),
        ).fetchall()

        settings = []
        for row in rows:
            # Convert the stored value based on type
            setting_value = self._convert_stored_value(row[3], row[4])

            settings.append(
                UserSetting(
                    user_setting_id=row[0],
                    user_id=row[1],
                    setting_key=row[2],
                    setting_value=setting_value,
                    value_type=row[4],
                )
            )

        return settings

    def save_user_setting(self, user_setting: UserSetting) -> bool:
        """
        Insert or update a user setting in the DB. Returns True if successful.
        Args:
            user_setting: The UserSetting object to save.
        Returns:
            True if the user setting was inserted or updated successfully.
        Raises:
            UserSettingValidationError: If the setting key is not unique for the user.
            ValueError: If validation fails (e.g., invalid data).
        """
        # Explicitly validate uniqueness before DB operation
        self._validate_key_uniqueness(
            user_setting.user_id, user_setting.setting_key, user_setting.user_setting_id
        )

        # Convert setting_value to string for storage
        setting_value_store = self._prepare_value_for_storage(user_setting.setting_value)

        if self.__user_setting_exists(user_setting.user_setting_id):
            return self.__update_user_setting(user_setting, setting_value_store)
        else:
            return self.__insert_user_setting(user_setting, setting_value_store)

    def delete_user_setting(self, user_id: str, setting_key: str) -> bool:
        """
        Delete a user setting by user ID and setting key.

        Args:
            user_id: The ID of the user.
            setting_key: The key of the setting to delete.

        Returns:
            bool: True if deleted, False if not found.
        """
        result = self.db_manager.execute(
            "DELETE FROM user_settings WHERE user_id = ? AND setting_key = ?",
            (user_id, setting_key),
        )
        return result.rowcount > 0

    def delete_all_settings_for_user(self, user_id: str) -> bool:
        """
        Delete all settings for a specific user.

        Args:
            user_id: The ID of the user.

        Returns:
            bool: True if any settings were deleted, False if none were found.
        """
        count = self.db_manager.execute(
            "SELECT COUNT(*) FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        self.db_manager.execute(
            "DELETE FROM user_settings WHERE user_id = ?", (user_id,)
        )
        return count > 0

    def __user_setting_exists(self, user_setting_id: str) -> bool:
        """
        Check if a user setting with the given ID exists.

        Args:
            user_setting_id: The ID of the user setting.

        Returns:
            bool: True if the user setting exists, False otherwise.
        """
        row = self.db_manager.execute(
            "SELECT 1 FROM user_settings WHERE user_setting_id = ?", (user_setting_id,)
        ).fetchone()
        return row is not None

    def __insert_user_setting(self, user_setting: UserSetting, setting_value_store: str) -> bool:
        """
        Insert a new user setting into the database.

        Args:
            user_setting: The UserSetting to insert.
            setting_value_store: The prepared setting value for storage.

        Returns:
            bool: True if the insertion was successful.
        """
        self.db_manager.execute(
            """
            INSERT INTO user_settings 
                (user_setting_id, user_id, setting_key, setting_value_store, value_type) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_setting.user_setting_id,
                user_setting.user_id,
                user_setting.setting_key,
                setting_value_store,
                user_setting.value_type,
            ),
        )
        return True

    def __update_user_setting(self, user_setting: UserSetting, setting_value_store: str) -> bool:
        """
        Update an existing user setting in the database.

        Args:
            user_setting: The UserSetting to update.
            setting_value_store: The prepared setting value for storage.

        Returns:
            bool: True if the update was successful.
        """
        self.db_manager.execute(
            """
            UPDATE user_settings 
            SET user_id = ?, setting_key = ?, setting_value_store = ?, value_type = ? 
            WHERE user_setting_id = ?
            """,
            (
                user_setting.user_id,
                user_setting.setting_key,
                setting_value_store,
                user_setting.value_type,
                user_setting.user_setting_id,
            ),
        )
        return True

    def _prepare_value_for_storage(self, value: Union[str, float, int]) -> str:
        """
        Prepare a setting value for storage in the database.

        Args:
            value: The setting value to prepare.

        Returns:
            str: The prepared value as a string.
        """
        return str(value)

    def _convert_stored_value(self, stored_value: str, value_type: str) -> Union[str, float, int]:
        """
        Convert a stored setting value to the appropriate type.

        Args:
            stored_value: The stored value as a string.
            value_type: The type of the value ("str", "float", or "int").

        Returns:
            Union[str, float, int]: The converted value.

        Raises:
            ValueError: If the value cannot be converted to the specified type.
        """
        if value_type == "str":
            return stored_value
        elif value_type == "float":
            try:
                return float(stored_value)
            except ValueError:
                raise ValueError(f"Cannot convert '{stored_value}' to float.")
        elif value_type == "int":
            try:
                return int(stored_value)
            except ValueError:
                raise ValueError(f"Cannot convert '{stored_value}' to int.")
        else:
            raise ValueError(f"Unsupported value_type: {value_type}")
