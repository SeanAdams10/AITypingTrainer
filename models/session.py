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
        if self.actual_chars == 0:
            if self.errors < self.expected_chars:
                raise ValueError("For abandoned sessions, errors must be at least expected_chars")
        else:
            min_errors = max(0, self.expected_chars - self.actual_chars)
            if self.errors < min_errors:
                raise ValueError("errors cannot be less than expected_chars - actual_chars")
        return self

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

    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        def parse_dt(val: object) -> datetime.datetime:
            if isinstance(val, datetime.datetime):
                return val
            if isinstance(val, str):
                return datetime.datetime.fromisoformat(val)
            raise ValueError("Invalid datetime value")

        return cls(
            session_id=str(data["session_id"]),
            snippet_id=str(data["snippet_id"]),
            snippet_index_start=int(data["snippet_index_start"]),
            snippet_index_end=int(data["snippet_index_end"]),
            content=str(data["content"]),
            start_time=parse_dt(data["start_time"]),
            end_time=parse_dt(data["end_time"]),
            actual_chars=int(data["actual_chars"]),
            errors=int(data["errors"]),
        )

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> "Session":
        return cls(
            session_id=str(row["session_id"]),
            snippet_id=str(row["snippet_id"]),
            snippet_index_start=int(row["snippet_index_start"]),
            snippet_index_end=int(row["snippet_index_end"]),
            content=str(row["content"]),
            start_time=row["start_time"]
            if isinstance(row["start_time"], datetime.datetime)
            else datetime.datetime.fromisoformat(row["start_time"]),
            end_time=row["end_time"]
            if isinstance(row["end_time"], datetime.datetime)
            else datetime.datetime.fromisoformat(row["end_time"]),
            actual_chars=int(row["actual_chars"]),
            errors=int(row["errors"]),
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
        }

    def get_summary(self) -> str:
        """
        Return a summary of the session (business logic only).
        """
        return f"Session {self.session_id} for snippet {self.snippet_id}: {self.content[:30]}..."
