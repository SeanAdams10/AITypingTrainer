import uuid
from datetime import datetime, timedelta
from typing import Dict, Union

import pytest
from pydantic import ValidationError

from models.session import Session


# --- Fixtures ---
@pytest.fixture
def valid_session_dict() -> Dict[str, object]:
    now = datetime(2023, 1, 1, 12, 0, 0)
    return {
        "session_id": str(uuid.uuid4()),
        "snippet_id": str(uuid.uuid4()),
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "abcde",
        "start_time": now,
        "end_time": now + timedelta(seconds=60),
        "actual_chars": 5,
        "errors": 1,
    }


# --- Creation and Validation ---
def test_valid_session_creation(valid_session_dict: Dict[str, object]) -> None:
    s = Session(**valid_session_dict)
    assert s.session_id == valid_session_dict["session_id"]
    assert s.snippet_id == valid_session_dict["snippet_id"]
    assert s.snippet_index_start == 0
    assert s.snippet_index_end == 5
    assert s.content == "abcde"
    assert s.actual_chars == 5
    assert s.errors == 1


@pytest.mark.parametrize(
    "missing_field",
    [
        # 'session_id' removed because it has a default factory and is not required
        "snippet_id",
        "snippet_index_start",
        "snippet_index_end",
        "content",
        "start_time",
        "end_time",
        "actual_chars",
        "errors",
    ],
)
def test_missing_required_fields_raises_validation(
    valid_session_dict: Dict[str, object], missing_field: str
) -> None:
    data = valid_session_dict.copy()
    data.pop(missing_field)
    with pytest.raises(ValidationError):
        Session(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", "not-a-uuid"),
        ("snippet_id", "not-a-uuid"),
        ("snippet_index_start", -1),
        ("snippet_index_end", 0),
        ("start_time", "not-a-date"),
        ("end_time", 12345),
        ("actual_chars", "not-an-int"),
        ("errors", "not-an-int"),
    ],
)
def test_invalid_field_values_raise(
    valid_session_dict: Dict[str, object], field: str, value: Union[str, int]
) -> None:
    data = valid_session_dict.copy()
    data[field] = value
    with pytest.raises((ValidationError, ValueError, TypeError)):
        Session(**data)


@pytest.mark.parametrize(
    "start,end,expect_error",
    [
        (0, 0, True),
        (5, 5, True),
        (10, 5, True),
        (-1, 5, True),
        (0, 1, False),
        (2, 5, False),
    ],
)
def test_index_business_rules(
    valid_session_dict: Dict[str, object], start: int, end: int, expect_error: bool
) -> None:
    data = valid_session_dict.copy()
    data["snippet_index_start"] = start
    data["snippet_index_end"] = end
    if expect_error:
        with pytest.raises((ValidationError, ValueError)):
            Session(**data)
    else:
        s = Session(**data)
        assert s.snippet_index_start == start
        assert s.snippet_index_end == end


def test_start_time_after_end_time_raises(valid_session_dict: Dict[str, object]) -> None:
    data = valid_session_dict.copy()
    data["start_time"] = data["end_time"] + timedelta(seconds=1)
    with pytest.raises(ValueError):
        Session(**data)


# --- Computed Properties ---
def test_computed_properties(valid_session_dict: Dict[str, object]) -> None:
    s = Session(**valid_session_dict)
    assert s.expected_chars == 5
    assert s.total_time == 60.0
    assert s.efficiency == 1.0
    assert s.correctness == 0.8
    assert s.accuracy == 0.8
    assert s.session_cpm == 5.0
    assert s.session_wpm == 1.0
    # ms_per_keystroke now uses expected_chars
    assert s.ms_per_keystroke == 12000.0


