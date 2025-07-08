from pathlib import Path
from typing import Generator
from uuid import uuid4

import pytest
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager, KeyboardNotFound, KeyboardValidationError


@pytest.fixture
def db_manager(tmp_path: Path) -> Generator[DatabaseManager, None, None]:
    db_file = tmp_path / "test_keyboards.db"
    db = DatabaseManager(str(db_file))
    db.init_tables()
    user_id = str(uuid4())
    db.execute(
        "INSERT INTO users (user_id, first_name, surname, email_address) VALUES (?, ?, ?, ?)",
        (user_id, "Test", "User", "test@example.com"),
    )
    yield db
    db.close()


@pytest.fixture
def keyboard_manager(db_manager: DatabaseManager) -> KeyboardManager:
    return KeyboardManager(db_manager)


def test_create_keyboard(keyboard_manager: KeyboardManager, db_manager: DatabaseManager) -> None:
    user_id = db_manager.fetchall("SELECT user_id FROM users")[0]["user_id"]
    k = Keyboard(user_id=user_id, keyboard_name="Alpha")
    assert keyboard_manager.save_keyboard(k)
    # Uniqueness enforced
    k2 = Keyboard(user_id=user_id, keyboard_name="Alpha")
    with pytest.raises(KeyboardValidationError):
        keyboard_manager.save_keyboard(k2)


def test_get_keyboard(keyboard_manager: KeyboardManager, db_manager: DatabaseManager) -> None:
    user_id = db_manager.fetchall("SELECT user_id FROM users")[0]["user_id"]
    k = Keyboard(user_id=user_id, keyboard_name="Beta")
    keyboard_manager.save_keyboard(k)
    fetched = keyboard_manager.get_keyboard_by_id(k.keyboard_id)
    assert fetched.keyboard_id == k.keyboard_id
    assert fetched.keyboard_name == "Beta"


def test_update_keyboard_name(
    keyboard_manager: KeyboardManager, db_manager: DatabaseManager
) -> None:
    user_id = db_manager.fetchall("SELECT user_id FROM users")[0]["user_id"]
    k = Keyboard(user_id=user_id, keyboard_name="Gamma")
    keyboard_manager.save_keyboard(k)
    k.keyboard_name = "Delta"
    assert keyboard_manager.save_keyboard(k)
    updated = keyboard_manager.get_keyboard_by_id(k.keyboard_id)
    assert updated.keyboard_name == "Delta"
    # Uniqueness enforced
    k2 = Keyboard(user_id=user_id, keyboard_name="Epsilon")
    keyboard_manager.save_keyboard(k2)
    k.keyboard_name = "Epsilon"
    with pytest.raises(KeyboardValidationError):
        keyboard_manager.save_keyboard(k)


def test_update_keyboard_target_speed(
    keyboard_manager: KeyboardManager, db_manager: DatabaseManager
) -> None:
    """Test updating the target_ms_per_keystroke field."""
    user_id = db_manager.fetchall("SELECT user_id FROM users")[0]["user_id"]

    # Create keyboard with default target speed (100)
    k = Keyboard(user_id=user_id, keyboard_name="Speed Test", target_ms_per_keystroke=100)
    keyboard_manager.save_keyboard(k)

    # Verify the default value was saved
    saved = keyboard_manager.get_keyboard_by_id(k.keyboard_id)
    assert saved.target_ms_per_keystroke == 100

    # Update the target speed
    k.target_ms_per_keystroke = 250
    assert keyboard_manager.save_keyboard(k)

    # Verify the updated value was saved
    updated = keyboard_manager.get_keyboard_by_id(k.keyboard_id)
    assert updated.target_ms_per_keystroke == 250

    # Test invalid values are rejected
    with pytest.raises(ValidationError):
        k.target_ms_per_keystroke = 5001  # Above max


def test_delete_keyboard(keyboard_manager: KeyboardManager, db_manager: DatabaseManager) -> None:
    user_id = db_manager.fetchall("SELECT user_id FROM users")[0]["user_id"]
    k = Keyboard(user_id=user_id, keyboard_name="Zeta")
    keyboard_manager.save_keyboard(k)
    assert keyboard_manager.delete_keyboard(k.keyboard_id)
    with pytest.raises(KeyboardNotFound):
        keyboard_manager.get_keyboard_by_id(k.keyboard_id)
