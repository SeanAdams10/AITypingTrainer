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
        return (self.end_time - self.start_time).total_seconds() * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        d = self.dict()
        d["total_time_ms"] = self.total_time_ms
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NGram":
        return cls(**d)
