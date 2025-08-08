"""
New N-Gram Data Models for the updated specification.

This module provides the SpeedNGram and ErrorNGram models along with
supporting enums and constants as defined in the ngram.md specification.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

# Constants from specification
MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 20

# Sequence separators that break n-gram sequences
SEQUENCE_SEPARATORS = [" ", "\n", "\t", "\0"]  # space, newline, tab, null character


class SpeedMode(str, Enum):
    """Speed calculation modes for n-gram analysis."""

    RAW = "raw"  # Uses all keystrokes including corrections
    NET = "net"  # Filters to keep only final keystrokes after corrections


class NGramClassifier(str, Enum):
    """N-gram classification types."""

    CLEAN = "CLEAN"  # All keystrokes correct, no separators, positive duration
    ERROR = "ERROR"  # Only last keystroke incorrect, no separators, positive duration
    IGNORED = "IGNORED"  # Errors in non-last positions, separators, or invalid duration


class SpeedNGram(BaseModel):
    """
    Model for clean n-grams used in speed analysis.

    Represents n-grams where all keystrokes match expected characters exactly.
    Stored in the session_ngram_speed table.
    """

    id: UUID = Field(..., description="Unique identifier for this speed n-gram")
    session_id: UUID = Field(..., description="ID of the typing session this n-gram belongs to")
    size: int = Field(..., ge=MIN_NGRAM_SIZE, le=MAX_NGRAM_SIZE, description="Length of the n-gram")
    text: str = Field(
        ...,
        min_length=MIN_NGRAM_SIZE,
        max_length=MAX_NGRAM_SIZE,
        description="The n-gram text (expected characters)",
    )
    duration_ms: float = Field(
        ..., gt=0, description="Total time to type this n-gram in milliseconds"
    )
    ms_per_keystroke: float = Field(..., ge=0, description="Average milliseconds per keystroke")
    speed_mode: SpeedMode = Field(..., description="Speed calculation mode used (raw or net)")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when this record was created"
    )

    model_config = {"extra": "forbid"}

    @validator("text")
    def validate_no_sequence_separators(cls, v: str) -> str:
        """Ensure n-gram text contains no sequence separators."""
        for separator in SEQUENCE_SEPARATORS:
            if separator in v:
                raise ValueError(f"N-gram text cannot contain sequence separator: '{separator}'")
        return v

    @validator("ms_per_keystroke", always=True)
    def calculate_ms_per_keystroke(cls, v: float, values: Dict[str, Any]) -> float:
        """Calculate ms_per_keystroke from duration_ms and size if not provided."""
        if v is None or v == 0:
            duration_ms = values.get("duration_ms", 0)
            size = values.get("size", 1)
            if duration_ms > 0 and size > 0:
                return duration_ms / size
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.dict()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpeedNGram":
        """Create instance from dictionary."""
        return cls(**d)


class ErrorNGram(BaseModel):
    """
    Model for error n-grams used in error analysis.

    Represents n-grams where only the final keystroke is incorrect.
    Stored in the session_ngram_errors table.
    """

    id: UUID = Field(..., description="Unique identifier for this error n-gram")
    session_id: UUID = Field(..., description="ID of the typing session this n-gram belongs to")
    size: int = Field(..., ge=MIN_NGRAM_SIZE, le=MAX_NGRAM_SIZE, description="Length of the n-gram")
    expected_text: str = Field(
        ...,
        min_length=MIN_NGRAM_SIZE,
        max_length=MAX_NGRAM_SIZE,
        description="The expected n-gram text",
    )
    actual_text: str = Field(
        ...,
        min_length=MIN_NGRAM_SIZE,
        max_length=MAX_NGRAM_SIZE,
        description="The actual typed n-gram text",
    )
    duration_ms: float = Field(
        ..., gt=0, description="Total time to type this n-gram in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when this record was created"
    )

    model_config = {"extra": "forbid"}

    @validator("expected_text", "actual_text")
    def validate_no_sequence_separators(cls, v: str) -> str:
        """Ensure n-gram text contains no sequence separators."""
        for separator in SEQUENCE_SEPARATORS:
            if separator in v:
                raise ValueError(f"N-gram text cannot contain sequence separator: '{separator}'")
        return v

    @validator("actual_text")
    def validate_error_pattern(cls, v: str, values: Dict[str, Any]) -> str:
        """Ensure only the last character differs from expected."""
        expected = values.get("expected_text", "")
        if expected and len(v) == len(expected):
            # All characters except the last must match
            if v[:-1] != expected[:-1]:
                raise ValueError("Error n-grams must have errors only in the last position")
            # Last character must be different
            if v[-1] == expected[-1]:
                raise ValueError("Error n-grams must have an error in the last position")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.dict()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ErrorNGram":
        """Create instance from dictionary."""
        return cls(**d)


class Keystroke(BaseModel):
    """
    Model representing a single keystroke in a typing session.

    This is used by the NGramManager for processing keystrokes into n-grams.
    """

    id: Optional[UUID] = Field(None, description="Unique identifier for this keystroke")
    session_id: UUID = Field(..., description="ID of the typing session")
    timestamp: datetime = Field(..., description="When this keystroke occurred")
    text_index: int = Field(..., ge=0, description="Position in the expected text")
    expected_char: str = Field(..., max_length=1, description="Expected character at this position")
    actual_char: str = Field(..., max_length=1, description="Actually typed character")
    is_correct: bool = Field(
        ..., description="Whether the keystroke matches the expected character"
    )

    model_config = {"extra": "forbid"}

    @validator("is_correct", always=True)
    def validate_correctness(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Ensure is_correct matches the comparison of expected vs actual."""
        expected = values.get("expected_char", "")
        actual = values.get("actual_char", "")
        if expected and actual:
            calculated_correct = expected == actual
            if v != calculated_correct:
                return calculated_correct  # Override with calculated value
        return v

    @property
    def is_error(self) -> bool:
        """Check if this keystroke is an error."""
        return not self.is_correct

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self.dict()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Keystroke":
        """Create instance from dictionary."""
        return cls(**d)


def validate_ngram_size(size: int) -> bool:
    """Validate that an n-gram size is within acceptable bounds."""
    return MIN_NGRAM_SIZE <= size <= MAX_NGRAM_SIZE


def has_sequence_separators(text: str) -> bool:
    """Check if text contains any sequence separators."""
    return any(separator in text for separator in SEQUENCE_SEPARATORS)


def is_valid_ngram_text(text: str) -> bool:
    """Validate that n-gram text is acceptable (no separators, correct length)."""
    if not text:
        return False
    if len(text) < MIN_NGRAM_SIZE or len(text) > MAX_NGRAM_SIZE:
        return False
    return not has_sequence_separators(text)
