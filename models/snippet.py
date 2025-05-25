"""
Snippet Pydantic model and validation logic.
"""

from typing import Dict, Optional, Union

from pydantic import BaseModel, Field, field_validator


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
                raise ValueError(
                    f"Value contains potentially unsafe pattern: {pattern}"
                )

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
            if not value.strip().isdigit() and not (value.startswith('-') and value[1:].isdigit()):
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
        snippet_id: Optional unique identifier for the snippet.
        category_id: Identifier for the category this snippet belongs to.
        snippet_name: Name of the snippet (must be unique within a category).
        content: The actual text content of the snippet.
    """
    snippet_id: Optional[int] = None
    category_id: int
    # snippet_name: Name of the snippet, ASCII, 1-128 chars.
    # Unique within category enforced by SnippetManager.
    snippet_name: str = Field(
        min_length=1, max_length=128 # ASCII pattern handled by validator
    )
    content: str = Field(min_length=1)

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }

    @field_validator("snippet_id", mode="before")
    @classmethod
    def validate_snippet_id(cls, v: Optional[Union[int, str]]) -> Optional[int]:
        if v is not None:
            return validate_integer(v)
        return None

    @field_validator("category_id", mode="before")
    @classmethod
    def validate_category_id(cls, v: Union[int, str]) -> int:
        return validate_integer(v)

    @field_validator("snippet_name")
    @classmethod
    def validate_snippet_name(cls, v: str) -> str:
        v = validate_non_empty(v)
        v = validate_ascii_only(v)
        # SQL injection check for names should be strict (is_content=False)
        v = validate_no_sql_injection(v, is_content=False)
        if not (1 <= len(v) <= 128):
            raise ValueError("Snippet name must be between 1 and 128 characters")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = validate_non_empty(v)
        # Content can have a broader range of characters, but still good to validate.
        # For now, keeping ASCII only, but this could be relaxed if needed.
        v = validate_ascii_only(v)
        # SQL injection check for content should be less strict (is_content=True)
        v = validate_no_sql_injection(v, is_content=True)
        if not (len(v) >= 1):
             raise ValueError("Content must be at least 1 character long")
        return v

    @classmethod
    def from_dict(cls, data: Dict) -> "Snippet":
        """Create a Snippet instance from a dictionary.

        Args:
            data: Dictionary containing snippet data.

        Returns:
            Snippet: An instance of the Snippet class.

        Raises:
            ValueError: If unexpected fields are present in the data.
        """
        allowed_fields = {"snippet_id", "category_id", "snippet_name", "content"}
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}

        if len(filtered_data) != len(data):
            extra_keys = [k for k in data if k not in allowed_fields]
            raise ValueError(f"Extra fields not permitted: {extra_keys}")

        return cls(**filtered_data)

    def to_dict(self) -> Dict:
        """Convert the Snippet instance to a dictionary.

        Returns:
            Dict: A dictionary representation of the snippet.
        """
        return {
            "snippet_id": self.snippet_id,
            "category_id": self.category_id,
            "snippet_name": self.snippet_name,
            "content": self.content,
        }
