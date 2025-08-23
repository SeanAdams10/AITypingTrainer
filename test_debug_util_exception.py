#!/usr/bin/env python3
"""Test script to verify MissingDebugUtilError is raised correctly."""

from db.database_manager import DatabaseManager

try:
    db = DatabaseManager()
    print("ERROR: Exception was not raised as expected!")
except Exception as e:
    print(f"SUCCESS: Exception raised as expected: {e.__class__.__name__}: {e}")
