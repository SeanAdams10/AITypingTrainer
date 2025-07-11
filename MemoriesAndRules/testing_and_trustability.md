# Testing and Trustability Rules

## General Principles
- All functionality in `.md` spec files under `prompts` and `@MemoriesAndRules` must be implemented and robustly tested.
- Robust tests must exist for all happy paths, edge cases, and destructive scenarios (e.g., injection, boundary, non-ASCII, blank, volume, timeout).
- Testing must proceed layer by layer; do not move on until all tests in the current layer pass with no failures or warnings.

## Test Design & Execution
- All tests must run independently and in any order.
- Use `pytest`/`pytest-mock` for all Python tests (strong preference over `unittest`).
- For UI, use the most controllable test framework (e.g., Selenium, Playwright, PyQt test utilities).
- Never use or alter the production DB (`project_root/typing_trainer.db`).
- All tests must use a temporary, isolated DB via pytest fixtures, cleaned up after each test.
- Core tables (e.g., `text_category`) must be created via app initialization, not manual SQL.
- Use pytest parameterization for repeated tests.
- All tests must leave the environment unchanged.

## Test Execution Order
1. Class/Core level: `tests/core`
2. API level: `tests/api`
3. Web UI: `tests/web` (if exists)
4. Desktop UI: `tests/desktop` (if exists)
- Do not skip or ignore any tests or warnings.

## information hiding
Tests must NOT touch the internals of any object, or know how this is implemented under the cover.    For example, no test should connect to SQLite, other than through the DatabaseManager class.    No test should inspect private variables.     If a test needs test affordances to make sure that a test is running successfully then this needs to be added to the class.     Follow TDD best practices here.

## Test Covereage
We are looking for 99% test coverage - if there are large areas of code which are missing, please suggest


## Test Structure
Strong preference that a test should test one thing rather than a test that has 20 assertions.    If a test has more than 1 or 2 asssertions, break this up into more atomic tests.

## Stubbing
While mocking and stubbing is necessary - this can also become self delusion.    Do not use mocks so much that the actual functionality of the object is not being tested.


## After All Tests Pass
- Only then address all currently known problems (`@current_problems`).
- Then run `mypy` (most verbose mode) on all `.py` files (excluding `.venv`) and fix all issues.
- Then run 'ruff' on all tests with autofix on - excluding anything under .venv
- After all tests, type checks, and lints are clean, update `.md` spec files to reflect the latest functionality. **Signal all changes to `.md` files loudly and visibly—these require explicit user acceptance.**

## Test Documentation and Execution Requirements

### Headless Test Execution
- All tests must be designed to run in a headless environment without user intervention
- Use mocking for any UI components that would normally require user interaction
- Avoid tests that depend on specific screen resolutions or window focus
- Use virtual displays or headless browsers when testing GUI components
- Ensure tests clean up all resources and processes when complete

### Test Documentation
- Every test function must begin with a docstring that clearly describes its purpose
- Start the docstring with "Test objective:" followed by a concise description of what functionality or outcome is being validated
- Include any important preconditions or assumptions
- Document any test-specific setup or teardown requirements
- For parameterized tests, explain the purpose of each parameter combination

Example:
```python
def test_user_login_with_valid_credentials():
    """Test objective: Verify that users can log in with valid credentials.

    This test validates that:
    - Users with correct credentials are authenticated
    - Session is properly initialized after successful login
    - User is redirected to the dashboard

    Preconditions:
    - Test user account exists in the test database
    - Test server is running with clean test database
    """
    # Test implementation...
```

## Persistent Context
- Always bring rules or memories in `.md` files under `@MemoriesAndRules` into context for every run
- Review and apply all relevant project memories and user rules before executing any testing or trustability actions

## Test Helpers and Fixtures

### Database Testing Helpers
Database testing helpers are located in `tests/helpers/db_helpers.py` and provide reusable fixtures for database testing:

#### Available Fixtures:
1. `temp_db`: Creates a temporary database file that's automatically cleaned up after the test
   ```python
   def test_something(temp_db):
       # temp_db is a path to a temporary database file
       db_manager = DatabaseManager(temp_db)
       # ... test code ...
   ```

2. `db_manager`: Provides a pre-configured DatabaseManager instance with a temporary database
   ```python
   def test_database_operations(db_manager):
       # db_manager is a DatabaseManager instance with a temporary database
       result = db_manager.fetchall("SELECT 1")
       assert result == [(1,)]
   ```

3. `db_with_tables`: Provides a DatabaseManager with all tables initialized
   ```python
   def test_with_tables(db_with_tables):
       # db_with_tables has all tables created and ready to use
       result = db_with_tables.fetchall("SELECT * FROM categories")
       assert result == []
   ```

#### Helper Functions:
- `create_connection_error_db()`: Returns a path that will cause a connection error
  ```python
  def test_connection_error():
      db_path = create_connection_error_db()
      with pytest.raises(ConnectionError):
          DatabaseManager(db_path)
  ```

## Standalone Test Execution
All test files must be executable as standalone scripts. This means:

1. Every test file must import the required modules at the top:
   ```python
   import sys
   import pytest
   ```

2. At the bottom of each test file, include the following to enable standalone execution:
   ```python
   if __name__ == "__main__":
       sys.exit(pytest.main([__file__]))
   ```

This allows each test file to be run directly (e.g., `python -m tests/path/to/test_file.py`) while also working when run through pytest.
