from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ValidationInfo

# Constants from spec
MIN_NGRAM_SIZE = 2
MAX_NGRAM_SIZE = 20
SEQUENCE_SEPARATORS = {" ", "\t", "\n", "\r", "\0"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def has_sequence_separators(text: str) -> bool:
    return any(ch in text for ch in SEQUENCE_SEPARATORS)


class SpeedMode(str, Enum):
    RAW = "raw"
    NET = "net"


class NGramType(str, Enum):
    CLEAN = "clean"
    ERROR_LAST_CHAR = "error_last_char"


class Keystroke(BaseModel):
    timestamp: datetime
    text_index: int
    expected_char: str
    actual_char: str
    correctness: bool

    @field_validator("expected_char", "actual_char")
    @classmethod
    def _nfc_single_char(cls, v: str) -> str:
        v = nfc(v)
        if len(v) != 1:
            raise ValueError("expected single character after normalization")
        return v


class SpeedNGram(BaseModel):
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
        if self.ms_per_keystroke is None and self.duration_ms is not None and self.size:
            self.ms_per_keystroke = float(self.duration_ms) / float(self.size)
        return self


class ErrorNGram(BaseModel):
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

    @field_validator("expected_text", "actual_text")
    @classmethod
    def _validate_texts(cls, v: str) -> str:
        v = nfc(v)
        if has_sequence_separators(v):
            raise ValueError("n-gram text contains a sequence separator")
        return v

    @field_validator("actual_text")
    @classmethod
    def _validate_error_pattern(cls, v: str, info: ValidationInfo) -> str:
        exp = info.data.get("expected_text") if info and info.data else None
        if exp and len(exp) == len(v):
            if len(exp) >= MIN_NGRAM_SIZE:
                if exp[:-1] != v[:-1] or exp[-1] == v[-1]:
                    raise ValueError("error n-gram must differ only at last character")
        return v


# Helper utilities commonly used by manager and tests

def validate_ngram_size(size: int) -> bool:
    return MIN_NGRAM_SIZE <= size <= MAX_NGRAM_SIZE


def is_valid_ngram_text(text: str) -> bool:
    return (not has_sequence_separators(text)) and validate_ngram_size(len(text))
