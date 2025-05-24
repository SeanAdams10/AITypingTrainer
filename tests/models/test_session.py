import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union  # Replaced Any with List for specific case

import pytest
from pydantic import ValidationError
from pytest import approx

from models.session import Session


@pytest.fixture
def valid_session_dict_fixture() -> Dict[str, object]:
    now = datetime.now()
    return {
        "session_id": str(uuid.uuid4()),
        "snippet_id": 1,
        "snippet_index_start": 0,
        "snippet_index_end": 5,
        "content": "abcde",
        "start_time": now,
        "end_time": now + timedelta(seconds=60),
        "actual_chars": 5,
        "errors": 1,
    }


@pytest.mark.parametrize(
    "case_name, overrides, expected_results",
    [
        (
            "Default fixture values",
            {},
            {
                "expected_chars": 5, "total_time": 60.0,
                "efficiency": 1.0, "correctness": 0.8, "accuracy": 0.8,
                "session_cpm": 5.0, "session_wpm": 1.0,
            },
        ),
        (
            "Perfect score, short text",
            {"actual_chars": 5, "errors": 0},
            {
                "expected_chars": 5, "total_time": 60.0,
                "efficiency": 1.0, "correctness": 1.0, "accuracy": 1.0,
                "session_cpm": 5.0, "session_wpm": 1.0,
            },
        ),
        (
            "All errors",
            {"actual_chars": 5, "errors": 5},
            {
                "expected_chars": 5, "total_time": 60.0,
                "efficiency": 1.0, "correctness": 0.0, "accuracy": 0.0,
                "session_cpm": 5.0, "session_wpm": 1.0,
            },
        ),
        (
            "Zero actual_chars (abandoned)",
            {"actual_chars": 0, "errors": 0},
            {
                "expected_chars": 5, "total_time": 60.0,
                "efficiency": 0.0, "correctness": 0.0, "accuracy": 0.0,
                "session_cpm": 0.0, "session_wpm": 0.0,
            },
        ),
        (
            "Short duration, high WPM/CPM",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 12, 0, 1),
                "actual_chars": 5, "errors": 0,
            },
            {
                "expected_chars": 5, "total_time": 1.0,
                "efficiency": 1.0, "correctness": 1.0, "accuracy": 1.0,
                "session_cpm": 300.0, "session_wpm": 60.0,
            },
        ),
        (
            "Long duration, low WPM/CPM, incomplete",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 13, 0, 0),
                "snippet_index_start": 0, "snippet_index_end": 100,
                "actual_chars": 50, "errors": 5,
            },
            {
                "expected_chars": 100, "total_time": 3600.0,
                "efficiency": 0.5, "correctness": 0.9, "accuracy": 0.45,
                "session_cpm": 50.0 / 60.0, "session_wpm": (50.0 / 5) / 60.0,
            },
        ),
        (
            "Zero total_time (start_time == end_time)",
            {
                "start_time": datetime(2023, 1, 1, 12, 0, 0),
                "end_time": datetime(2023, 1, 1, 12, 0, 0),
                "actual_chars": 5, "errors": 0,
            },
            {
                "expected_chars": 5, "total_time": 0.0,
                "efficiency": 1.0, "correctness": 1.0, "accuracy": 1.0,
                "session_cpm": 0.0, "session_wpm": 0.0,
            },
        ),
        (
            "Incomplete typing (actual_chars < expected_chars)",
            {
                "snippet_index_start": 0, "snippet_index_end": 30,
                "actual_chars": 20, "errors": 2,
            },
            {
                "expected_chars": 30, "total_time": 60.0,
                "efficiency": 20.0/30.0,
                "correctness": 18.0/20.0,
                "accuracy": (18.0/20.0) * (20.0/30.0),
                "session_cpm": 20.0, "session_wpm": 4.0,
            },
        ),
        (
            "Snippet ID is None",
            {"snippet_id": None},
            {
                "expected_chars": 5, "total_time": 60.0,
                "efficiency": 1.0, "correctness": 0.8, "accuracy": 0.8,
                "session_cpm": 5.0, "session_wpm": 1.0,
            },
        ),
    ],
)
def test_session_creation_and_calculated_fields(
    case_name: str,
    overrides: Dict[str, object],
    expected_results: Dict[str, object],
    valid_session_dict_fixture: Dict[str, object],
) -> None:
    data = valid_session_dict_fixture.copy()
    data.update(overrides)

    s = Session(**data)

    if "session_id" in data:
        assert s.session_id == data["session_id"]
    if "snippet_id" in overrides:
        assert s.snippet_id == overrides["snippet_id"]
    elif "snippet_id" in data :
         assert s.snippet_id == data["snippet_id"]
    else:
        assert s.snippet_id is None

    assert s.expected_chars == approx(expected_results["expected_chars"]), (
        f"{case_name}: expected_chars"
    )
    assert s.total_time == approx(expected_results["total_time"]), f"{case_name}: total_time"
    assert s.efficiency == approx(expected_results["efficiency"]), f"{case_name}: efficiency"
    assert s.correctness == approx(expected_results["correctness"]), f"{case_name}: correctness"
    assert s.accuracy == approx(expected_results["accuracy"]), f"{case_name}: accuracy"
    assert s.session_cpm == approx(expected_results["session_cpm"]), f"{case_name}: session_cpm"
    assert s.session_wpm == approx(expected_results["session_wpm"]), f"{case_name}: session_wpm"


