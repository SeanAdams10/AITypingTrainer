"""
Comprehensive tests for the Keystroke Pydantic model.
Tests cover creation, serialization, validation, and edge cases.
Based on Keystroke.md specification requirements.
"""

import datetime
import uuid
from typing import Any, Dict
import pytest
from unittest.mock import Mock, patch

from models.keystroke import Keystroke


@pytest.fixture
def valid_keystroke_data() -> Dict[str, Any]:
    """Fixture providing valid keystroke data for testing."""
    return {
        "session_id": str(uuid.uuid4()),
        "keystroke_id": str(uuid.uuid4()),  # Use UUID string
        "keystroke_time": datetime.datetime.now(),
        "keystroke_char": "a",
        "expected_char": "a",
        "is_error": False,
        "time_since_previous": 100,
    }


@pytest.fixture
def sample_keystroke(valid_keystroke_data: Dict[str, Any]) -> Keystroke:
    """Fixture providing a sample Keystroke instance."""
    return Keystroke(**valid_keystroke_data)


class TestKeystrokeCreation:
    """Test Keystroke model creation and validation."""

    def test_keystroke_creation_with_valid_data(self, valid_keystroke_data: Dict[str, Any]) -> None:
        """Test creating a Keystroke with valid data."""
        keystroke = Keystroke(**valid_keystroke_data)
        assert keystroke.session_id == valid_keystroke_data["session_id"]
        assert keystroke.keystroke_char == valid_keystroke_data["keystroke_char"]
        assert keystroke.expected_char == valid_keystroke_data["expected_char"]
        assert keystroke.is_error == valid_keystroke_data["is_error"]
        assert keystroke.time_since_previous == valid_keystroke_data["time_since_previous"]

    def test_keystroke_creation_with_defaults(self) -> None:
        """Test creating a Keystroke with default values."""
        keystroke = Keystroke()
        assert keystroke.session_id is None
        assert keystroke.keystroke_id is None
        assert isinstance(keystroke.keystroke_time, datetime.datetime)
        assert keystroke.keystroke_char == ""
        assert keystroke.expected_char == ""
        assert keystroke.is_error is False
        assert keystroke.time_since_previous is None

    def test_keystroke_id_auto_generation(self) -> None:
        """Test that keystroke_id is None by default (no auto-generation)."""
        keystroke = Keystroke()
        assert keystroke.keystroke_id is None

    def test_keystroke_time_auto_generation(self) -> None:
        """Test that keystroke_time is auto-generated if not provided."""
        before = datetime.datetime.now()
        keystroke = Keystroke()
        after = datetime.datetime.now()
        assert before <= keystroke.keystroke_time <= after

    def test_keystroke_with_none_session_id(self) -> None:
        """Test creating keystroke with None session_id."""
        keystroke = Keystroke(session_id=None)
        assert keystroke.session_id is None

    def test_keystroke_with_error_true(self) -> None:
        """Test creating keystroke with is_error set to True."""
        keystroke = Keystroke(is_error=True)
        assert keystroke.is_error is True

    def test_keystroke_with_empty_strings(self) -> None:
        """Test creating keystroke with empty character strings."""
        keystroke = Keystroke(keystroke_char="", expected_char="")
        assert keystroke.keystroke_char == ""
        assert keystroke.expected_char == ""