@pytest.mark.parametrize(
    "actual_chars,errors,expected_correctness,expected_accuracy",
    [
        (5, 0, 1.0, 1.0),
        (5, 5, 0.0, 0.0),
        (0, 0, 0.0, 0.0),
    ],
)
def test_correctness_and_accuracy(
    valid_session_dict: Dict[str, object],
    actual_chars: int,
    errors: int,
    expected_correctness: float,
    expected_accuracy: float,
) -> None:
    data = valid_session_dict.copy()
    data["actual_chars"] = actual_chars
    data["errors"] = errors
    s = Session(**data)
    assert s.correctness == expected_correctness
    assert s.accuracy == expected_accuracy


@pytest.mark.parametrize(
    "start_time,end_time,expected_wpm,expected_cpm",
    [
        (datetime(2023, 1, 1, 12, 0, 0), datetime(2023, 1, 1, 12, 0, 0), 0.0, 0.0),
        (datetime(2023, 1, 1, 12, 0, 0), datetime(2023, 1, 1, 12, 1, 0), 1.0, 5.0),
    ],
)
def test_wpm_cpm_zero_and_normal(
    valid_session_dict: Dict[str, object],
    start_time: datetime,
    end_time: datetime,
    expected_wpm: float,
    expected_cpm: float,
) -> None:
    data = valid_session_dict.copy()
    data["start_time"] = start_time
    data["end_time"] = end_time
    s = Session(**data)
    assert s.session_wpm == expected_wpm
    assert s.session_cpm == expected_cpm


# --- Dict/Row Roundtrip ---
def test_to_dict_and_from_dict(valid_session_dict: Dict[str, object]) -> None:
    s = Session(**valid_session_dict)
    d = s.to_dict()
    s2 = Session.from_dict(d)
    assert s2.session_id == s.session_id
    assert s2.snippet_id == s.snippet_id
    assert s2.content == s.content
    assert s2.start_time == s.start_time
    assert s2.end_time == s.end_time
    assert s2.actual_chars == s.actual_chars
    assert s2.errors == s.errors


# --- Extra/Calculated Fields ---
def test_from_dict_ignores_calculated_fields(valid_session_dict: Dict[str, object]) -> None:
    d = valid_session_dict.copy()
    d["total_time"] = 123
    d["session_wpm"] = 1.23
    d["session_cpm"] = 4.56
    d["expected_chars"] = 5
    d["efficiency"] = 1.0
    d["correctness"] = 1.0
    d["accuracy"] = 1.0
    d["ms_per_keystroke"] = 1000.0
    s = Session.from_dict(d)
    assert s.session_id == d["session_id"]
    assert s.snippet_id == d["snippet_id"]


def test_from_dict_with_extra_fields_raises(valid_session_dict: Dict[str, object]) -> None:
    d = valid_session_dict.copy()
    d["extra_field"] = 123
    with pytest.raises(ValueError):
        Session.from_dict(d)


# --- Summary ---
def test_get_summary_truncates_content(valid_session_dict: Dict[str, object]) -> None:
    s = Session(**valid_session_dict)
    summary = s.get_summary()
    assert s.session_id in summary
    assert s.snippet_id in summary
    assert s.content[:10] in summary


# --- Forbidden extra fields on creation ---
def test_extra_fields_forbidden_on_creation(valid_session_dict: Dict[str, object]) -> None:
    d = valid_session_dict.copy()
    d["foo"] = "bar"
    with pytest.raises(ValidationError):
        Session(**d)


# --- ms_per_keystroke edge case ---
def test_ms_per_keystroke_zero_chars(valid_session_dict: Dict[str, object]) -> None:
    d = valid_session_dict.copy()
    d["start_time"] = d["end_time"]  # total_time = 0, expected_chars > 0
    s = Session(**d)
    assert s.ms_per_keystroke == 0.0


# --- UUID default factory ---
def test_session_id_default_factory(valid_session_dict: Dict[str, object]) -> None:
    d = valid_session_dict.copy()
    d.pop("session_id")
    s = Session(**d)
    uuid.UUID(s.session_id)  # Should not raise


# --- Content required for non-abandoned sessions ---
def test_content_required_if_actual_chars(valid_session_dict: Dict[str, object]) -> None:
    d = valid_session_dict.copy()
    d["content"] = ""
    with pytest.raises(ValueError):
        Session(**d)
