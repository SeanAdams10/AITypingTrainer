"""
Snippet Pydantic model and validation logic.
"""

from __future__ import annotations

from typing import Any, Dict, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# Common validator helper functions
def validate_non_empty(value: str) -> str:
    """Validate that a string is not empty or just whitespace."""
    if not value or not value.strip():
        raise ValueError("Value cannot be empty or whitespace")
    return value.strip()  # Return stripped value


def validate_ascii_only(value: str) -> str:
    """Validate that a string contains only ASCII characters."""
    if not all(ord(c) < 128 for c in value):
        raise ValueError("Value must contain only ASCII characters")
    return value


def validate_no_sql_injection(value: str, is_content: bool = False) -> str:
    """Check for potential SQL injection patterns in the input.

    Args:
        value: The string to check
        is_content: Whether this is snippet content (code/text) that may legitimately contain
                    quotes and equals signs
    """
    import re

    # Core SQL injection patterns that should never be allowed
    # Using regex patterns to catch variations like SELECT * FROM, SELECT col FROM, etc.
    core_patterns = [
        ("DROP TABLE", r"DROP\s+TABLE"),
        ("DELETE FROM", r"DELETE\s+FROM"),
        ("INSERT INTO", r"INSERT\s+INTO"),
        ("UPDATE SET", r"UPDATE\s+.*\s+SET"),
        ("SELECT FROM", r"SELECT\s+.*\s+FROM"),  # Catches SELECT * FROM, SELECT col FROM, etc.
        ("OR 1=1", r"OR\s+1\s*=\s*1"),
        ("' OR '", r"'\s*OR\s*'"),
    ]

    # Extended patterns that might be legitimate in code snippets but not in names/IDs
    extended_patterns = [
        "--",  # SQL comment
        ";",  # Statement terminator
        "'",  # Single quote (used in SQL injection)
        "=",  # Equals (used in WHERE clauses)
    ]

    # Always check core patterns using regex for more flexible matching
    for pattern_name, pattern_regex in core_patterns:
        if re.search(pattern_regex, value, re.IGNORECASE):
            raise ValueError(f"Value contains potentially unsafe pattern: {pattern_name}")

    # Only check extended patterns if not validating content (code/text)
    if not is_content:
        for pattern in extended_patterns:
            if pattern.lower() in value.lower():
                raise ValueError(f"Value contains potentially unsafe pattern: {pattern}")

    return value


def validate_integer(value: Union[int, str]) -> int:
    """Validate that a value is an integer or can be converted to one.

    Args:
        value: The value to validate, which can be an int or string representation of an int

    Returns:
        The validated integer value

    Raises:
        ValueError: If the value cannot be converted to an integer
    """
    try:
        if isinstance(value, str):
            # Ensure string is a valid representation of an integer
            if not value.strip().isdigit() and not (value.startswith("-") and value[1:].isdigit()):
                raise ValueError("String must represent a valid integer")
            return int(value)
        if not isinstance(value, int):
            raise ValueError("Value must be an integer")
        return value
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Value must be an integer: {value}") from exc


class Snippet(BaseModel):
    """Pydantic model for a typing snippet.

    Attributes:
        snippet_id: Unique identifier for the snippet (UUID string).
        category_id: Identifier for the category this snippet belongs to (UUID string).
        snippet_name: Name of the snippet (must be unique within a category).
        content: The actual text content of the snippet.
    """

    snippet_id: str | None = None
    snippet_name: str = Field(...)
    content: str = Field(...)
    category_id: str = Field(...)
    description: str = Field("")

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }

    @model_validator(mode="before")
    @classmethod
    def ensure_snippet_id(cls, values: dict) -> dict:
        if not values.get("snippet_id"):
            values["snippet_id"] = str(uuid4())
        return values

    @field_validator("snippet_id", "category_id", mode="before")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        if not v:
            raise ValueError("ID must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("ID must be a valid UUID string") from err
        return v

    @field_validator("snippet_name", mode="before")
    @classmethod
    def validate_snippet_name(cls, v: str) -> str:
        v = validate_non_empty(v)
        v = validate_ascii_only(v)
        v = validate_no_sql_injection(v, is_content=False)
        if not (1 <= len(v) <= 128):
            raise ValueError("Snippet name must be between 1 and 128 characters")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = validate_non_empty(v)
        v = validate_ascii_only(v)
        v = validate_no_sql_injection(v, is_content=True)
        if not (len(v) >= 1):
            raise ValueError("Content must be at least 1 character long")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Snippet":
        allowed = set(cls.__fields__.keys())
        extra = set(d.keys()) - allowed
        if extra:
            from pydantic import ErrorWrapper, ValidationError

            errors = [
                ErrorWrapper(ValueError(f"Extra field not permitted: {field}"), loc=field)
                for field in extra
            ]
            raise ValidationError(errors, cls)
        return cls(**d)
