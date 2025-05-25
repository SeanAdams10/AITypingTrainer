"""
Script to debug specific tests in test_snippet.py
"""
import sys
import pytest

if __name__ == "__main__":
    # Run with -v for verbose output
    exit_code = pytest.main(["tests/models/test_snippet.py::test_create_snippet_with_nonexistent_category", "-v"])
    sys.exit(exit_code)
