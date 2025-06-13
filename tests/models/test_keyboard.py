from uuid import uuid4

import pytest
from pydantic import ValidationError

from models.keyboard import Keyboard


def test_keyboard_valid() -> None:
    k = Keyboard(keyboard_id=str(uuid4()), user_id=str(uuid4()), keyboard_name="My Keyboard")
    assert k.keyboard_name == "My Keyboard"


def test_keyboard_empty_name() -> None:
    with pytest.raises(ValidationError):
        Keyboard(keyboard_id=str(uuid4()), user_id=str(uuid4()), keyboard_name="  ")


def test_keyboard_name_strip() -> None:
    k = Keyboard(keyboard_id=str(uuid4()), user_id=str(uuid4()), keyboard_name="  Test  ")
    assert k.keyboard_name == "Test"
