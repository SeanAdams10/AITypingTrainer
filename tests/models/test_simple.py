"""
Simple test file to verify pytest discovery.
"""

def test_simple():
    """A simple test that should always pass."""
    assert 1 + 1 == 2

if __name__ == "__main__":
    import sys

    import pytest
    sys.exit(pytest.main(["-v", "-s", __file__]))
