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


def _user_id(user: User) -> str:
    assert user.user_id is not None
    return str(user.user_id)


@pytest.fixture
def user_manager(db_with_tables: DatabaseManager) -> Generator[UserManager, None, None]:
    """Create a UserManager instance with a temporary database."""

    manager = UserManager(db_manager=db_with_tables)
    yield manager


class TestUserManager:
    """Test cases for the UserManager class."""

    def test_create_and_retrieve_user(self, user_manager: UserManager) -> None:
        """Test creating and retrieving a user."""
        # Save the user
        assert user_manager.save_user(user=TEST_USER_1)

        # Retrieve by ID
        user_id = _user_id(TEST_USER_1)
        fetched = user_manager.get_user_by_id(user_id=user_id)
        assert fetched.first_name == TEST_USER_1.first_name
        assert fetched.surname == TEST_USER_1.surname
        assert fetched.email_address == TEST_USER_1.email_address

        # Retrieve by email
        fetched_by_email = user_manager.get_user_by_email(email_address=TEST_USER_1.email_address)
        assert fetched_by_email.user_id == TEST_USER_1.user_id

    def test_update_user(self, user_manager: UserManager) -> None:
        """Test updating an existing user."""
        # Create initial user
        user_manager.save_user(user=TEST_USER_1)

        # Update user
        updated_user = User(
            user_id=_user_id(TEST_USER_1),
            first_name="Alicia",
            surname="Smith-Jones",
            email_address="alicia.smith-jones@example.com",
        )
        assert user_manager.save_user(user=updated_user)

        # Verify update
        fetched = user_manager.get_user_by_id(user_id=_user_id(TEST_USER_1))
        assert fetched.first_name == "Alicia"
        assert fetched.surname == "Smith-Jones"
        assert fetched.email_address == "alicia.smith-jones@example.com"

    def test_delete_user(self, user_manager: UserManager) -> None:
        """Test deleting a user."""
        # Create user
        user_manager.save_user(user=TEST_USER_1)
        user_id = _user_id(TEST_USER_1)

        # Delete user
        assert user_manager.delete_user(user_id=user_id)

        # Verify deletion
        with pytest.raises(UserNotFound):
            user_manager.get_user_by_id(user_id=user_id)

        # Verify delete of non-existent user returns False
        assert not user_manager.delete_user(user_id=str(uuid4()))

    def test_list_all_users(self, user_manager: UserManager) -> None:
        """Test listing all users."""
        # Add multiple users
        user_manager.save_user(user=TEST_USER_1)
        user_manager.save_user(user=TEST_USER_2)

        # Get all users
        users = user_manager.list_all_users()
        assert len(users) == 2
        user_ids = {user.user_id for user in users}
        assert TEST_USER_1.user_id in user_ids
        assert TEST_USER_2.user_id in user_ids

    def test_email_uniqueness(self, user_manager: UserManager) -> None:
        """Test that email addresses must be unique."""
        # Save first user
        user_manager.save_user(user=TEST_USER_1)

        # Create a second user with the same email address but different case
        duplicate_email_user = User(
            first_name="AliceB",  # Valid name without digits
            surname="SmithB",  # Valid name without digits
            email_address=TEST_USER_1.email_address.upper(),  # Same email, different case
        )

        # UserManager should raise UserValidationError when trying to save with duplicate email
        with pytest.raises(UserValidationError) as excinfo:
            user_manager.save_user(user=duplicate_email_user)
        assert "must be unique" in str(excinfo.value)

        # Try to update a user to use an existing email
        user2 = User(first_name="Bob", surname="Johnson", email_address="bob@example.com")
        user_manager.save_user(user=user2)

        # Create a new user2 with conflicting email but mixed case
        # (since User is immutable, we create a new instance)
        updated_user2 = User(
            user_id=_user_id(user2),
            first_name=user2.first_name,
            surname=user2.surname,
            # Title case to test case insensitivity
            email_address=TEST_USER_1.email_address.title(),
        )

        # This should also fail due to email uniqueness (case insensitive)
        with pytest.raises(UserValidationError) as excinfo:
            user_manager.save_user(user=updated_user2)
        assert "must be unique" in str(excinfo.value)

    def test_update_user_with_same_email(self, user_manager: UserManager) -> None:
        """Test that a user can be updated with the same email (their own)."""
        # Create user
        user_manager.save_user(user=TEST_USER_1)

        # Update with same email (should work)
        updated_user = User(
            user_id=_user_id(TEST_USER_1),
            first_name="Alicia",
            surname=TEST_USER_1.surname,
            email_address=TEST_USER_1.email_address,
        )
        assert user_manager.save_user(user=updated_user)

        # Verify update
        fetched = user_manager.get_user_by_id(user_id=_user_id(TEST_USER_1))
        assert fetched.first_name == "Alicia"
        assert fetched.email_address == TEST_USER_1.email_address

    def test_nonexistent_user_retrieval(self, user_manager: UserManager) -> None:
        """Test retrieving non-existent users raises appropriate errors."""
        non_existent_id = str(uuid4())

        with pytest.raises(UserNotFound) as excinfo:
            user_manager.get_user_by_id(user_id=non_existent_id)
        assert non_existent_id in str(excinfo.value)

        with pytest.raises(UserNotFound) as excinfo:
            user_manager.get_user_by_email(email_address="nonexistent@example.com")
        assert "nonexistent@example.com" in str(excinfo.value)

    def test_case_insensitive_email_retrieval(self, user_manager: UserManager) -> None:
        """Test that email retrieval is case-insensitive."""
        # Create user with mixed case email
        user = User(
            first_name="Case", surname="Sensitive", email_address="Case.Sensitive@Example.COM"
        )
        user_manager.save_user(user=user)

        # Retrieve with different case
        fetched = user_manager.get_user_by_email(email_address="case.sensitive@example.com")
        assert fetched.user_id == _user_id(user)

        # Should be stored in lowercase
        assert (
            user_manager.get_user_by_id(user_id=_user_id(user)).email_address == user.email_address.lower()
        )

    def test_empty_database_operations(self, user_manager: UserManager) -> None:
        """Test operations on an empty database."""
        # List all users (should be empty)
        assert user_manager.list_all_users() == []

        # Try to delete non-existent user (should return False, not raise)
        assert not user_manager.delete_user(user_id=str(uuid4()))

    def test_delete_user_by_id_method(self, user_manager: UserManager) -> None:
        """Test the delete_user_by_id method specifically."""
        # Create user
        user_manager.save_user(user=TEST_USER_1)
        user_id = _user_id(TEST_USER_1)

        # Delete using delete_user_by_id method
        assert user_manager.delete_user_by_id(user_id=user_id)

        # Verify deletion
        with pytest.raises(UserNotFound):
            user_manager.get_user_by_id(user_id=user_id)

        # Test deleting non-existent user
        assert not user_manager.delete_user_by_id(user_id=str(uuid4()))

    def test_delete_all_users(self, user_manager: UserManager) -> None:
        """Test deleting all users from the database."""
        # Test with empty database
        assert not user_manager.delete_all_users()  # Should return False (no users to delete)

        # Add multiple users
        user_manager.save_user(user=TEST_USER_1)
        user_manager.save_user(user=TEST_USER_2)

        # Verify users exist
        assert len(user_manager.list_all_users()) == 2

        # Delete all users
        assert user_manager.delete_all_users()  # Should return True (users were deleted)

        # Verify all users are gone
        assert user_manager.list_all_users() == []

        # Test delete_all_users again on empty database
        assert not user_manager.delete_all_users()  # Should return False (no users to delete)

    def test_email_validation_edge_cases(self, user_manager: UserManager) -> None:
        """Test email validation with various edge cases."""
        # Create user with valid email
        user_manager.save_user(user=TEST_USER_1)

        # Test case insensitive uniqueness with different variations
        email_variations = [
            TEST_USER_1.email_address.upper(),
            TEST_USER_1.email_address.lower(),
            TEST_USER_1.email_address.title(),
            TEST_USER_1.email_address.swapcase(),
        ]

        for email_variant in email_variations:
            duplicate_user = User(
                first_name="Different",
                surname="User",
                email_address=email_variant,
            )
            with pytest.raises(UserValidationError, match="must be unique"):
                user_manager.save_user(user=duplicate_user)

    def test_user_retrieval_edge_cases(self, user_manager: UserManager) -> None:
        """Test user retrieval with various edge cases."""
        # Create user with mixed case email
        mixed_case_user = User(
            first_name="Mixed",
            surname="Case",
            email_address="Mixed.Case@Example.COM",
        )
        user_manager.save_user(user=mixed_case_user)

        # Test retrieval with different case variations
        email_variations = [
            "mixed.case@example.com",
            "MIXED.CASE@EXAMPLE.COM",
            "Mixed.Case@Example.COM",
            "mIxEd.CaSe@eXaMpLe.CoM",
        ]

        for email_variant in email_variations:
            retrieved_user = user_manager.get_user_by_email(email_address=email_variant)
            assert retrieved_user.user_id == mixed_case_user.user_id

    def test_comprehensive_crud_workflow(self, user_manager: UserManager) -> None:
        """Test a comprehensive CRUD workflow with multiple operations."""
        # Create multiple users
        users = [
            User(first_name="Alice", surname="Anderson", email_address="alice.anderson@test.com"),
            User(first_name="Bob", surname="Brown", email_address="bob.brown@test.com"),
            User(first_name="Charlie", surname="Clark", email_address="charlie.clark@test.com"),
        ]

        # Save all users
        for user in users:
            assert user_manager.save_user(user=user)

        # Verify all users exist
        all_users = user_manager.list_all_users()
        assert len(all_users) == 3

        # Update one user
        updated_user = User(
            user_id=users[0].user_id,
            first_name="Alicia",
            surname="Anderson-Smith",
            email_address="alicia.anderson.smith@test.com",
        )
        assert user_manager.save_user(user=updated_user)

        # Verify update
        retrieved = user_manager.get_user_by_id(user_id=str(users[0].user_id))
        assert retrieved.first_name == "Alicia"
        assert retrieved.surname == "Anderson-Smith"
        assert retrieved.email_address == "alicia.anderson.smith@test.com"

        # Delete one user
        assert user_manager.delete_user_by_id(user_id=str(users[1].user_id))

        # Verify deletion
        remaining_users = user_manager.list_all_users()
        assert len(remaining_users) == 2

        # Verify correct users remain
        remaining_ids = {user.user_id for user in remaining_users}
        assert users[0].user_id in remaining_ids  # Updated user
        assert users[1].user_id not in remaining_ids  # Deleted user
        assert users[2].user_id in remaining_ids  # Unchanged user