def test_session_from_dict_parses_iso(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    d = valid_session_dict_fixture.copy()
    if isinstance(d["start_time"], datetime) and isinstance(d["end_time"], datetime):
        d["start_time"] = d["start_time"].isoformat()
        d["end_time"] = d["end_time"].isoformat()
    else:
        pytest.fail("Fixture times are not datetime objects")
    s = Session.from_dict(d)
    assert isinstance(s.start_time, datetime)
    assert isinstance(s.end_time, datetime)


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "123", "", " "])
def test_session_id_validation_bad_values(
    bad_id: str, valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    data["session_id"] = bad_id
    with pytest.raises(ValidationError, match="session_id must be a valid UUID string"):
        Session(**data)

def test_session_id_none_value(valid_session_dict_fixture: Dict[str, object]) -> None:
    data = valid_session_dict_fixture.copy()
    data["session_id"] = None # type: ignore
    with pytest.raises(ValidationError, match="Input should be a valid string"):
        Session(**data)

def test_session_id_default_factory(valid_session_dict_fixture: Dict[str, object]) -> None:
    data = valid_session_dict_fixture.copy()
    del data["session_id"]
    s = Session(**data)
    assert isinstance(s.session_id, str)
    try:
        uuid.UUID(s.session_id)
    except ValueError:
        pytest.fail("Default session_id is not a valid UUID")


@pytest.mark.parametrize(
    "start_index, end_index, expected_error_message_part",
    [
        (5, 5, "snippet_index_start must be less than snippet_index_end"),
        (10, 5, "snippet_index_start must be less than snippet_index_end"),
        (-1, 5, "snippet_index_start must be >= 0"),
        (0, -1, "snippet_index_start must be less than snippet_index_end"),
        (-2, -1, "snippet_index_start must be >= 0"),
        (0, 0, "snippet_index_start must be less than snippet_index_end"),
        (0, 1, None),
        (2, 5, None),
        (0, 100, None),
    ]
)
def test_index_rule_violations(
    start_index: int,
    end_index: int,
    expected_error_message_part: Optional[str],
    valid_session_dict_fixture: Dict[str, object],
) -> None:
    data = valid_session_dict_fixture.copy()
    data["snippet_index_start"] = start_index
    data["snippet_index_end"] = end_index
    if expected_error_message_part:
        with pytest.raises(ValidationError, match=expected_error_message_part):
            Session(**data)
    else:
        try:
            Session(**data)
        except ValidationError as e:
            # Wrapped long f-string
            error_msg = (
                f"Should not raise ValidationError for valid indices "
                f"{start_index}, {end_index}: {e}"
            )
            pytest.fail(error_msg)


def test_start_time_after_end_time(valid_session_dict_fixture: Dict[str, object]) -> None:
    d = valid_session_dict_fixture.copy()
    d["start_time"] = datetime(2025, 5, 24, 13, 0, 0)
    d["end_time"] = datetime(2025, 5, 24, 12, 0, 0)
    with pytest.raises(ValidationError, match="start_time must be less than or equal to end_time"):
        Session(**d)


@pytest.mark.parametrize(
    "field, value, error_match",
    [
        ("session_id", 123, "Input should be a valid string"),
        ("start_time", "not a datetime", "Datetime must be ISO 8601 string"),
        ("end_time", 12345, "Datetime must be a datetime or ISO 8601 string"),
        ("actual_chars", "not an int", "Input should be a valid integer"),
        ("errors", "not an int", "Input should be a valid integer"),
        ("snippet_id", "not-an-int-or-none", "Input should be a valid integer"),
        ("snippet_index_start", "not an int", "Input should be a valid integer"),
        ("snippet_index_end", [1,2], "Input should be a valid integer"),
        ("content", 123, "Input should be a valid string"),
    ]
)
def test_type_enforcement_all_fields(
    field: str,
    value: Union[str, int, List[int]], # Replaced Any with Union of tested types
    error_match: str,
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    data[field] = value
    with pytest.raises(ValidationError, match=error_match):
        Session(**data)


def test_to_dict_and_from_dict_roundtrip(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    s = Session(**valid_session_dict_fixture)
    d = s.to_dict()
    s2 = Session.from_dict(d)
    assert s2 == s


@pytest.mark.parametrize(
    "time_input, is_valid, expected_exception, error_message_part",
    [
        (datetime.now(), True, None, None),
        (datetime.now().isoformat(), True, None, None),
        ("not-a-valid-iso-date", False, ValueError, "Datetime must be ISO 8601 string"),
        (12345, False, TypeError, "Datetime must be a datetime or ISO 8601 string"),
        ([2023,1,1], False, TypeError, "Datetime must be a datetime or ISO 8601 string"),
    ]
)
def test_datetime_validation(
    time_input: Union[datetime, str, int, list], # list is still used here for the test case
    is_valid: bool,
    expected_exception: Optional[type[Exception]],
    error_message_part: Optional[str],
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    data["start_time"] = time_input

    if not is_valid and expected_exception:
        with pytest.raises(ValidationError) as excinfo:
            Session(**data)
        assert error_message_part is not None
        assert error_message_part in str(excinfo.value)
    else:
        try:
            s = Session(**data)
            assert isinstance(s.start_time, datetime)
        except ValidationError as e:
            error_msg = (
                f"Should not raise ValidationError for valid datetime input "
                f"{time_input}: {e}"
            )
            pytest.fail(error_msg)

@pytest.mark.parametrize(
    "actual_chars_override, errors_override, should_raise, error_message",
    [
        ({"actual_chars": 3, "errors": 1}, True,
         "errors cannot be less than expected_chars - actual_chars"),
        ({"actual_chars": 3, "errors": 2}, False, None),
        ({"actual_chars": 3, "errors": 3}, False, None),
        ({"actual_chars": 5, "errors": -1}, True,
         "errors cannot be less than expected_chars - actual_chars"),
        ({"actual_chars": 5, "errors": 0}, False, None),
        ({"actual_chars": 6, "errors": -2}, True,
         "errors cannot be less than expected_chars - actual_chars"),
        ({"actual_chars": 6, "errors": 0}, False, None),
    ]
)
def test_business_rule_errors_vs_chars_difference(
    actual_chars_override: Dict[str, int],
    errors_override: Dict[str, int],
    should_raise: bool,
    error_message: Optional[str],
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    data.update(actual_chars_override)
    data.update(errors_override)

    if should_raise:
        assert error_message is not None
        with pytest.raises(ValidationError, match=error_message):
            Session(**data)
    else:
        try:
            Session(**data)
        except ValidationError as e:
            error_msg = (
                f"Should not raise for valid errors/actual_chars combination: "
                f"{data}, Error: {e}"
            )
            pytest.fail(error_msg)

def test_from_dict_with_extra_fields(valid_session_dict_fixture: Dict[str, object]) -> None:
    data = valid_session_dict_fixture.copy()
    data["extra_field_not_allowed"] = "some_value"
    data["another_one"] = 123
    with pytest.raises(
        ValueError,
        match=r"Extra fields not permitted: \\['extra_field_not_allowed', 'another_one'\\]"
    ):
        Session.from_dict(data)

def test_from_dict_ignores_calculated_fields(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    original_start_time = data["start_time"]
    original_end_time = data["end_time"]
    assert isinstance(original_start_time, datetime)
    assert isinstance(original_end_time, datetime)

    data["total_time"] = 12345.67
    data["session_wpm"] = 999.9

    s = Session.from_dict(data)

    expected_total_time = (original_end_time - original_start_time).total_seconds()
    assert s.total_time == approx(expected_total_time)
    assert s.total_time != approx(12345.67)

    expected_wpm = 0.0
    if expected_total_time > 0:
        expected_wpm = (s.actual_chars / 5) / (expected_total_time / 60)
    assert s.session_wpm == approx(expected_wpm)
    assert s.session_wpm != approx(999.9)


def test_from_dict_missing_required_fields(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    del data["content"]
    with pytest.raises(ValidationError, match="Field required"):
        Session.from_dict(data)

def test_to_dict_content_and_format(valid_session_dict_fixture: Dict[str, object]) -> None:
    s = Session(**valid_session_dict_fixture)
    d = s.to_dict()

    assert d["session_id"] == s.session_id
    assert d["snippet_id"] == s.snippet_id
    assert d["snippet_index_start"] == s.snippet_index_start
    assert d["snippet_index_end"] == s.snippet_index_end
    assert d["content"] == s.content
    assert d["start_time"] == s.start_time.isoformat()
    assert d["end_time"] == s.end_time.isoformat()
    assert d["actual_chars"] == s.actual_chars
    assert d["errors"] == s.errors

    assert d["total_time"] == approx(s.total_time)
    assert d["session_wpm"] == approx(s.session_wpm)
    assert d["session_cpm"] == approx(s.session_cpm)
    assert d["expected_chars"] == approx(s.expected_chars)
    assert d["efficiency"] == approx(s.efficiency)
    assert d["correctness"] == approx(s.correctness)
    assert d["accuracy"] == approx(s.accuracy)

    # 8 base + 7 computed + session_id = 16
    assert len(d.keys()) == 16


def test_get_summary_format_and_truncation(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    data["content"] = (
        "This is a very long content string that "
        "is definitely over thirty characters long."
    )
    data["session_id"] = "test-uuid-summary"
    data["snippet_id"] = 789
    s = Session(**data)

    summary = s.get_summary()
    expected_prefix = f"Session test-uuid-summary for snippet 789: {s.content[:30]}..."
    assert summary == expected_prefix

def test_get_summary_short_content(valid_session_dict_fixture: Dict[str, object]) -> None:
    data = valid_session_dict_fixture.copy()
    data["content"] = "Short"
    data["session_id"] = "test-uuid-short"
    data["snippet_id"] = 123
    s = Session(**data)

    summary = s.get_summary()
    expected_summary = "Session test-uuid-short for snippet 123: Short..."
    assert summary == expected_summary


def test_get_summary_with_none_snippet_id(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    data["snippet_id"] = None
    data["session_id"] = "test-uuid-none-snippet"
    s = Session(**data)
    summary = s.get_summary()
    expected_prefix = f"Session test-uuid-none-snippet for snippet None: {s.content[:30]}..."
    assert summary == expected_prefix

def test_extra_fields_forbidden_on_creation(
    valid_session_dict_fixture: Dict[str, object]
) -> None:
    data = valid_session_dict_fixture.copy()
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Session(**data, unexpected_field="some_value", another_extra="bla")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
