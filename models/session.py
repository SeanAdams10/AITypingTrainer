"""
Session module for backward compatibility with older tests.

This module provides the Session class that was previously part of
the ngram_analyzer module but has been moved as part of the refactoring.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


class Session(BaseModel):
    """
    Pydantic model for a typing practice session, matching the practice_sessions table.
    All fields are validated and session_id is a UUID string.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    snippet_id: Optional[int] = None
    snippet_index_start: int
    snippet_index_end: int
    content: str
    start_time: datetime
    end_time: datetime
    actual_chars: int
    errors: int

    model_config = {
        "extra": "forbid"
    }

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
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except Exception as e:
                raise ValueError(f"Datetime must be ISO 8601 string: {v}") from e
        raise TypeError(f"Datetime must be a datetime or ISO 8601 string, got {type(v)}")

    @model_validator(mode="after")
    def check_business_rules(self) -> "Session":
        if self.snippet_index_start < 0:
            raise ValueError("snippet_index_start must be >= 0")
        if self.start_time > self.end_time:
            raise ValueError("start_time must be less than or equal to end_time")
        if self.snippet_index_start >= self.snippet_index_end:
            raise ValueError("snippet_index_start must be less than snippet_index_end")
        if self.errors < (self.expected_chars - self.actual_chars):
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
        # Example: correctness = (actual_chars - errors) / actual_chars
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
        # Accepts DB row dict, parses datetimes, ignores calculated fields
        allowed = {
            "session_id",
            "snippet_id",
            "snippet_index_start",
            "snippet_index_end",
            "content",
            "start_time",
            "end_time",
            "actual_chars",
            "errors",
        }
        # Remove all calculated fields if present
        data = {k: v for k, v in data.items() if k not in {
            "total_time", "session_wpm", "session_cpm", "expected_chars",
            "efficiency", "correctness", "accuracy"
        }}
        filtered = {k: v for k, v in data.items() if k in allowed}
        # If any extra fields, raise ValueError
        if len(filtered) != len(data):
            extra_keys = [k for k in data if k not in allowed]
            raise ValueError(f"Extra fields not permitted: {extra_keys}")
        return cls(**filtered)

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
        return (
            f"Session {self.session_id} for snippet {self.snippet_id}: "
            f"{self.content[:30]}..."
        )
