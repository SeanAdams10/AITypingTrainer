"""Unit tests for the Snippet Pydantic model."""

import uuid

import pytest
from pydantic import ValidationError

from models.snippet import Snippet, validate_no_sql_injection


def test_snippet_valid_data_produces_model() -> None:
    model = Snippet(
        category_id=str(uuid.uuid4()),
        snippet_name="ValidName",
        content="Valid content",
        description="",
    )

    assert model.snippet_id
    assert model.snippet_name == "ValidName"
    assert model.content == "Valid content"


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "a" * 129,
        "Invälid",
        "Robert'); DROP TABLE snippets;--",
    ],
)
def test_snippet_invalid_names_raise_validation_error(name: str) -> None:
    with pytest.raises(ValidationError):
        Snippet(
            category_id=str(uuid.uuid4()),
            snippet_name=name,
            content="Valid content",
            description="",
        )


def test_snippet_name_is_stripped() -> None:
    model = Snippet(
        category_id=str(uuid.uuid4()),
        snippet_name="  TrimMe  ",
        content="abc",
        description="",
    )

    assert model.snippet_name == "TrimMe"


@pytest.mark.parametrize(
    "content",
    [
        "",
        " ",
        "InvalidÇontent",
        "text'); DROP TABLE snippets; --",
    ],
)
def test_snippet_invalid_content_raises(content: str) -> None:
    with pytest.raises(ValidationError):
        Snippet(
            category_id=str(uuid.uuid4()),
            snippet_name="ValidName",
            content=content,
            description="",
        )


def test_snippet_valid_content_allows_python_code() -> None:
    python_code = """import numpy as np\nmean = np.mean([1, 2, 3])\nprint(f\"Mean: {mean}\")"""

    model = Snippet(
        category_id=str(uuid.uuid4()),
        snippet_name="PythonSnippet",
        content=python_code,
        description="",
    )

    assert model.content == python_code


def test_validate_no_sql_injection_respects_is_content_flag() -> None:
    python_code = """df['Age'] = df['Age'] + 1  # equals sign"""

    validate_no_sql_injection(python_code, is_content=True)

    with pytest.raises(ValueError):
        validate_no_sql_injection(python_code, is_content=False)


def test_snippet_invalid_category_id_raises() -> None:
    with pytest.raises(ValidationError):
        Snippet(
            category_id="not-a-uuid",
            snippet_name="ValidName",
            content="Valid content",
            description="",
        )


def test_snippet_sql_injection_patterns_blocked() -> None:
    with pytest.raises(ValidationError):
        Snippet(
            category_id=str(uuid.uuid4()),
            snippet_name="Name'); DROP TABLE categories; --",
            content="Safe",
            description="",
        )


def test_snippet_content_core_patterns_blocked() -> None:
    with pytest.raises(ValidationError):
        Snippet(
            category_id=str(uuid.uuid4()),
            snippet_name="SafeName",
            content="DROP TABLE snippets;",
            description="",
        )
