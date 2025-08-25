"""Script to debug tests in test_snippet.py with improved error reporting."""
import sys

import pytest

# Run specific tests with detailed error output
tests = [
    "test_create_snippet_with_nonexistent_category",
    "test_snippet_manager_handles_db_errors_gracefully_on_create",
    "test_snippet_manager_handles_db_errors_gracefully_on_delete"
]

if __name__ == "__main__":
    print("Running specific tests from test_snippet.py with detailed error reporting")
    exit_code = pytest.main([f"tests/models/test_snippet.py::{tests[0]}", "-vv"])
    print(f"\nTest exit code: {exit_code}")
    sys.exit(exit_code)
