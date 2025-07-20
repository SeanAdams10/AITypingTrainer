"""
Tests for UserManager database access pattern fixes.
Specifically tests the fixes for psycopg2.ProgrammingError: no results to fetch.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List
import uuid

from models.user_manager import UserManager, UserNotFound, UserValidationError
from models.user import User


class TestUserManagerDatabaseAccessFixes:
    """Test the UserManager database access pattern fixes."""

    @pytest.fixture
    def mock_db_manager(self) -> Mock:
        """Create a mock database manager."""
        return Mock()

    @pytest.fixture
    def user_manager(self, mock_db_manager: Mock) -> UserManager:
        """Create a UserManager with mock database manager."""
        return UserManager(mock_db_manager)

    @pytest.fixture
    def sample_user_data(self) -> Dict[str, Any]:
        """Sample user data as returned by fetchone."""
        return {
            "user_id": str(uuid.uuid4()),
            "first_name": "John",
            "surname": "Doe",
            "email_address": "john.doe@example.com"
        }

    @pytest.fixture
    def sample_users_data(self) -> List[Dict[str, Any]]:
        """Sample users data as returned by fetchall."""
        return [
            {
                "user_id": str(uuid.uuid4()),
                "first_name": "Alice",
                "surname": "Smith",
                "email_address": "alice@example.com"
            },
            {
                "user_id": str(uuid.uuid4()),
                "first_name": "Bob",
                "surname": "Jones",
                "email_address": "bob@example.com"
            }
        ]

    def test_list_all_users_with_results(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock,
        sample_users_data: List[Dict[str, Any]]
    ) -> None:
        """Test list_all_users when users exist."""
        mock_db_manager.fetchall.return_value = sample_users_data
        
        users = user_manager.list_all_users()
        
        assert len(users) == 2
        assert users[0].first_name == "Alice"
        assert users[0].surname == "Smith"
        assert users[1].first_name == "Bob"
        assert users[1].surname == "Jones"
        mock_db_manager.fetchall.assert_called_once()

    def test_list_all_users_empty_database(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test list_all_users when no users exist (empty database)."""
        mock_db_manager.fetchall.return_value = []
        
        users = user_manager.list_all_users()
        
        assert users == []
        mock_db_manager.fetchall.assert_called_once()

    def test_get_user_by_id_found(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock,
        sample_user_data: Dict[str, Any]
    ) -> None:
        """Test get_user_by_id when user exists."""
        mock_db_manager.fetchone.return_value = sample_user_data
        
        test_user_id = sample_user_data["user_id"]
        user = user_manager.get_user_by_id(test_user_id)
        
        assert user.user_id == test_user_id
        assert user.first_name == "John"
        assert user.surname == "Doe"
        assert user.email_address == "john.doe@example.com"
        mock_db_manager.fetchone.assert_called_once()

    def test_get_user_by_id_not_found(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test get_user_by_id when user doesn't exist."""
        mock_db_manager.fetchone.return_value = None
        
        test_user_id = str(uuid.uuid4())
        with pytest.raises(UserNotFound, match=f"User with ID {test_user_id} not found"):
            user_manager.get_user_by_id(test_user_id)
        
        mock_db_manager.fetchone.assert_called_once()

    def test_get_user_by_email_found(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock,
        sample_user_data: Dict[str, Any]
    ) -> None:
        """Test get_user_by_email when user exists."""
        mock_db_manager.fetchone.return_value = sample_user_data
        
        test_user_id = sample_user_data["user_id"]
        user = user_manager.get_user_by_email("john.doe@example.com")
        
        assert user.user_id == test_user_id
        assert user.first_name == "John"
        assert user.surname == "Doe"
        assert user.email_address == "john.doe@example.com"
        mock_db_manager.fetchone.assert_called_once()

    def test_get_user_by_email_not_found(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test get_user_by_email when user doesn't exist."""
        mock_db_manager.fetchone.return_value = None
        
        with pytest.raises(UserNotFound, match="User with email 'test@example.com' not found"):
            user_manager.get_user_by_email("test@example.com")
        
        mock_db_manager.fetchone.assert_called_once()

    def test_user_exists_true(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test __user_exists when user exists."""
        mock_db_manager.fetchone.return_value = {"1": 1}  # EXISTS query result
        
        # Access private method for testing
        test_user_id = str(uuid.uuid4())
        result = user_manager._UserManager__user_exists(test_user_id)
        
        assert result is True
        mock_db_manager.fetchone.assert_called_once()

    def test_user_exists_false(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test __user_exists when user doesn't exist."""
        mock_db_manager.fetchone.return_value = None
        
        # Access private method for testing
        test_user_id = str(uuid.uuid4())
        result = user_manager._UserManager__user_exists(test_user_id)
        
        assert result is False
        mock_db_manager.fetchone.assert_called_once()

    def test_delete_user_by_id_exists(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test delete_user_by_id when user exists."""
        mock_db_manager.fetchone.return_value = {"1": 1}  # User exists
        mock_db_manager.execute.return_value = None
        
        test_user_id = str(uuid.uuid4())
        result = user_manager.delete_user_by_id(test_user_id)
        
        assert result is True
        assert mock_db_manager.fetchone.call_count == 1
        assert mock_db_manager.execute.call_count == 1

    def test_delete_user_by_id_not_exists(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test delete_user_by_id when user doesn't exist."""
        mock_db_manager.fetchone.return_value = None  # User doesn't exist
        
        test_user_id = str(uuid.uuid4())
        result = user_manager.delete_user_by_id(test_user_id)
        
        assert result is False
        mock_db_manager.fetchone.assert_called_once()
        mock_db_manager.execute.assert_not_called()

    def test_delete_all_users_with_users_dict_result(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test delete_all_users when users exist (dict count result)."""
        mock_db_manager.fetchone.return_value = {"count": 5}  # 5 users exist
        mock_db_manager.execute.return_value = None
        
        result = user_manager.delete_all_users()
        
        assert result is True
        assert mock_db_manager.fetchone.call_count == 1
        assert mock_db_manager.execute.call_count == 1

    def test_delete_all_users_with_users_non_dict_result(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test delete_all_users when users exist (non-dict count result)."""
        mock_db_manager.fetchone.return_value = 3  # 3 users exist (non-dict)
        mock_db_manager.execute.return_value = None
        
        result = user_manager.delete_all_users()
        
        assert result is True
        assert mock_db_manager.fetchone.call_count == 1
        assert mock_db_manager.execute.call_count == 1

    def test_delete_all_users_no_users_dict_result(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test delete_all_users when no users exist (dict count result)."""
        mock_db_manager.fetchone.return_value = {"count": 0}  # No users
        mock_db_manager.execute.return_value = None
        
        result = user_manager.delete_all_users()
        
        assert result is False
        assert mock_db_manager.fetchone.call_count == 1
        assert mock_db_manager.execute.call_count == 1

    def test_delete_all_users_no_users_empty_result(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test delete_all_users when no users exist (empty count result)."""
        mock_db_manager.fetchone.return_value = None  # Empty result
        mock_db_manager.execute.return_value = None
        
        result = user_manager.delete_all_users()
        
        assert result is False
        assert mock_db_manager.fetchone.call_count == 1
        assert mock_db_manager.execute.call_count == 1

    def test_validate_email_uniqueness_unique(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test _validate_email_uniqueness when email is unique."""
        mock_db_manager.fetchone.return_value = None  # No duplicate found
        
        # Should not raise exception
        user_manager._validate_email_uniqueness("unique@example.com")
        
        mock_db_manager.fetchone.assert_called_once()

    def test_validate_email_uniqueness_duplicate(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test _validate_email_uniqueness when email is not unique."""
        mock_db_manager.fetchone.return_value = {"1": 1}  # Duplicate found
        
        with pytest.raises(UserValidationError, match="Email address 'duplicate@example.com' must be unique"):
            user_manager._validate_email_uniqueness("duplicate@example.com")
        
        mock_db_manager.fetchone.assert_called_once()

    def test_validate_email_uniqueness_update_same_user(
        self,
        user_manager: UserManager,
        mock_db_manager: Mock
    ) -> None:
        """Test _validate_email_uniqueness when updating same user's email."""
        mock_db_manager.fetchone.return_value = None  # No other user has this email
        
        # Should not raise exception when updating same user
        user_manager._validate_email_uniqueness("test@example.com", "user-123")
        
        mock_db_manager.fetchone.assert_called_once()
