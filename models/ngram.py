"""
NGram Pydantic model for representing a single n-gram occurrence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class NGram(BaseModel):
    ngram_id: str = Field(..., description="UUID for this n-gram occurrence")
    text: str = Field(...)
    size: int = Field(...)
    start_time: datetime = Field(...)
    end_time: datetime = Field(...)
    is_clean: bool = Field(...)
    is_error: bool = Field(...)
    is_valid: bool = Field(...)

    model_config = {"extra": "forbid"}

    @property
    def total_time_ms(self) -> float:
        raw_time_ms = (self.end_time - self.start_time).total_seconds() * 1000.0
        # For ngrams of size 1, or invalid timestamps, return the raw time
        if self.size <= 1:
            return raw_time_ms
        # Adjust for missing time to first keystroke: (raw_time / (n-1)) * n
        return (raw_time_ms / (self.size - 1)) * self.size
        
    @property
    def ms_per_keystroke(self) -> float:
        """Average time in milliseconds per keystroke in this n-gram."""
        if self.size <= 0:
            return 0.0
        return self.total_time_ms / self.size

    def to_dict(self) -> Dict[str, Any]:
        d = self.dict()
        d["total_time_ms"] = self.total_time_ms
        d["ms_per_keystroke"] = self.ms_per_keystroke
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NGram":
        return cls(**d)
