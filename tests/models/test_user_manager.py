import pytest

from db.database_manager import DatabaseManager
from models.user import User
from models.user_manager import UserManager, UserNotFound, UserValidationError


def temp_db():
    db = DatabaseManager(":memory:")
    db.init_tables()
    return db


def test_user_manager_crud():
    db = temp_db()
    manager = UserManager(db)
    user = User(first_name="Alice", surname="Smith", email_address="alice@example.com")
    # Create
    assert manager.save_user(user)
    # Read by id
    fetched = manager.get_user_by_id(user.user_id)
    assert fetched.first_name == "Alice"
    # Read by email
    fetched2 = manager.get_user_by_email("alice@example.com")
    assert fetched2.user_id == user.user_id
    # List all
    users = manager.list_all_users()
    assert len(users) == 1
    # Update
    user.surname = "Johnson"
    assert manager.save_user(user)
    assert manager.get_user_by_id(user.user_id).surname == "Johnson"
    # Delete
    assert manager.delete_user(user.user_id)
    assert manager.list_all_users() == []
    # Not found
    with pytest.raises(UserNotFound):
        manager.get_user_by_id(user.user_id)
    with pytest.raises(UserNotFound):
        manager.get_user_by_email("alice@example.com")


def test_user_manager_email_uniqueness():
    db = temp_db()
    manager = UserManager(db)
    user1 = User(first_name="Alice", surname="Smith", email_address="alice@example.com")
    user2 = User(first_name="Bob", surname="Brown", email_address="alice@example.com")
    manager.save_user(user1)
    with pytest.raises(UserValidationError):
        manager.save_user(user2)
