"""
Keyboard Manager for CRUD operations.
Handles all DB access for keyboards.
"""
from typing import List, Optional
from db.database_manager import DatabaseManager
from models.keyboard import Keyboard

class KeyboardValidationError(Exception):
    def __init__(self, message: str = "Keyboard validation failed") -> None:
        self.message = message
        super().__init__(self.message)

class KeyboardNotFound(Exception):
    def __init__(self, message: str = "Keyboard not found") -> None:
        self.message = message
        super().__init__(self.message)

class KeyboardManager:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager: DatabaseManager = db_manager

    def _validate_name_uniqueness(self, keyboard_name: str, user_id: str, keyboard_id: Optional[str] = None) -> None:
        query = "SELECT 1 FROM keyboards WHERE keyboard_name = ? AND user_id = ?"
        params = [keyboard_name, user_id]
        if keyboard_id is not None:
            query += " AND keyboard_id != ?"
            params.append(keyboard_id)
        if self.db_manager.execute(query, tuple(params)).fetchone():
            raise KeyboardValidationError(f"Keyboard name '{keyboard_name}' must be unique for this user.")

    def get_keyboard_by_id(self, keyboard_id: str) -> Keyboard:
        row = self.db_manager.execute(
            "SELECT keyboard_id, user_id, keyboard_name FROM keyboards WHERE keyboard_id = ?",
            (keyboard_id,),
        ).fetchone()
        if not row:
            raise KeyboardNotFound(f"Keyboard with ID {keyboard_id} not found.")
        return Keyboard(keyboard_id=row[0], user_id=row[1], keyboard_name=row[2])

    def list_keyboards_for_user(self, user_id: str) -> List[Keyboard]:
        rows = self.db_manager.execute(
            "SELECT keyboard_id, user_id, keyboard_name FROM keyboards WHERE user_id = ? ORDER BY keyboard_name",
            (user_id,)
        ).fetchall()
        return [Keyboard(keyboard_id=row[0], user_id=row[1], keyboard_name=row[2]) for row in rows]

    def save_keyboard(self, keyboard: Keyboard) -> bool:
        self._validate_name_uniqueness(keyboard.keyboard_name, keyboard.user_id, keyboard.keyboard_id)
        if self.__keyboard_exists(keyboard.keyboard_id):
            return self.__update_keyboard(keyboard)
        else:
            return self.__insert_keyboard(keyboard)

    def __keyboard_exists(self, keyboard_id: str) -> bool:
        row = self.db_manager.execute(
            "SELECT 1 FROM keyboards WHERE keyboard_id = ?", (keyboard_id,)
        ).fetchone()
        return row is not None

    def __insert_keyboard(self, keyboard: Keyboard) -> bool:
        self.db_manager.execute(
            "INSERT INTO keyboards (keyboard_id, user_id, keyboard_name) VALUES (?, ?, ?)",
            (keyboard.keyboard_id, keyboard.user_id, keyboard.keyboard_name),
        )
        return True

    def __update_keyboard(self, keyboard: Keyboard) -> bool:
        self.db_manager.execute(
            "UPDATE keyboards SET user_id = ?, keyboard_name = ? WHERE keyboard_id = ?",
            (keyboard.user_id, keyboard.keyboard_name, keyboard.keyboard_id),
        )
        return True

    def delete_keyboard_by_id(self, keyboard_id: str) -> bool:
        if not self.db_manager.execute(
            "SELECT 1 FROM keyboards WHERE keyboard_id = ?",
            (keyboard_id,),
        ).fetchone():
            return False
        self.db_manager.execute(
            "DELETE FROM keyboards WHERE keyboard_id = ?",
            (keyboard_id,),
        )
        return True

    def delete_keyboard(self, keyboard_id: str) -> bool:
        return self.delete_keyboard_by_id(keyboard_id)

    def delete_all_keyboards(self) -> bool:
        count = self.db_manager.execute("SELECT COUNT(*) FROM keyboards").fetchone()[0]
        self.db_manager.execute("DELETE FROM keyboards")
        return count > 0
