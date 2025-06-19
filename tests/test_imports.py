"""Test file to verify imports and test environment."""

def test_imports():
    """Test that all required imports work."""
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from models.category import Category
        from db.database_manager import DatabaseManager
        from desktop_ui.library_main import LibraryMainWindow
        from desktop_ui.modern_dialogs import CategoryDialog
        assert True, "All imports successful"
    except ImportError as e:
        assert False, f"Import error: {e}"
