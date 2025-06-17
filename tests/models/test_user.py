"""Tests for the User model."""

from uuid import UUID, uuid4

import pytest

from models.user import User

# Test data
VALID_EMAILS = [
    "test@example.com",
    "test.user@example.com",
    "test+user@example.com",
    "test.user+tag@example.co.uk",
    "test@subdomain.example.com",
    "test@123.123.123.123",  # Valid but not recommended
    "test@[123.123.123.123]",  # Valid but not recommended
]

INVALID_EMAILS = [
    "plainaddress",
    "@missingusername.com",
    "username@.com",
    ".username@example.com",
    "username@example..com",
    "username@example.com.",
    "username@.example.com",
    "username@-example.com",
    "username@example-.com",
    "username@example.com-",
    "username@example.c",
    "username@example.com.1a",
    "username@example.com.a",
    "username@example.com.1",
    "username@example.com.a1-",
    "username@example.com.-a",
]

VALID_NAMES = [
    "John",
    "Mary-Jane",
    "O'Reilly",
    "De La Cruz",
    "X",  # Minimum length
    "A" * 64,  # Maximum length
]

INVALID_NAMES = [
    "",  # Empty
    " ",  # Whitespace only
    "\t",  # Tab only
    "\n",  # Newline only
    "A" * 65,  # Too long
    "John@Doe",  # Invalid character
    "John\nDoe",  # Newline
    "John\tDoe",  # Tab
    "John\rDoe",  # Carriage return
    "John\fDoe",  # Form feed
    "John\vDoe",  # Vertical tab
]


class TestUserModel:
    """Test cases for the User model."""

    def test_create_user_with_minimal_fields(self) -> None:
        """Test creating a user with minimal required fields."""
        user = User(first_name="John", surname="Doe", email_address="john.doe@example.com")
        assert user.first_name == "John"
        assert user.surname == "Doe"
        assert user.email_address == "john.doe@example.com"
        assert user.user_id is not None
        try:
            UUID(user.user_id)
        except ValueError:
            pytest.fail("user_id is not a valid UUID")

    def test_create_user_with_existing_id(self) -> None:
        """Test creating a user with a pre-existing ID."""
        test_id = str(uuid4())
        user = User(
            user_id=test_id, first_name="John", surname="Doe", email_address="john.doe@example.com"
        )
        assert user.user_id == test_id

    @pytest.mark.parametrize("email", VALID_EMAILS)
    def test_valid_email_formats(self, email: str) -> None:
        """Test various valid email formats.

        Args:
            email: A valid email address to test.
        """
        user = User(first_name="Test", surname="User", email_address=email)
        assert user.email_address == email.lower()

    @pytest.mark.parametrize("email", INVALID_EMAILS)
    def test_invalid_email_formats(self, email: str) -> None:
        """Test various invalid email formats.

        Args:
            email: An invalid email address that should raise a ValueError.
        """
        with pytest.raises(ValueError):
            User(first_name="Test", surname="User", email_address=email)

    @pytest.mark.parametrize("name", VALID_NAMES)
    def test_valid_name_formats(self, name: str) -> None:
        """Test various valid name formats.

        Args:
            name: A valid name to test.
        """
        user = User(first_name=name, surname=name, email_address="test@example.com")
        assert user.first_name == name.strip()
        assert user.surname == name.strip()

    @pytest.mark.parametrize("name", INVALID_NAMES)
    def test_invalid_name_formats(self, name: str) -> None:
        """Test various invalid name formats.

        Args:
            name: An invalid name that should raise a ValueError.
        """
        with pytest.raises(ValueError):
            User(first_name=name, surname="Valid", email_address="test@example.com")
        with pytest.raises(ValueError):
            User(first_name="Valid", surname=name, email_address="test@example.com")

    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is properly stripped from string fields."""
        user = User(
            first_name="  John  ", surname="  Doe  ", email_address="  john.doe@example.com  "
        )
        assert user.first_name == "John"
        assert user.surname == "Doe"
        assert user.email_address == "john.doe@example.com"

    def test_case_insensitive_email(self) -> None:
        """Test that email addresses are case-insensitive."""
        user1 = User(first_name="John", surname="Doe", email_address="John.Doe@Example.COM")
        user2 = User(first_name="John", surname="Doe", email_address="john.doe@example.com")
        assert user1.email_address.lower() == user2.email_address.lower()

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        user = User(first_name="John", surname="Doe", email_address="john.doe@example.com")
        user_dict = user.to_dict()
        assert user_dict["first_name"] == "John"
        assert user_dict["surname"] == "Doe"
        assert user_dict["email_address"] == "john.doe@example.com"
        assert "user_id" in user_dict

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        user_data = {
            "first_name": "John",
            "surname": "Doe",
            "email_address": "john.doe@example.com",
        }
        user = User.from_dict(user_data)
        assert user.first_name == "John"
        assert user.surname == "Doe"
        assert user.email_address == "john.doe@example.com"
        assert user.user_id is not None

    def test_from_dict_with_extra_fields(self) -> None:
        """Test that extra fields in dictionary raise an error."""
        user_data = {
            "first_name": "John",
            "surname": "Doe",
            "email_address": "john.doe@example.com",
            "extra_field": "should cause error",
        }
        with pytest.raises(ValueError) as excinfo:
            User.from_dict(user_data)
        assert "Extra fields not permitted" in str(excinfo.value)
            
    def test_validate_user_id_empty(self) -> None:
        """Test that empty user_id raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            User(user_id="", first_name="John", surname="Doe", email_address="john.doe@example.com")
        assert "user_id must not be empty" in str(excinfo.value)
        
    def test_validate_user_id_invalid(self) -> None:
        """Test that invalid UUID user_id raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            User(user_id="not-a-uuid", first_name="John", surname="Doe", email_address="john.doe@example.com")
        assert "user_id must be a valid UUID string" in str(excinfo.value)
        
    def test_ip_address_domain_variants(self) -> None:
        """Test various forms of IP address domains in emails."""
        # Test bracketed IP address domain
        user1 = User(first_name="John", surname="Doe", email_address="john@[192.168.1.1]")
        assert "@[192.168.1.1]" in user1.email_address
        
        # Test unbracketed IP address domain
        user2 = User(first_name="John", surname="Doe", email_address="john@192.168.1.1")
        assert "@192.168.1.1" in user2.email_address
        
    def test_special_domain_validation(self) -> None:
        """Test special cases for domain validation."""
        # Valid domain with hyphen
        user = User(first_name="John", surname="Doe", email_address="john@my-domain.com")
        assert user.email_address == "john@my-domain.com"
        
        # Test domains with invalid characters
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@domain_with_underscore.com")
            
        # Test domain with invalid TLD (too short)
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@example.c")
            
        # Test domain with numeric TLD
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@example.123")
    
    def test_domain_edge_cases(self) -> None:
        """Test edge cases in domain validation."""
        # Domain starting with dot
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@.example.com")
            
        # Domain ending with dot
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@example.com.")
            
        # Domain with consecutive dots
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@example..com")
            
        # Domain part starting with hyphen
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@-example.com")
            
        # Domain part ending with hyphen
        with pytest.raises(ValueError):
            User(first_name="John", surname="Doe", email_address="john@example-.com")
