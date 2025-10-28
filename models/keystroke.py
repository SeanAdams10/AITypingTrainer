"""Keystroke model for tracking keystrokes during practice sessions."""

import datetime
import logging
import unicodedata
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class Keystroke(BaseModel):
    """Pydantic model for tracking individual keystrokes in practice sessions."""

    session_id: Optional[str] = None
    keystroke_id: Optional[str] = None  # Changed from int to str (UUID)
    keystroke_time: datetime.datetime = Field(default_factory=datetime.datetime.now)
    keystroke_char: str = ""
    expected_char: str = ""
    is_error: bool = False
    time_since_previous: Optional[int] = None
    text_index: int = Field(
        default=0, ge=0, description="Index of the expected character in the text being typed"
    )
    key_index: int = Field(
        default=0, ge=0, description="Order index of the key pressed in the drill (0-based)"
    )

    @field_validator("expected_char", "keystroke_char", mode="before")
    @classmethod
    def _normalize_nfc(cls, v: object) -> str:
        """Normalize character fields to NFC form for consistent comparisons.

        The n-gram spec requires NFC normalization when comparing expected vs actual
        characters. Ensure both fields are normalized upon model creation.
        """
        if v is None:
            return ""
        if not isinstance(v, str):
            v = str(v)
        return unicodedata.normalize("NFC", v)

    @field_validator("text_index")
    @classmethod
    def validate_text_index(cls, v: int) -> int:
        """Ensure text_index is a non-negative integer."""
        if v < 0:
            raise ValueError("text_index must be a non-negative integer")
        return v

    @field_validator("key_index")
    @classmethod
    def validate_key_index(cls, v: int) -> int:
        """Ensure key_index is a non-negative integer."""
        if v < 0:
            raise ValueError("key_index must be a non-negative integer")
        return v

    @classmethod
    def from_dict(cls, *, data: Dict[str, Any]) -> "Keystroke":
        """Create a Keystroke instance from a dictionary, ensuring UUID IDs."""
        # Handle datetime conversion
        keystroke_time = data.get("keystroke_time")
        if isinstance(keystroke_time, str):
            try:
                keystroke_time = datetime.datetime.fromisoformat(
                    keystroke_time.replace("Z", "+00:00")
                )
            except ValueError:
                keystroke_time = datetime.datetime.now()
        if not isinstance(keystroke_time, datetime.datetime):
            keystroke_time = datetime.datetime.now()

        # Handle boolean conversion
        is_error = data.get("is_error")
        if isinstance(is_error, str):
            is_error = is_error.lower() in ("true", "1", "t", "y", "yes")
        elif isinstance(is_error, int):
            is_error = bool(is_error)
        if not isinstance(is_error, bool):
            is_error = bool(is_error)

        # Ensure IDs are UUID strings
        session_id = data.get("session_id")
        if session_id is not None and not isinstance(session_id, str):
            try:
                session_id = str(session_id)
            except (ValueError, TypeError):
                session_id = None
        if not isinstance(session_id, str) or session_id.startswith("{"):
            session_id = None

        keystroke_id = data.get("keystroke_id")
        if keystroke_id is None:
            keystroke_id = str(uuid.uuid4())
        elif not isinstance(keystroke_id, str):
            try:
                keystroke_id = str(keystroke_id)
            except (ValueError, TypeError):
                keystroke_id = str(uuid.uuid4())

        # Handle text_index conversion
        text_index = data.get("text_index", 0)
        if isinstance(text_index, str):
            try:
                text_index = int(text_index)
            except (ValueError, TypeError):
                text_index = 0
        elif not isinstance(text_index, int):
            text_index = 0

        # Ensure text_index is non-negative
        if text_index < 0:
            text_index = 0

        # Handle key_index conversion
        key_index = data.get("key_index", 0)
        if isinstance(key_index, str):
            try:
                key_index = int(key_index)
            except (ValueError, TypeError):
                key_index = 0
        elif not isinstance(key_index, int):
            key_index = 0

        # Ensure key_index is non-negative
        if key_index < 0:
            key_index = 0

        return cls(
            session_id=session_id,
            keystroke_id=keystroke_id,
            keystroke_time=keystroke_time,
            keystroke_char=data.get("keystroke_char", ""),
            expected_char=data.get("expected_char", ""),
            is_error=is_error,
            time_since_previous=data.get("time_since_previous"),
            text_index=text_index,
            key_index=key_index,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the keystroke to a dictionary with UUID IDs."""
        return {
            "session_id": self.session_id,
            "keystroke_id": self.keystroke_id,
            # Format the timestamp properly
            "keystroke_time": (self.keystroke_time.isoformat() if self.keystroke_time else None),
            "keystroke_char": self.keystroke_char,
            "expected_char": self.expected_char,
            "is_error": self.is_error,
            "time_since_previous": self.time_since_previous,
            "text_index": self.text_index,
            "key_index": self.key_index,
        }
