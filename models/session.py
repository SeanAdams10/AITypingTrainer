"""Session module for backward compatibility with older tests.

This module provides the Session class that was previously part of
the ngram_analyzer module but has been moved as part of the refactoring.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator, model_validator


class Session(BaseModel):
    """Pydantic model for a typing practice session, matching the practice_sessions table.

    All fields are validated and session_id is a UUID string.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    snippet_id: str
    snippet_index_start: int
    snippet_index_end: int
    content: str
    start_time: datetime
    end_time: datetime
    actual_chars: int
    errors: int
    user_id: str
    keyboard_id: str

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }

    @field_validator("session_id", "snippet_id", "user_id", "keyboard_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the provided value is a valid UUID string."""
        uuid.UUID(v)
        return v

    @field_validator("snippet_index_start", "snippet_index_end")
    @classmethod
    def validate_indices(cls, v: int) -> int:
        """Ensure index values are non-negative integers."""
        if v < 0:
            raise ValueError("Indices must be >= 0")
        return v

    @model_validator(mode="after")
    def check_indices_and_times(self) -> "Session":
        """Validate cross-field constraints for indices and timestamps."""
        if self.snippet_index_end <= self.snippet_index_start:
            raise ValueError("snippet_index_end must be > snippet_index_start")
        if self.start_time > self.end_time:
            raise ValueError("start_time must be before end_time")
        if self.actual_chars and not self.content:
            raise ValueError("Content required if actual_chars > 0")
        return self

    @property
    def expected_chars(self) -> int:
        """Number of expected characters based on start/end indices."""
        return self.snippet_index_end - self.snippet_index_start

    @property
    def total_time(self) -> float:
        """Total session duration in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def efficiency(self) -> float:
        """Typing efficiency: actual_chars / expected_chars, capped at 1.0."""
        if self.expected_chars == 0:
            return 0.0
        return min(1.0, self.actual_chars / self.expected_chars)

    @property
    def correctness(self) -> float:
        """Correctness ratio: (actual_chars - errors) / actual_chars."""
        if self.actual_chars == 0:
            return 0.0
        return max(0.0, (self.actual_chars - self.errors) / self.actual_chars)

    @property
    def accuracy(self) -> float:
        """Accuracy ratio: (actual_chars - errors) / expected_chars."""
        if self.expected_chars == 0:
            return 0.0
        return max(0.0, (self.actual_chars - self.errors) / self.expected_chars)

    @property
    def session_cpm(self) -> float:
        """Characters per minute over the whole session."""
        if self.total_time == 0:
            return 0.0
        return self.actual_chars * 60.0 / self.total_time

    @property
    def session_wpm(self) -> float:
        """Words per minute (assuming 5 chars per word)."""
        if self.total_time == 0:
            return 0.0
        return (self.actual_chars / 5.0) * 60.0 / self.total_time

    @property
    def ms_per_keystroke(self) -> float:
        """Milliseconds per expected keystroke over the session duration."""
        if self.expected_chars == 0 or self.total_time == 0:
            return 0.0
        return (self.total_time * 1000.0) / self.expected_chars

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the model to a plain dict using Pydantic v2 `model_dump()`."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Session":
        """Create a Session from a dict, ignoring calculated properties."""
        # Create a copy of the input dictionary to avoid modifying the original
        data = d.copy()

        # Handle calculated fields that might be in the input
        calculated_fields = {
            "total_time", "session_wpm", "session_cpm", "expected_chars",
            "efficiency", "correctness", "accuracy", "ms_per_keystroke"
        }

        # Remove any calculated fields from the input data
        for field in calculated_fields:
            data.pop(field, None)

        # Use Pydantic's model_validate for proper validation
        try:
            return cls.model_validate(data)
        except ValueError as e:
            # Re-raise with a more specific message while preserving the original exception
            raise ValueError(f"Invalid session data: {str(e)}") from e

    def get_summary(self) -> str:
        """Return a summary of the session (business logic only)."""
        return (
            f"Session {self.session_id} for snippet {self.snippet_id} "
            f"(user {self.user_id}, keyboard {self.keyboard_id}): "
            f"{self.content[:10]}... ({self.actual_chars} chars, {self.errors} errors)"
        )
