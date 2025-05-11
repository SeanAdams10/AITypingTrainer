"""
Pytest configuration file for the Snippets Library application.

This configures both pytest-qt and pytest-flask to work together properly,
and defines custom markers for categorizing tests.
"""

# import sys
# import pytest
# from _pytest.config import Config
# from _pytest.nodes import Item


# def pytest_configure(config: Config) -> None:
#     """
#     Register custom marks to avoid warnings
#     """
#     config.addinivalue_line("markers", "qt: mark tests that use Qt")
#     config.addinivalue_line("markers", "integration: mark integration tests")


# def pytest_runtest_setup(item: Item) -> None:
#     """
#     Disable Flask plugin for Qt tests to avoid conflicts
#     """
#     # Skip Flask's app fixture patching for Qt tests
#     if item.get_closest_marker('qt') and 'app' in item.fixturenames:
#         for fixture_name in item.fixturenames:
#             if fixture_name == 'app' and 'flask' not in sys.modules:
#                 # This avoids Flask plugin trying to patch Qt's app
#                 item.fixturenames.remove('app')
#                 break
