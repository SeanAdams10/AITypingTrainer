import os
import sys

# Add project root to sys.path to allow direct imports from 'core', 'services', etc.
# This conftest.py is at the project root, so os.path.dirname(__file__) is the root.
project_root_path = os.path.abspath(os.path.dirname(__file__))
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)


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
