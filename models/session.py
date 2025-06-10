"""
Session module for backward compatibility with older tests.

This module provides the Session class that was previously part of
the ngram_analyzer module but has been moved as part of the refactoring.
"""

import datetime
import uuid
from typing import Dict, Mapping

from pydantic import BaseModel, Field, field_validator, model_validator


class Session(BaseModel):
    """
    Pydantic model for a typing practice session, matching the practice_sessions table.
    All fields are validated and session_id is a UUID string.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    snippet_id: str
    snippet_index_start: int
    snippet_index_end: int
    content: str
    start_time: datetime.datetime
    end_time: datetime.datetime
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

    @field_validator("snippet_id")
    @classmethod
    def validate_snippet_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except Exception as e:
            raise ValueError(f"snippet_id must be a valid UUID string: {v}") from e
        return v

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_datetime(cls, v: object) -> datetime.datetime:
        if isinstance(v, datetime.datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.datetime.fromisoformat(v)
            except (ValueError, TypeError) as e:
                raise ValueError("Datetime must be ISO 8601 string") from e
        raise TypeError("Datetime must be a datetime or ISO 8601 string")

    @model_validator(mode="after")
    def check_business_rules(self) -> "Session":
        if self.snippet_index_start < 0:
            raise ValueError("snippet_index_start must be >= 0")
        if self.snippet_index_start >= self.snippet_index_end:
            raise ValueError("snippet_index_start must be less than snippet_index_end")
        if self.start_time > self.end_time:
            raise ValueError("start_time must be less than or equal to end_time")
        if not self.content and self.actual_chars > 0:
            raise ValueError("content cannot be empty for non-abandoned sessions")

    @property
    def expected_chars(self) -> int:
        return self.snippet_index_end - self.snippet_index_start

    @property
    def total_time(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    @property
    def efficiency(self) -> float:
        if self.expected_chars == 0:
            return 0.0
        return self.actual_chars / self.expected_chars

    @property
    def correctness(self) -> float:
        if self.actual_chars == 0:
            return 0.0
        return (self.actual_chars - self.errors) / self.actual_chars

    @property
    def accuracy(self) -> float:
        return self.correctness * self.efficiency

    @property
    def session_wpm(self) -> float:
        if self.total_time == 0:
            return 0.0
        return (self.actual_chars / 5) / (self.total_time / 60)

    @property
    def session_cpm(self) -> float:
        if self.total_time == 0:
            return 0.0
        return self.actual_chars / (self.total_time / 60)

    @property
    def ms_per_keystroke(self) -> float:
        """
        Return the average milliseconds per keystroke for the session.
        Returns 0.0 if actual_chars is 0.
        """
        if self.actual_chars == 0:
            return 0.0
        return (self.total_time * 1000) / self.actual_chars

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        # Create a copy of the data so we don't modify the original
        data = data.copy()

        # Define expected fields
        expected_fields = {
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

        # Known calculated fields that should be ignored
        calculated_fields = {
            "total_time",
            "session_wpm",
            "session_cpm",
            "expected_chars",
            "efficiency",
            "correctness",
            "accuracy",
            "ms_per_keystroke",
        }

        # Check for unexpected fields (ignoring known calculated fields)
        unexpected_fields = set(data.keys()) - expected_fields - calculated_fields
        if unexpected_fields:
            raise ValueError("Unexpected fields.")

        def parse_dt(val: object) -> datetime.datetime:
            if isinstance(val, datetime.datetime):
                return val
            if isinstance(val, str):
                try:
                    return datetime.datetime.fromisoformat(val)
                except (ValueError, TypeError) as e:
                    raise ValueError("Datetime must be ISO 8601 string") from e
            raise TypeError("Datetime must be a datetime or ISO 8601 string")

        # Prepare parameters dict for creating the Session object
        params = {}

        # Only add keys if present in data
        if "session_id" in data:
            params["session_id"] = str(data["session_id"])
        if "snippet_id" in data:
            params["snippet_id"] = str(data["snippet_id"])
        if "snippet_index_start" in data:
            params["snippet_index_start"] = data["snippet_index_start"]
        if "snippet_index_end" in data:
            params["snippet_index_end"] = data["snippet_index_end"]
        if "content" in data:
            params["content"] = data["content"]
        if "start_time" in data:
            params["start_time"] = parse_dt(data["start_time"])
        if "end_time" in data:
            params["end_time"] = parse_dt(data["end_time"])
        if "actual_chars" in data:
            params["actual_chars"] = data["actual_chars"]
        if "errors" in data:
            params["errors"] = data["errors"]

        return cls(**params)

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> "Session":
        def parse_dt(val: object) -> datetime.datetime:
            if isinstance(val, datetime.datetime):
                return val
            if isinstance(val, str):
                try:
                    return datetime.datetime.fromisoformat(val)
                except (ValueError, TypeError) as e:
                    raise ValueError("Datetime must be ISO 8601 string") from e
            raise TypeError("Datetime must be a datetime or ISO 8601 string")

        def parse_str(val: object) -> str:
            if isinstance(val, str):
                return val
            raise TypeError("Value must be a string")

        def parse_int(val: object) -> int:
            if isinstance(val, int):
                return val
            if isinstance(val, str):
                try:
                    return int(val)
                except Exception as e:
                    raise TypeError(
                        "Value must be an integer or string representing an integer"
                    ) from e
            raise TypeError("Value must be an integer or string representing an integer")

        return cls(
            session_id=parse_str(row["session_id"]),
            snippet_id=parse_str(row["snippet_id"]),
            snippet_index_start=parse_int(row["snippet_index_start"]),
            snippet_index_end=parse_int(row["snippet_index_end"]),
            content=parse_str(row["content"]),
            start_time=parse_dt(row["start_time"]),
            end_time=parse_dt(row["end_time"]),
            actual_chars=parse_int(row["actual_chars"]),
            errors=parse_int(row["errors"]),
        )

    def to_dict(self) -> Dict:
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
            "ms_per_keystroke": self.ms_per_keystroke,
        }

    def get_summary(self) -> str:
        """
        Return a summary of the session (business logic only).
        """
        return f"Session {self.session_id} for snippet {self.snippet_id}: {self.content[:30]}..."
