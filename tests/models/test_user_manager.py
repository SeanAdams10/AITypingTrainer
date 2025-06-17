"""Comprehensive tests for the UserManager class."""

from typing import Generator
from uuid import uuid4

import pytest

from db.database_manager import DatabaseManager
from models.user import User
from models.user_manager import UserManager, UserNotFound, UserValidationError

# Test data
TEST_USER_1 = User(first_name="Alice", surname="Smith", email_address="alice.smith@example.com")

TEST_USER_2 = User(first_name="Bob", surname="Johnson", email_address="bob.johnson@example.com")

TEST_USER_UPDATED = User(
    first_name="Alicia", surname="Smith-Jones", email_address="alicia.smith-jones@example.com"
)


@pytest.fixture
def temp_db() -> Generator[DatabaseManager, None, None]:
    """Create a temporary in-memory database for testing."""
    db = DatabaseManager(":memory:")
    db.init_tables()
    yield db
    db.close()


@pytest.fixture
def user_manager(temp_db: DatabaseManager) -> UserManager:
    """Create a UserManager instance with a temporary database."""
    return UserManager(temp_db)


class TestUserManager:
    """Test cases for the UserManager class."""

    def test_create_and_retrieve_user(self, user_manager: UserManager) -> None:
        """Test creating and retrieving a user."""
        # Save the user
        assert user_manager.save_user(TEST_USER_1)

        # Retrieve by ID
        fetched = user_manager.get_user_by_id(TEST_USER_1.user_id)
        assert fetched.first_name == TEST_USER_1.first_name
        assert fetched.surname == TEST_USER_1.surname
        assert fetched.email_address == TEST_USER_1.email_address

        # Retrieve by email
        fetched_by_email = user_manager.get_user_by_email(TEST_USER_1.email_address)
        assert fetched_by_email.user_id == TEST_USER_1.user_id

    def test_update_user(self, user_manager: UserManager) -> None:
        """Test updating an existing user."""
        # Create initial user
        user_manager.save_user(TEST_USER_1)

        # Update user
        updated_user = User(
            user_id=TEST_USER_1.user_id,
            first_name="Alicia",
            surname="Smith-Jones",
            email_address="alicia.smith-jones@example.com",
        )
        assert user_manager.save_user(updated_user)

        # Verify update
        fetched = user_manager.get_user_by_id(TEST_USER_1.user_id)
        assert fetched.first_name == "Alicia"
        assert fetched.surname == "Smith-Jones"
        assert fetched.email_address == "alicia.smith-jones@example.com"

    def test_delete_user(self, user_manager: UserManager) -> None:
        """Test deleting a user."""
        # Create user
        user_manager.save_user(TEST_USER_1)

        # Delete user
        assert user_manager.delete_user(TEST_USER_1.user_id)

        # Verify deletion
        with pytest.raises(UserNotFound):
            user_manager.get_user_by_id(TEST_USER_1.user_id)

        # Verify delete of non-existent user returns False
        assert not user_manager.delete_user(str(uuid4()))

    def test_list_all_users(self, user_manager: UserManager) -> None:
        """Test listing all users."""
        # Add multiple users
        user_manager.save_user(TEST_USER_1)
        user_manager.save_user(TEST_USER_2)

        # Get all users
        users = user_manager.list_all_users()
        assert len(users) == 2
        user_ids = {user.user_id for user in users}
        assert TEST_USER_1.user_id in user_ids
        assert TEST_USER_2.user_id in user_ids

    def test_email_uniqueness(self, user_manager: UserManager) -> None:
        """Test that email addresses must be unique."""
        # Save first user
        user_manager.save_user(TEST_USER_1)
        
        # Create a different user email but with the same lowercase representation
        # Since User model normalizes emails to lowercase, need different approach
        duplicate_email_user = User(
            first_name="Alice2",
            surname="Smith2",
            # Use a different email that will normalize the same way
            email_address="ALICE.smith@example.com"  # Will normalize to same as TEST_USER_1
        )
        
        # This should fail because the normalized emails match
        with pytest.raises(UserValidationError) as excinfo:
            user_manager.save_user(duplicate_email_user)
        assert "must be unique" in str(excinfo.value)
        
        # Try to update a user to use an existing email
        user2 = User(
            first_name="Bob",
            surname="Johnson",
            email_address="bob@example.com"
        )
        user_manager.save_user(user2)
        
        # Create a new user2 with the conflicting email (since User is immutable)
        updated_user2 = User(
            user_id=user2.user_id,
            first_name=user2.first_name,
            surname=user2.surname,
            email_address=TEST_USER_1.email_address
        )
        
        # This should fail due to email uniqueness
        with pytest.raises(UserValidationError) as excinfo:
            user_manager.save_user(updated_user2)
        assert "must be unique" in str(excinfo.value)

    def test_update_user_with_same_email(self, user_manager: UserManager) -> None:
        """Test that a user can be updated with the same email (their own)."""
        # Create user
        user_manager.save_user(TEST_USER_1)

        # Update with same email (should work)
        updated_user = User(
            user_id=TEST_USER_1.user_id,
            first_name="Alicia",
            surname=TEST_USER_1.surname,
            email_address=TEST_USER_1.email_address,
        )
        assert user_manager.save_user(updated_user)

        # Verify update
        fetched = user_manager.get_user_by_id(TEST_USER_1.user_id)
        assert fetched.first_name == "Alicia"
        assert fetched.email_address == TEST_USER_1.email_address

    def test_nonexistent_user_retrieval(self, user_manager: UserManager) -> None:
        """Test retrieving non-existent users raises appropriate errors."""
        non_existent_id = str(uuid4())

        with pytest.raises(UserNotFound) as excinfo:
            user_manager.get_user_by_id(non_existent_id)
        assert non_existent_id in str(excinfo.value)

        with pytest.raises(UserNotFound) as excinfo:
            user_manager.get_user_by_email("nonexistent@example.com")
        assert "nonexistent@example.com" in str(excinfo.value)

    def test_case_insensitive_email_retrieval(self, user_manager: UserManager) -> None:
        """Test that email retrieval is case-insensitive."""
        # Create user with mixed case email
        user = User(
            first_name="Case", surname="Sensitive", email_address="Case.Sensitive@Example.COM"
        )
        user_manager.save_user(user)

        # Retrieve with different case
        fetched = user_manager.get_user_by_email("case.sensitive@example.com")
        assert fetched.user_id == user.user_id

        # Should be stored in lowercase
        assert user_manager.get_user_by_id(user.user_id).email_address == user.email_address.lower()

    def test_empty_database_operations(self, user_manager: UserManager) -> None:
        """Test operations on an empty database."""
        # List all users (should be empty)
        assert user_manager.list_all_users() == []

        # Try to delete non-existent user (should return False, not raise)
        assert not user_manager.delete_user(str(uuid4()))
