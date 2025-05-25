"""
Enhanced pytest debugging script
"""
import sys
import pytest

if __name__ == "__main__":
    # Enable pytest to show full tracebacks and verbose output
    sys.exit(pytest.main([
        "tests/models/test_snippet.py::test_create_snippet_with_nonexistent_category",
        "-v", "--no-header", "--showlocals", "--tb=native"
    ]))
