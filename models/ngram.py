"""Core n-gram models and utilities.

Provides Pydantic models for speed/error n-grams, enums, and helper
functions used across the application and tests.
"""

from __future__ import annotations

import unicodedata
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from models.keystroke import Keystroke  # Use unified Keystroke model

# Constants from spec
MIN_NGRAM_SIZE = 1
MAX_NGRAM_SIZE = 20
SEQUENCE_SEPARATORS = {" ", "\t", "\n", "\r", "\0"}


def nfc(s: str | None) -> str:
    """Return the NFC-normalized version of the input string.

    Accepts optional or non-string inputs, coercing them to strings prior to
    normalization so all downstream comparisons operate on NFC text.
    """
    if s is None:
        value = ""
    else:
        value = str(s)
    return unicodedata.normalize("NFC", value)


def has_sequence_separators(text: str) -> bool:
    """Return True if the text contains any sequence separator characters."""
    return any(ch in text for ch in SEQUENCE_SEPARATORS)


class SpeedMode(str, Enum):
    """Speed calculation mode for typing metrics."""

    RAW = "raw"
    NET = "net"


class NGramType(str, Enum):
    """Classification of n-gram record types."""

    CLEAN = "clean"
    ERROR_LAST_CHAR = "error_last_char"


class SpeedNGram(BaseModel):
    """Speed n-gram sample captured from typing sessions.

    Represents an n-gram with timing information used to compute typing
    speed metrics (e.g., ms per keystroke) in either raw or net modes.
    """

    id: uuid.UUID
    session_id: uuid.UUID
    size: int
    text: str
    duration_ms: float
    ms_per_keystroke: Optional[float] = None
    speed_mode: SpeedMode
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("size")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        if v < MIN_NGRAM_SIZE or v > MAX_NGRAM_SIZE:
            raise ValueError("invalid n-gram size")
        return v

    @field_validator("text")
    @classmethod
    def _validate_text(cls, v: str) -> str:
        v = nfc(v)
        if has_sequence_separators(v):
            raise ValueError("n-gram text contains a sequence separator")
        return v

    @model_validator(mode="after")
    def _compute_ms_per_keystroke(self) -> "SpeedNGram":
        if self.ms_per_keystroke is None and self.size:
            self.ms_per_keystroke = float(self.duration_ms) / float(self.size)
        return self


class ErrorNGram(BaseModel):
    """Error n-gram capturing a last-character mistake pattern.

    Ensures that the actual text differs from expected only at the last
    character when both are the same length and at least the minimum
    n-gram size.
    """

    id: uuid.UUID
    session_id: uuid.UUID
    size: int
    expected_text: str
    actual_text: str
    duration_ms: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("size")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        if v < MIN_NGRAM_SIZE or v > MAX_NGRAM_SIZE:
            raise ValueError("invalid n-gram size")
        return v

    @field_validator("expected_text")
    @classmethod
    def _validate_expected_text(cls, v: str) -> str:
        v = nfc(v)
        if has_sequence_separators(v):
            raise ValueError("n-gram text contains a sequence separator")
        return v

    @field_validator("actual_text", mode="before")
    @classmethod
    def _normalize_actual_text(cls, v: str) -> str:
        return nfc(v)

    @field_validator("actual_text")
    @classmethod
    def _validate_error_pattern(cls, v: str, info: ValidationInfo) -> str:
        if has_sequence_separators(v):
            raise ValueError("n-gram text contains a sequence separator")

        exp = info.data.get("expected_text") if info and info.data else None
        if exp and len(exp) == len(v):
            if len(exp) >= MIN_NGRAM_SIZE:
                if exp[:-1] != v[:-1] or exp[-1] == v[-1]:
                    raise ValueError("error n-gram must differ only at last character")
        return v


# Helper utilities commonly used by manager and tests


def validate_ngram_size(size: int) -> bool:
    """Validate that an n-gram size is within configured bounds."""
    return MIN_NGRAM_SIZE <= size <= MAX_NGRAM_SIZE


def is_valid_ngram_text(text: str) -> bool:
    """Return True if text is a valid n-gram candidate.

    Validity requires: no separator characters and length within
    [MIN_NGRAM_SIZE, MAX_NGRAM_SIZE].
    """
    return (not has_sequence_separators(text)) and validate_ngram_size(len(text))


# Re-export symbols for external imports
__all__ = [
    "SpeedMode",
    "NGramType",
    "SpeedNGram",
    "ErrorNGram",
    "validate_ngram_size",
    "is_valid_ngram_text",
    "Keystroke",
]
