import pytest

from models.user import User


def test_user_valid():
    user = User(first_name="Alice", surname="Smith", email_address="alice@example.com")
    assert user.first_name == "Alice"
    assert user.surname == "Smith"
    assert user.email_address == "alice@example.com"
    assert user.user_id is not None


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("first_name", "", "Name cannot be blank."),
        ("surname", "", "Name cannot be blank."),
        ("first_name", "A" * 65, "Name must be at most 64 characters."),
        ("surname", "B" * 65, "Name must be at most 64 characters."),
        ("first_name", "Alïce", "Name must be ASCII-only."),
        ("surname", "Smïth", "Name must be ASCII-only."),
        ("email_address", "", "Email address cannot be blank."),
        ("email_address", "a@b", "Email address must be 5-128 characters."),
        ("email_address", "a" * 129 + "@example.com", "Email address must be 5-128 characters."),
        ("email_address", "aliceatexample.com", "Email address must contain '@' and '.'"),
        ("email_address", "alice@examplé.com", "Email address must be ASCII-only."),
    ],
)
def test_user_invalid(field, value, error):
    kwargs = {"first_name": "Alice", "surname": "Smith", "email_address": "alice@example.com"}
    kwargs[field] = value
    with pytest.raises(ValueError) as exc:
        User(**kwargs)
    assert error in str(exc.value)