class TestKeystrokeFromDict:
    """Test Keystroke.from_dict method for various data types and edge cases."""

    def test_from_dict_with_valid_data(self, valid_keystroke_data: Dict[str, Any]) -> None:
        """Test from_dict with completely valid data."""
        keystroke = Keystroke.from_dict(valid_keystroke_data)
        assert keystroke.session_id == valid_keystroke_data["session_id"]
        assert keystroke.keystroke_char == valid_keystroke_data["keystroke_char"]
        assert keystroke.expected_char == valid_keystroke_data["expected_char"]
        assert keystroke.is_error == valid_keystroke_data["is_error"]

    def test_from_dict_with_minimal_data(self) -> None:
        """Test from_dict with minimal required data."""
        data = {"keystroke_char": "b", "expected_char": "b"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.keystroke_char == "b"
        assert keystroke.expected_char == "b"
        assert isinstance(keystroke.keystroke_time, datetime.datetime)

    def test_from_dict_datetime_iso_string(self) -> None:
        """Test from_dict with ISO format datetime string."""
        data = {
            "keystroke_time": "2023-01-01T12:00:00",
            "keystroke_char": "x",
            "expected_char": "x",
        }
        keystroke = Keystroke.from_dict(data)
        assert isinstance(keystroke.keystroke_time, datetime.datetime)
        assert keystroke.keystroke_time.year == 2023

    def test_from_dict_datetime_iso_string_with_z(self) -> None:
        """Test from_dict with ISO format datetime string with Z suffix."""
        data = {
            "keystroke_time": "2023-01-01T12:00:00Z",
            "keystroke_char": "y",
            "expected_char": "y",
        }
        keystroke = Keystroke.from_dict(data)
        assert isinstance(keystroke.keystroke_time, datetime.datetime)

    def test_from_dict_invalid_datetime_string(self) -> None:
        """Test from_dict with invalid datetime string falls back to current time."""
        data = {"keystroke_time": "not-a-valid-date", "keystroke_char": "z", "expected_char": "z"}
        before = datetime.datetime.now()
        keystroke = Keystroke.from_dict(data)
        after = datetime.datetime.now()
        assert before <= keystroke.keystroke_time <= after

    def test_from_dict_non_datetime_object(self) -> None:
        """Test from_dict with non-datetime object falls back to current time."""
        data = {"keystroke_time": 12345, "keystroke_char": "w", "expected_char": "w"}
        before = datetime.datetime.now()
        keystroke = Keystroke.from_dict(data)
        after = datetime.datetime.now()
        assert before <= keystroke.keystroke_time <= after

    @pytest.mark.parametrize(
        "error_value,expected",
        [
            ("true", True),
            ("True", True),
            ("1", True),
            ("t", True),
            ("y", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("f", False),
            ("n", False),
            ("no", False),
            ("", False),
            ("other", False),
        ],
    )
    def test_from_dict_is_error_string_values(self, error_value: str, expected: bool) -> None:
        """Test from_dict with various string values for is_error."""
        data = {"is_error": error_value, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.is_error == expected

    @pytest.mark.parametrize(
        "error_value,expected",
        [
            (0, False),
            (1, True),
            (-1, True),
            (42, True),
        ],
    )
    def test_from_dict_is_error_integer_values(self, error_value: int, expected: bool) -> None:
        """Test from_dict with integer values for is_error."""
        data = {"is_error": error_value, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.is_error == expected

    def test_from_dict_is_error_none_value(self) -> None:
        """Test from_dict with None value for is_error."""
        data = {"is_error": None, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.is_error is False

    def test_from_dict_session_id_conversion(self) -> None:
        """Test from_dict converts session_id to string."""
        data = {"session_id": 12345, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.session_id == "12345"

    def test_from_dict_session_id_invalid_conversion(self) -> None:
        """Test from_dict handles invalid session_id conversion gracefully."""
        data = {"session_id": {"invalid": "object"}, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.session_id is None

    def test_from_dict_keystroke_id_conversion(self) -> None:
        """Test from_dict converts keystroke_id to string."""
        data = {"keystroke_id": 67890, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.keystroke_id == "67890"

    def test_from_dict_keystroke_id_invalid_conversion(self) -> None:
        """Test from_dict handles invalid keystroke_id conversion gracefully."""
        data = {"keystroke_id": {"invalid": "object"}, "keystroke_char": "a", "expected_char": "a"}
        keystroke = Keystroke.from_dict(data)
        # Should fallback to a UUID string
        assert isinstance(keystroke.keystroke_id, str)
        assert len(keystroke.keystroke_id) >= 8  # UUID string

    def test_from_dict_empty_dict(self) -> None:
        """Test from_dict with empty dictionary."""
        data = {}
        keystroke = Keystroke.from_dict(data)
        assert keystroke.keystroke_char == ""
        assert keystroke.expected_char == ""
        assert keystroke.is_error is False


class TestKeystrokeToDict:
    """Test Keystroke.to_dict method."""

    def test_to_dict_complete_data(self, sample_keystroke: Keystroke) -> None:
        """Test to_dict with complete keystroke data."""
        result = sample_keystroke.to_dict()

        assert "session_id" in result
        assert "keystroke_id" in result
        assert "keystroke_time" in result
        assert "keystroke_char" in result
        assert "expected_char" in result
        assert "is_error" in result
        assert "time_since_previous" in result

        assert result["session_id"] == sample_keystroke.session_id
        assert result["keystroke_char"] == sample_keystroke.keystroke_char
        assert result["expected_char"] == sample_keystroke.expected_char
        assert result["is_error"] == sample_keystroke.is_error

    def test_to_dict_datetime_serialization(self, sample_keystroke: Keystroke) -> None:
        """Test to_dict properly serializes datetime to ISO format."""
        result = sample_keystroke.to_dict()
        assert isinstance(result["keystroke_time"], str)
        # Should be able to parse it back
        datetime.datetime.fromisoformat(result["keystroke_time"])

    def test_to_dict_with_none_values(self) -> None:
        """Test to_dict with None values."""
        keystroke = Keystroke(session_id=None, keystroke_id=None, time_since_previous=None)
        result = keystroke.to_dict()
        assert result["session_id"] is None
        assert result["keystroke_id"] is None
        assert result["time_since_previous"] is None

    def test_to_dict_roundtrip(self, sample_keystroke: Keystroke) -> None:
        """Test that to_dict -> from_dict preserves data."""
        dict_data = sample_keystroke.to_dict()
        new_keystroke = Keystroke.from_dict(dict_data)

        assert new_keystroke.session_id == sample_keystroke.session_id
        assert new_keystroke.keystroke_char == sample_keystroke.keystroke_char
        assert new_keystroke.expected_char == sample_keystroke.expected_char
        assert new_keystroke.is_error == sample_keystroke.is_error
        assert new_keystroke.time_since_previous == sample_keystroke.time_since_previous


class TestKeystrokeClassMethods:
    """Test Keystroke class methods for database operations."""

    @patch("models.keystroke.DatabaseManager")
    def test_get_for_session_success(self, mock_db_class: Mock) -> None:
        """Test get_for_session returns keystrokes for a session."""
        # Setup mock
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_row = {
            "session_id": "test-session",
            "keystroke_id": "test-id",
            "keystroke_time": "2023-01-01T12:00:00",
            "keystroke_char": "a",
            "expected_char": "a",
            "is_error": 0,
            "time_since_previous": 100,
        }
        mock_db.fetchall.return_value = [mock_row]

        result = Keystroke.get_for_session("test-session")

        assert len(result) == 1
        assert isinstance(result[0], Keystroke)
        assert result[0].session_id == "test-session"
        assert result[0].keystroke_char == "a"
        mock_db.fetchall.assert_called_once()

    @patch("models.keystroke.DatabaseManager")
    def test_get_for_session_empty_result(self, mock_db_class: Mock) -> None:
        """Test get_for_session returns empty list when no keystrokes found."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.fetchall.return_value = []

        result = Keystroke.get_for_session("nonexistent-session")

        assert result == []
        mock_db.fetchall.assert_called_once()

    @patch("models.keystroke.DatabaseManager")
    def test_get_for_session_none_result(self, mock_db_class: Mock) -> None:
        """Test get_for_session handles None result from database."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.fetchall.return_value = None

        result = Keystroke.get_for_session("test-session")

        assert result == []

    @patch("models.keystroke.DatabaseManager")
    def test_get_errors_for_session_success(self, mock_db_class: Mock) -> None:
        """Test get_errors_for_session returns only error keystrokes."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_row = {
            "session_id": "test-session",
            "keystroke_id": "test-id",
            "keystroke_time": "2023-01-01T12:00:00",
            "keystroke_char": "x",
            "expected_char": "a",
            "is_error": 1,
            "time_since_previous": 150,
        }
        mock_db.fetchall.return_value = [mock_row]

        result = Keystroke.get_errors_for_session("test-session")

        assert len(result) == 1
        assert isinstance(result[0], Keystroke)
        assert result[0].is_error is True
        assert result[0].keystroke_char == "x"
        mock_db.fetchall.assert_called_once()

    @patch("models.keystroke.DatabaseManager")
    def test_get_errors_for_session_empty_result(self, mock_db_class: Mock) -> None:
        """Test get_errors_for_session returns empty list when no errors found."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.fetchall.return_value = []

        result = Keystroke.get_errors_for_session("perfect-session")

        assert result == []

    @patch("models.keystroke.DatabaseManager")
    def test_delete_all_keystrokes_success(self, mock_db_class: Mock) -> None:
        """Test delete_all_keystrokes successfully deletes all keystrokes."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        result = Keystroke.delete_all_keystrokes(mock_db)

        assert result is True
        mock_db.execute.assert_called_once_with("DELETE FROM session_keystrokes", ())

    @patch("models.keystroke.DatabaseManager")
    def test_delete_all_keystrokes_exception(self, mock_db_class: Mock) -> None:
        """Test delete_all_keystrokes handles database exceptions."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.execute.side_effect = Exception("Database error")

        result = Keystroke.delete_all_keystrokes(mock_db)

        assert result is False
        mock_db.execute.assert_called_once()


class TestKeystrokeEdgeCases:
    """Test edge cases and error conditions."""

    def test_keystroke_with_unicode_characters(self) -> None:
        """Test keystroke with unicode characters."""
        keystroke = Keystroke(keystroke_char="ñ", expected_char="ñ")
        assert keystroke.keystroke_char == "ñ"
        assert keystroke.expected_char == "ñ"

    def test_keystroke_with_special_characters(self) -> None:
        """Test keystroke with special characters."""
        special_chars = ["\n", "\t", " ", "!", "@", "#", "$", "%"]
        for char in special_chars:
            keystroke = Keystroke(keystroke_char=char, expected_char=char)
            assert keystroke.keystroke_char == char
            assert keystroke.expected_char == char

    def test_keystroke_with_very_long_strings(self) -> None:
        """Test keystroke with very long character strings."""
        long_string = "a" * 1000
        keystroke = Keystroke(keystroke_char=long_string, expected_char=long_string)
        assert keystroke.keystroke_char == long_string
        assert keystroke.expected_char == long_string

    def test_keystroke_with_negative_time_since_previous(self) -> None:
        """Test keystroke with negative time_since_previous."""
        keystroke = Keystroke(time_since_previous=-100)
        assert keystroke.time_since_previous == -100

    def test_keystroke_with_zero_time_since_previous(self) -> None:
        """Test keystroke with zero time_since_previous."""
        keystroke = Keystroke(time_since_previous=0)
        assert keystroke.time_since_previous == 0

    def test_keystroke_with_very_large_time_since_previous(self) -> None:
        """Test keystroke with very large time_since_previous value."""
        large_time = 999999999
        keystroke = Keystroke(time_since_previous=large_time)
        assert keystroke.time_since_previous == large_time

    def test_from_dict_with_extra_fields(self) -> None:
        """Test from_dict ignores extra fields not in the model."""
        data = {
            "keystroke_char": "a",
            "expected_char": "a",
            "extra_field": "should_be_ignored",
            "another_field": 12345,
        }
        keystroke = Keystroke.from_dict(data)
        assert keystroke.keystroke_char == "a"
        assert keystroke.expected_char == "a"
        # Extra fields should not be present
        assert not hasattr(keystroke, "extra_field")
        assert not hasattr(keystroke, "another_field")


class TestKeystrokeIntegration:
    """Integration tests with actual database operations."""

    def test_full_workflow_create_save_retrieve(self) -> None:
        """Test full workflow: create keystroke, convert to dict, create from dict."""
        # Create original keystroke
        original = Keystroke(
            session_id=str(uuid.uuid4()),
            keystroke_char="t",
            expected_char="t",
            is_error=False,
            time_since_previous=200,
        )

        # Convert to dict (simulating serialization)
        dict_data = original.to_dict()

        # Create new keystroke from dict (simulating deserialization)
        restored = Keystroke.from_dict(dict_data)

        # Verify data integrity
        assert restored.session_id == original.session_id
        assert restored.keystroke_char == original.keystroke_char
        assert restored.expected_char == original.expected_char
        assert restored.is_error == original.is_error
        assert restored.time_since_previous == original.time_since_previous

    def test_model_consistency_with_specification(self) -> None:
        """Test that the model matches the specification requirements."""
        keystroke = Keystroke()

        # Verify required fields exist
        assert hasattr(keystroke, "session_id")
        assert hasattr(keystroke, "keystroke_id")
        assert hasattr(keystroke, "keystroke_time")
        assert hasattr(keystroke, "keystroke_char")
        assert hasattr(keystroke, "expected_char")
        assert hasattr(keystroke, "is_error")
        assert hasattr(keystroke, "time_since_previous")

        # Verify class methods exist
        assert hasattr(Keystroke, "from_dict")
        assert hasattr(Keystroke, "to_dict")
        assert hasattr(Keystroke, "get_for_session")
        assert hasattr(Keystroke, "get_errors_for_session")
        assert hasattr(Keystroke, "delete_all_keystrokes")


if __name__ == "__main__":
    pytest.main([__file__])
