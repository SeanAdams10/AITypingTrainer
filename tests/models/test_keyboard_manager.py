"""Tests for keyboard manager functionality.

Tests for keyboard management, storage, and configuration.
"""
import pytest
from pydantic import ValidationError

from db.database_manager import DatabaseManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager, KeyboardNotFound, KeyboardValidationError
from models.user import User


@pytest.fixture
def keyboard_manager(db_with_tables: DatabaseManager) -> KeyboardManager:
    return KeyboardManager(db_with_tables)


def test_create_keyboard(keyboard_manager: KeyboardManager, test_user: User) -> None:
    k = Keyboard(user_id=str(test_user.user_id), keyboard_name="Alpha")
    assert keyboard_manager.save_keyboard(k)
    # Uniqueness enforced
    k2 = Keyboard(user_id=str(test_user.user_id), keyboard_name="Alpha")
    with pytest.raises(KeyboardValidationError):
        keyboard_manager.save_keyboard(k2)


def test_get_keyboard(keyboard_manager: KeyboardManager, test_user: User) -> None:
    k = Keyboard(user_id=str(test_user.user_id), keyboard_name="Beta")
    keyboard_manager.save_keyboard(k)
    fetched = keyboard_manager.get_keyboard_by_id(k.keyboard_id)
    assert fetched.keyboard_id == k.keyboard_id
    assert fetched.keyboard_name == "Beta"


def test_update_keyboard_name(keyboard_manager: KeyboardManager, test_user: User) -> None:
    k = Keyboard(user_id=str(test_user.user_id), keyboard_name="Gamma")
    keyboard_manager.save_keyboard(k)
    k.keyboard_name = "Delta"
    assert keyboard_manager.save_keyboard(k)
    updated = keyboard_manager.get_keyboard_by_id(k.keyboard_id)
    assert updated.keyboard_name == "Delta"
    # Uniqueness enforced
    k2 = Keyboard(user_id=str(test_user.user_id), keyboard_name="Epsilon")
    keyboard_manager.save_keyboard(k2)
    k.keyboard_name = "Epsilon"
    with pytest.raises(KeyboardValidationError):
        keyboard_manager.save_keyboard(k)


def test_update_keyboard_target_speed(keyboard_manager: KeyboardManager, test_user: User) -> None:
    """Test updating the target_ms_per_keystroke field."""
    # Create keyboard with default target speed (100)
    k = Keyboard(
        user_id=str(test_user.user_id),
        keyboard_name="Speed Test",
        target_ms_per_keystroke=100,
    )
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


def test_delete_keyboard(keyboard_manager: KeyboardManager, test_user: User) -> None:
    k = Keyboard(user_id=str(test_user.user_id), keyboard_name="Zeta")
    keyboard_manager.save_keyboard(k)
    assert keyboard_manager.delete_keyboard(k.keyboard_id)
    with pytest.raises(KeyboardNotFound):
        keyboard_manager.get_keyboard_by_id(k.keyboard_id)
