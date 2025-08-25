"""Keyboard Manager for CRUD operations.

Handles all DB access for keyboards.
"""

from typing import Any, Dict, List, Optional, Tuple, Union, cast

from db.database_manager import DatabaseManager
from models.keyboard import Keyboard


class KeyboardValidationError(Exception):
    """Raised when keyboard data fails validation checks."""

    def __init__(self, message: str = "Keyboard validation failed") -> None:
        """Initialize the error with a helpful message."""
        self.message = message
        super().__init__(self.message)


class KeyboardNotFound(Exception):
    """Raised when a keyboard entity cannot be found in the database."""

    def __init__(self, message: str = "Keyboard not found") -> None:
        """Initialize the error with a helpful message."""
        self.message = message
        super().__init__(self.message)


class KeyboardManager:
    """Service layer for managing `Keyboard` entities via `DatabaseManager`."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Create a new manager using the provided database manager."""
        self.db_manager: DatabaseManager = db_manager

    # Internal types used for DB rows
    _Row = Union[Dict[str, object], Tuple[object, ...]]

    def _get_val(self, row: _Row, key: str, index: int) -> object:
        """Return a value from a row that may be a dict or a tuple."""
        if isinstance(row, dict):
            return row.get(key)
        return row[index]

    def _row_to_keyboard(self, row: _Row) -> Keyboard:
        """Convert a DB row (dict or tuple) to a validated Keyboard instance."""
        keyboard_id_val = self._get_val(row, "keyboard_id", 0)
        user_id_val = self._get_val(row, "user_id", 1)
        keyboard_name_val = self._get_val(row, "keyboard_name", 2)
        target_val = self._get_val(row, "target_ms_per_keystroke", 3)

        # Coerce to expected types; validation will run in the model too
        keyboard_id_str: Optional[str]
        if keyboard_id_val is None:
            keyboard_id_str = None
        else:
            keyboard_id_str = str(keyboard_id_val)

        return Keyboard(
            keyboard_id=keyboard_id_str,
            user_id=str(user_id_val),
            keyboard_name=str(keyboard_name_val),
            target_ms_per_keystroke=int(cast(Any, target_val)),
        )

    def _validate_name_uniqueness(
        self, keyboard_name: str, user_id: str, keyboard_id: Optional[str] = None
    ) -> None:
        query = "SELECT 1 FROM keyboards WHERE keyboard_name = ? AND user_id = ?"
        params = [keyboard_name, user_id]
        if keyboard_id is not None:
            query += " AND keyboard_id != ?"
            params.append(keyboard_id)
        if self.db_manager.execute(query, tuple(params)).fetchone():
            raise KeyboardValidationError(
                f"Keyboard name '{keyboard_name}' must be unique for this user."
            )

    def get_keyboard_by_id(self, keyboard_id: str) -> Keyboard:
        """Return a `Keyboard` by its ID or raise `KeyboardNotFound`."""
        row_opt = self.db_manager.execute(
            """
            SELECT keyboard_id, user_id, keyboard_name, target_ms_per_keystroke
            FROM keyboards
            WHERE keyboard_id = ?
            """,
            (keyboard_id,),
        ).fetchone()
        if not row_opt:
            raise KeyboardNotFound(f"Keyboard with ID {keyboard_id} not found.")
        row = cast(KeyboardManager._Row, row_opt)
        return self._row_to_keyboard(row)

    def list_keyboards_for_user(self, user_id: str) -> List[Keyboard]:
        """List all keyboards for a given user, ordered by name."""
        rows_raw = self.db_manager.execute(
            """
            SELECT keyboard_id, user_id, keyboard_name, target_ms_per_keystroke
            FROM keyboards
            WHERE user_id = ?
            ORDER BY keyboard_name
            """,
            (user_id,),
        ).fetchall()
        rows_typed: List[KeyboardManager._Row] = cast(
            List[KeyboardManager._Row], rows_raw
        )
        return [self._row_to_keyboard(r) for r in rows_typed]

    def save_keyboard(self, keyboard: Keyboard) -> bool:
        """Insert or update the keyboard after validation; return True on success."""
        self._validate_name_uniqueness(
            keyboard.keyboard_name, keyboard.user_id, keyboard.keyboard_id
        )
        if self.__keyboard_exists(keyboard.keyboard_id):
            return self.__update_keyboard(keyboard)
        else:
            return self.__insert_keyboard(keyboard)

    def __keyboard_exists(self, keyboard_id: str | None) -> bool:
        if not keyboard_id:
            return False

        row = self.db_manager.execute(
            "SELECT 1 FROM keyboards WHERE keyboard_id = ?", (keyboard_id,)
        ).fetchone()
        return row is not None

    def __insert_keyboard(self, keyboard: Keyboard) -> bool:
        self.db_manager.execute(
            """
            INSERT INTO keyboards
            (keyboard_id, user_id, keyboard_name, target_ms_per_keystroke)
            VALUES (?, ?, ?, ?)
            """,
            (
                keyboard.keyboard_id,
                keyboard.user_id,
                keyboard.keyboard_name,
                keyboard.target_ms_per_keystroke
            ),
        )
        return True

    def __update_keyboard(self, keyboard: Keyboard) -> bool:
        self.db_manager.execute(
            """
            UPDATE keyboards
            SET user_id = ?, keyboard_name = ?, target_ms_per_keystroke = ?
            WHERE keyboard_id = ?
            """,
            (
                keyboard.user_id,
                keyboard.keyboard_name,
                keyboard.target_ms_per_keystroke,
                keyboard.keyboard_id
            ),
        )
        return True

    def delete_keyboard_by_id(self, keyboard_id: str) -> bool:
        """Delete keyboard by ID; return False if it does not exist."""
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
        """Alias for `delete_keyboard_by_id` for API symmetry."""
        return self.delete_keyboard_by_id(keyboard_id)

    def delete_all_keyboards(self) -> bool:
        """Delete all keyboards; return True if any rows were removed."""
        # Alias the column for predictable dict-key access; support tuple as well
        count_row_opt = self.db_manager.execute(
            "SELECT COUNT(*) AS cnt FROM keyboards"
        ).fetchone()
        cnt: int = 0
        if count_row_opt is not None:
            if isinstance(count_row_opt, tuple):
                tup: Tuple[Any, ...] = cast(Tuple[Any, ...], count_row_opt)
                first = tup[0]
                if isinstance(first, int):
                    cnt = first
                elif isinstance(first, (float, str)):
                    cnt = int(first)
                else:
                    cnt = 0
            elif isinstance(count_row_opt, dict):
                dct: Dict[str, Any] = cast(Dict[str, Any], count_row_opt)
                val = dct.get("cnt", 0)
                if isinstance(val, int):
                    cnt = val
                elif isinstance(val, (float, str)):
                    cnt = int(val)
                else:
                    cnt = 0
        
        self.db_manager.execute("DELETE FROM keyboards")
        return cnt > 0
