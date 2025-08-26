"""Debug script to run specific tests from test_snippet_manager.py and get detailed output."""

import sys

import pytest

if __name__ == "__main__":
    # Run the tests with detailed error reporting
    # Run a specific test that might be failing
    test_path = (
        "tests/models/test_snippet_manager.py::TestCreateSnippet::"
        "test_create_snippet_pydantic_validation_errors"
    )
    print(f"\nRunning test: {test_path}\n")
    exit_code = pytest.main([test_path, "-vv"])

    print(f"\nTest result: {'PASSED' if exit_code == 0 else f'FAILED with code {exit_code}'}")
    sys.exit(exit_code)
