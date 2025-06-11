from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from models.ngram import NGram


def test_ngram_creation_and_fields() -> None:
    start = datetime(2025, 6, 10, 12, 0, 0)
    end = start + timedelta(milliseconds=1500)
    ngram = NGram(
        ngram_id="123e4567-e89b-12d3-a456-426614174000",
        text="the",
        size=3,
        start_time=start,
        end_time=end,
        is_clean=True,
        is_error=False,
        is_valid=True,
    )
    assert ngram.text == "the"
    assert ngram.size == 3
    assert ngram.start_time == start
    assert ngram.end_time == end
    assert ngram.is_clean is True
    assert ngram.is_error is False
    assert ngram.is_valid is True
    assert abs(ngram.total_time_ms - 1500.0) < 1e-6


def test_ngram_to_dict_includes_total_time_ms() -> None:
    start = datetime(2025, 6, 10, 12, 0, 0)
    end = start + timedelta(milliseconds=500)
    ngram = NGram(
        ngram_id="123e4567-e89b-12d3-a456-426614174001",
        text="ab",
        size=2,
        start_time=start,
        end_time=end,
        is_clean=False,
        is_error=True,
        is_valid=True,
    )
    d = ngram.to_dict()
    assert d["text"] == "ab"
    assert d["size"] == 2
    assert d["start_time"] == start
    assert d["end_time"] == end
    assert d["is_clean"] is False
    assert d["is_error"] is True
    assert d["is_valid"] is True
    assert abs(d["total_time_ms"] - 500.0) < 1e-6


def test_ngram_from_dict_roundtrip() -> None:
    start = datetime(2025, 6, 10, 12, 0, 0)
    end = start + timedelta(milliseconds=250)
    d = {
        "ngram_id": "123e4567-e89b-12d3-a456-426614174002",
        "text": "xy",
        "size": 2,
        "start_time": start,
        "end_time": end,
        "is_clean": True,
        "is_error": False,
        "is_valid": True,
    }
    ngram = NGram.from_dict(d)
    assert ngram.text == "xy"
    assert ngram.size == 2
    assert ngram.start_time == start
    assert ngram.end_time == end
    assert ngram.is_clean is True
    assert ngram.is_error is False
    assert ngram.is_valid is True
    # to_dict should include total_time_ms
    d2 = ngram.to_dict()
    assert abs(d2["total_time_ms"] - 250.0) < 1e-6


def test_ngram_total_time_ms_zero() -> None:
    now = datetime.now()
    ngram = NGram(
        ngram_id="123e4567-e89b-12d3-a456-426614174003",
        text="zz",
        size=2,
        start_time=now,
        end_time=now,
        is_clean=False,
        is_error=False,
        is_valid=False,
    )
    assert ngram.total_time_ms == 0.0


def test_ngram_from_dict_missing_field() -> None:
    # Should raise error if required field is missing
    d = {
        "text": "ab",
        "size": 2,
        # missing start_time
        "end_time": datetime.now(),
        "is_clean": True,
        "is_error": False,
        "is_valid": True,
        "ngram_id": "123e4567-e89b-12d3-a456-426614174004",
    }
    with pytest.raises(ValidationError):
        NGram.from_dict(d)


def test_ngram_from_dict_extra_field() -> None:
    # Should raise error if extra field is present
    d = {
        "ngram_id": "123e4567-e89b-12d3-a456-426614174005",
        "text": "ab",
        "size": 2,
        "start_time": datetime.now(),
        "end_time": datetime.now(),
        "is_clean": True,
        "is_error": False,
        "is_valid": True,
        "extra_field": 123,
    }
    with pytest.raises(ValidationError):
        NGram.from_dict(d)
