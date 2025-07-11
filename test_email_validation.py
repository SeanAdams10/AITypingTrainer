"""Test script to debug email validation."""

from models.user import User


def test_email_validation(email: str) -> None:
    """Test email validation with the given email address."""
    try:
        user = User(
            first_name="Test",
            surname="User",
            email_address=email
        )
        print(f"✅ Valid email: {email} -> {user.email_address}")
        return True
    except ValueError as e:
        print(f"❌ Invalid email: {email} -> {str(e)}")
        return False

if __name__ == "__main__":
    # Test cases from INVALID_EMAILS
    test_emails = [
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

    print("\nTesting invalid email formats:")
    results = []
    for email in test_emails:
        results.append(test_email_validation(email))

    failed = sum(1 for r in results if r is True)
    print(f"\nSummary: {failed}/{len(test_emails)} invalid emails were incorrectly accepted")
