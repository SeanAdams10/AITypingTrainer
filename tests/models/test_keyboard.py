"""Tests for keyboard functionality.

Tests for keyboard input handling, key mapping, and input validation.
"""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.keyboard import Keyboard


def test_keyboard_valid() -> None:
    """Test creating a valid keyboard instance."""
    k = Keyboard(
        keyboard_id=str(uuid4()),
        user_id=str(uuid4()),
        keyboard_name="My Keyboard",
        target_ms_per_keystroke=120,
    )
    assert k.keyboard_name == "My Keyboard"
    assert k.target_ms_per_keystroke == 120


def test_keyboard_empty_name() -> None:
    """Test that empty keyboard name raises ValidationError."""
    with pytest.raises(ValidationError):
        Keyboard(keyboard_id=str(uuid4()), user_id=str(uuid4()), keyboard_name="  ")


def test_keyboard_name_strip() -> None:
    """Test that keyboard name is automatically stripped of whitespace."""
    k = Keyboard(keyboard_id=str(uuid4()), user_id=str(uuid4()), keyboard_name="  Test  ")
    assert k.keyboard_name == "Test"


def test_keyboard_default_target_ms() -> None:
    """Test that default target_ms value of 600 is used when not specified."""
    # Test that default value of 600 is used when not specified
    k = Keyboard(keyboard_id=str(uuid4()), user_id=str(uuid4()), keyboard_name="Test")
    assert k.target_ms_per_keystroke == 600


def test_keyboard_custom_target_ms() -> None:
    """Test that custom target_ms value is stored correctly."""
    # Test that custom value is stored correctly
    k = Keyboard(
        keyboard_id=str(uuid4()),
        user_id=str(uuid4()),
        keyboard_name="Test",
        target_ms_per_keystroke=500,
    )
    assert k.target_ms_per_keystroke == 500


def test_keyboard_target_ms_too_low() -> None:
    """Test that validator rejects target_ms values below 50."""
    # Test that validator rejects values below 50
    with pytest.raises(ValidationError) as excinfo:
        Keyboard(
            keyboard_id=str(uuid4()),
            user_id=str(uuid4()),
            keyboard_name="Test",
            target_ms_per_keystroke=49,
        )
    assert "Target milliseconds per keystroke must be between 50 and 5000" in str(excinfo.value)


def test_keyboard_target_ms_too_high() -> None:
    """Test that validator rejects target_ms values above 5000."""
    # Test that validator rejects values above 5000
    with pytest.raises(ValidationError) as excinfo:
        Keyboard(
            keyboard_id=str(uuid4()),
            user_id=str(uuid4()),
            keyboard_name="Test",
            target_ms_per_keystroke=5001,
        )
    assert "Target milliseconds per keystroke must be between 50 and 5000" in str(excinfo.value)


def test_keyboard_target_ms_none() -> None:
    """Test that validator rejects None values for target_ms."""
    # Test that validator rejects None values
    with pytest.raises(ValidationError):
        # We need to use a dict and model_validate to bypass Pydantic's type checking
        # and test our explicit None validator
        Keyboard.model_validate(
            {
                "keyboard_id": str(uuid4()),
                "user_id": str(uuid4()),
                "keyboard_name": "Test",
                "target_ms_per_keystroke": None,
            }
        )
    # assert "Target milliseconds per keystroke cannot be None" in str(excinfo.value)
