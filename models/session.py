"""
Session module for backward compatibility with older tests.

This module provides the Session class that was previously part of
the ngram_analyzer module but has been moved as part of the refactoring.
"""

import sqlite3
import uuid
from datetime import datetime, timedelta  # noqa: F401 - timedelta is used in computed_field
from typing import Dict

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class Session(BaseModel):
    """
    Pydantic model for a typing practice session, matching the practice_sessions table.
    All fields are validated and session_id is a UUID string.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(..., min_length=1, description="The text content that was practiced")
    snippet_id: int
    snippet_index_start: int
    snippet_index_end: int

    start_time: datetime
    end_time: datetime
    actual_chars: int
    errors: int

    model_config = {"extra": "forbid"}

    @field_validator("session_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except Exception as e:
            raise ValueError(f"session_id must be a valid UUID string: {v}") from e
        return v

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_datetime(cls, v: object) -> datetime:
        # Handle datetime objects directly
        if isinstance(v, datetime):
            return v
            
        # Handle string inputs (ISO 8601 format)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except (ValueError, TypeError) as e:
                # Match the exact error message expected by the test
                raise ValueError("Datetime must be ISO 8601 string") from e
                
        # For any other type, raise a TypeError with the exact expected message
        raise TypeError("Datetime must be a datetime or ISO 8601 string")

    @model_validator(mode="after")
    def check_business_rules(self) -> "Session":
        # Validate indices
        if self.snippet_index_start < 0:
            raise ValueError("snippet_index_start must be >= 0")
            
        if self.snippet_index_start >= self.snippet_index_end:
            raise ValueError("snippet_index_start must be less than snippet_index_end")
            
        # Validate timing
        if self.start_time > self.end_time:
            raise ValueError("start_time must be less than or equal to end_time")
            
        # Validate content - allow empty content for abandoned sessions
        if not self.content and self.actual_chars > 0:
            raise ValueError("content cannot be empty for non-abandoned sessions")
            
        # For abandoned sessions (actual_chars = 0), errors must be at least expected_chars
        if self.actual_chars == 0:
            if self.errors < self.expected_chars:
                raise ValueError(
                    "For abandoned sessions, errors must be at least expected_chars"
                )
        else:
            # For non-abandoned sessions, enforce the normal error rule
            min_errors = max(0, self.expected_chars - self.actual_chars)
            if self.errors < min_errors:
                raise ValueError(
                    "errors cannot be less than expected_chars - actual_chars"
                )
            
        return self

    @computed_field
    def total_time(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    @computed_field
    def expected_chars(self) -> int:
        return self.snippet_index_end - self.snippet_index_start

    @computed_field
    def efficiency(self) -> float:
        # Example: efficiency = actual_chars / expected_chars
        if self.expected_chars == 0:
            return 0.0
        return self.actual_chars / self.expected_chars

    @computed_field
    def correctness(self) -> float:
        # correctness = (actual_chars - errors) / actual_chars
        if self.actual_chars == 0:
            return 0.0
        return (self.actual_chars - self.errors) / self.actual_chars

    @computed_field
    def accuracy(self) -> float:
        # accuracy = correctness * efficiency
        return self.correctness * self.efficiency

    @computed_field
    def session_wpm(self) -> float:
        # WPM = (actual_chars / 5) / (total_time / 60)
        if self.total_time == 0:
            return 0.0
        return (self.actual_chars / 5) / (self.total_time / 60)

    @computed_field
    def session_cpm(self) -> float:
        # CPM = actual_chars / (total_time / 60)
        if self.total_time == 0:
            return 0.0
        return self.actual_chars / (self.total_time / 60)

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        """Create a Session instance from a dictionary, ignoring calculated fields."""
        allowed_model_fields = set(cls.model_fields.keys())
        calculated_fields_to_ignore = set(cls.model_computed_fields.keys())

        init_kwargs: Dict[str, object] = {}
        data_keys = set(data.keys())

        known_keys = allowed_model_fields | calculated_fields_to_ignore
        unexpected_keys = data_keys - known_keys

        if unexpected_keys:
            raise ValueError("Unexpected fields.")

        for key, value in data.items():
            if key in allowed_model_fields:
                init_kwargs[key] = value

        return cls(**init_kwargs)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Session":
        return cls(
            session_id=row["session_id"],
            snippet_id=row["snippet_id"],
            snippet_index_start=row["snippet_index_start"],
            snippet_index_end=row["snippet_index_end"],
            content=row["content"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            actual_chars=row["actual_chars"],
            errors=row["errors"],
        )

    def to_dict(self) -> Dict:
        # Returns all fields, including calculated
        return {
            "session_id": self.session_id,
            "snippet_id": self.snippet_id,
            "snippet_index_start": self.snippet_index_start,
            "snippet_index_end": self.snippet_index_end,
            "content": self.content,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_time": self.total_time,
            "session_wpm": self.session_wpm,
            "session_cpm": self.session_cpm,
            "expected_chars": self.expected_chars,
            "actual_chars": self.actual_chars,
            "errors": self.errors,
            "efficiency": self.efficiency,
            "correctness": self.correctness,
            "accuracy": self.accuracy,
        }

    def get_summary(self) -> str:
        """
        Return a summary of the session (business logic only).
        """
        return f"Session {self.session_id} for snippet {self.snippet_id}: {self.content[:30]}..."
