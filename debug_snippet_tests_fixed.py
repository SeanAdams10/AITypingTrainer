"""
Script to debug specific tests in test_snippet.py with detailed error reporting
"""
import sys
import traceback
import pytest

# Function to run a specific test with detailed error output
def run_test(test_path):
    print(f"\n=== Running test: {test_path} ===")
    try:
        result = pytest.main([test_path, "-v"])
        if result != 0:
            print(f"Test failed with exit code: {result}")
    except Exception as e:
        print(f"Exception occurred: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    # Test specific test cases one by one
    tests = [
        "tests/models/test_snippet.py::test_create_snippet_with_nonexistent_category",
        "tests/models/test_snippet.py::test_snippet_manager_handles_db_errors_gracefully_on_create",
        "tests/models/test_snippet.py::test_snippet_manager_handles_db_errors_gracefully_on_delete"
    ]
    
    for test in tests:
        run_test(test)
    
    sys.exit(0)  # Exit with success to ensure we see all output
