"""User data model."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator, model_validator


class User(BaseModel):
    """User data model with validation.

    Attributes:
        user_id: Unique identifier for the user (UUID string).
        first_name: User's first name (ASCII, 1-64 chars).
        surname: User's surname (ASCII, 1-64 chars).
        email_address: User's email address (ASCII, 5-128 chars).
    """

    user_id: str | None = None
    first_name: str = Field(...)
    surname: str = Field(...)
    email_address: str = Field(...)
    created_at: datetime | str | None = None

    model_config = {
        "frozen": True,  # Make the model immutable after creation
    }

    @field_validator("first_name", "surname")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        r"""Validate name format.

        Names must:
        - Not be empty or whitespace only
        - Be 1-64 characters long
        - Be ASCII-only
        - Not contain control characters (\n, \t, etc.)
        - Only contain letters, spaces, hyphens, and apostrophes
        - Not start or end with a space, hyphen, or apostrophe
        - Not contain consecutive spaces, hyphens, or apostrophes

        Args:
            v: The name to validate

        Returns:
            The validated and stripped name

        Raises:
            ValueError: If the name is invalid
        """
        if not v or not v.strip():
            raise ValueError("Name cannot be blank.")

        stripped_v = v.strip()

        # Length validation
        if not stripped_v:
            raise ValueError("Name cannot be blank.")
        if len(stripped_v) > 64:
            raise ValueError("Name must be at most 64 characters.")

        # Check for ASCII-only
        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("Name must be ASCII-only.")

        # Check for control characters
        if any(ord(c) < 32 for c in stripped_v):
            raise ValueError("Name contains invalid control characters.")

        # Check for invalid characters (only letters, spaces, hyphens, and apostrophes allowed)
        if not all(c.isalpha() or c.isspace() or c in "-.'" for c in stripped_v):
            raise ValueError("Name contains invalid characters.")

        # Check for leading/trailing spaces, hyphens, or apostrophes
        if stripped_v[0] in " -'" or stripped_v[-1] in " -'":
            raise ValueError("Name cannot start or end with a space, hyphen, or apostrophe.")

        # Check for consecutive spaces, hyphens, or apostrophes
        for i in range(len(stripped_v) - 1):
            if stripped_v[i] in " -'" and stripped_v[i + 1] in " -'":
                raise ValueError("Name cannot contain consecutive spaces, hyphens, or apostrophes.")

        return stripped_v

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate and normalize the email address using email-validator."""
        if not v or not v.strip():
            raise ValueError("Email address cannot be blank.")

        stripped_v = v.strip()

        # Basic length and character validation
        if len(stripped_v) < 5 or len(stripped_v) > 128:
            raise ValueError("Email address must be 5-128 characters.")

        if not all(ord(c) < 128 for c in stripped_v):
            raise ValueError("Email address must be ASCII-only.")

        # Check if this is an IP address domain (with or without brackets)
        if "@" in stripped_v:
            _, domain = stripped_v.split("@", 1)

            # Handle IP address in domain (with or without brackets)
            is_bracketed = domain.startswith("[") and domain.endswith("]")
            domain_to_check = domain[1:-1] if is_bracketed else domain

            # Check if it's an IP address (all parts are digits and dots)
            try:
                ip_parts = domain_to_check.split(".")
                if len(ip_parts) == 4 and all(
                    part.isdigit() and 0 <= int(part) <= 255 for part in ip_parts
                ):
                    # It's a valid IP address, skip the rest of the validation
                    local_part = stripped_v.split("@")[0].lower()
                    # Preserve the original bracketed format if it was provided
                    return f"{local_part}@{domain if is_bracketed else domain_to_check}"
            except (ValueError, AttributeError):
                pass  # Not an IP address, continue with normal validation

            # For non-IP addresses, perform standard domain validation
            # Check for consecutive dots in domain
            if ".." in domain:
                raise ValueError("Domain cannot contain consecutive dots")

            # Check for domain starting or ending with a dot
            if domain.startswith(".") or domain.endswith("."):
                raise ValueError("Domain cannot start or end with a dot")

            # Split domain into parts
            domain_parts = domain.split(".")

            # Check each domain part
            for part in domain_parts:
                # Check for empty parts (should be caught by other validations)
                if not part:
                    continue

                # Check for invalid characters in domain parts
                if not all(c.isalnum() or c == "-" for c in part):
                    raise ValueError(f"Domain part '{part}' contains invalid characters")

                # Check for parts starting or ending with a hyphen
                if part.startswith("-") or part.endswith("-"):
                    raise ValueError("Domain parts cannot start or end with a hyphen")

            # Validate TLD (last part of domain)
            tld = domain_parts[-1]
            if len(domain_parts) < 2:
                raise ValueError("Domain must have at least one dot")

            # TLD must be at least 2 characters and contain only letters
            if len(tld) < 2 or not tld.isalpha():
                raise ValueError(
                    "Top-level domain must be at least 2 letters and contain only letters"
                )

        # Use email-validator for comprehensive validation
        try:
            # Validate the email
            email_info = validate_email(
                stripped_v,
                check_deliverability=False,  # Don't check if domain actually exists
                allow_smtputf8=False,  # Require ASCII-only
                allow_empty_local=False,
            )

            # Return the normalized email (lowercase, etc.)
            return email_info.normalized

        except EmailNotValidError as e:
            # Convert email-validator's error messages to our format
            raise ValueError(str(e)) from e

    @model_validator(mode="before")
    @classmethod
    def ensure_user_id(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure `user_id` exists by generating a UUID when value is missing or None."""
        # Only generate a default UUID if user_id is None (not provided)
        # NOT if it's an empty string (explicitly provided as empty)
        if "user_id" not in values or values["user_id"] is None:
            values["user_id"] = str(uuid4())
        # Normalize created_at to datetime if provided as str
        ca = values.get("created_at")
        if isinstance(ca, str):
            try:
                values["created_at"] = datetime.fromisoformat(ca)
            except Exception:
                # Leave as-is; pydantic may attempt parsing
                pass
        return values

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate that `user_id` is a non-empty valid UUID string."""
        if not v:
            raise ValueError("user_id must not be empty")
        try:
            UUID(v)
        except Exception as err:
            raise ValueError("user_id must be a valid UUID string") from err
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict representation via Pydantic's `model_dump()`."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "User":
        """Create a `User` from a dict while rejecting unexpected fields."""
        allowed = set(cls.model_fields.keys())
        extra = set(d.keys()) - allowed
        if extra:
            raise ValueError(f"Extra fields not permitted: {extra}")
        return cls(**d)
