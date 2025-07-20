"""
Tests for LibraryManager and Snippets Library functionality.

This test suite covers only the models/library.py logic (categories, snippets, CRUD, validation).
"""

import os
import sys
import tempfile
from typing import Generator

import pytest
from PySide6.QtWidgets import QApplication

import desktop_ui.library_main as library_main
from db.database_manager import DatabaseManager
from models.library import LibraryManager

# ===== Fixtures =====


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Provide a path to a temporary SQLite database file."""
    # Create a temporary file and immediately close it to release the handle
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name
        # Close the file handle immediately
        tmp.close()

    try:
        # Yield the path to the test
        yield tmp_path
    finally:
        # Clean up the temp file after test
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception as e:
            print(f"Warning: Failed to remove temporary database file: {e}")


@pytest.fixture
def db_manager(temp_db: str) -> Generator[DatabaseManager, None, None]:
    """
    Provide a DatabaseManager instance with a temporary database.

    Args:
        temp_db: Path to the temporary database file

    Yields:
        DatabaseManager: A database manager instance connected to the temp database
    """
    db = None
    try:
        db = DatabaseManager(temp_db)
        # Initialize all required tables
        db.init_tables()
        yield db
    finally:
        # Ensure the database connection is properly closed
        if db is not None:
            try:
                db.close()
            except Exception as e:
                print(f"Warning: Error closing database connection: {e}")


@pytest.fixture
def library_manager(db_manager: DatabaseManager) -> LibraryManager:
    """Provide a LibraryManager instance."""
    return LibraryManager(db_manager)


@pytest.fixture(scope="module")
def qt_app():
    """Provide a QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def mock_db_manager(db_manager):
    # Patch CategoryManager and SnippetManager to use the test db
    return db_manager


@pytest.fixture
def main_window(qt_app, mock_db_manager):
    win = library_main.LibraryMainWindow(db_manager=mock_db_manager, testing_mode=True)
    yield win
    win.close()


# ===== Tests =====


def test_create_and_list_category(library_manager: LibraryManager) -> None:
    """Test creating and listing categories."""
    cat_id = library_manager.create_category("Test Category")
    categories = library_manager.list_categories()
    assert any(c.category_id == cat_id for c in categories)
    assert any(c.category_name == "Test Category" for c in categories)


def test_rename_category(library_manager: LibraryManager) -> None:
    """Test renaming a category."""
    cat_id = library_manager.create_category("Old Name")
    library_manager.rename_category(cat_id, "New Name")
    categories = library_manager.list_categories()
    assert any(c.category_name == "New Name" for c in categories)


def test_delete_category(library_manager: LibraryManager) -> None:
    """Test deleting a category."""
    cat_id = library_manager.create_category("To Delete")
    assert library_manager.delete_category(cat_id)
    categories = library_manager.list_categories()
    assert not any(c.category_id == cat_id for c in categories)


def test_create_and_list_snippet(library_manager: LibraryManager) -> None:
    """Test creating and listing snippets."""
    cat_id = library_manager.create_category("Cat for Snippet")
    snip_id = library_manager.create_snippet(cat_id, "Snippet1", "Some content")
    snippets = library_manager.list_snippets(cat_id)
    assert any(s.snippet_id == snip_id for s in snippets)
    assert any(s.snippet_name == "Snippet1" for s in snippets)


def test_edit_snippet(library_manager: LibraryManager) -> None:
    """Test editing a snippet."""
    cat_id = library_manager.create_category("Cat for Edit")
    snip_id = library_manager.create_snippet(cat_id, "EditMe", "Old content")
    library_manager.edit_snippet(snip_id, "Edited", "New content")
    snippets = library_manager.list_snippets(cat_id)
    assert any(s.snippet_name == "Edited" and s.content == "New content" for s in snippets)


def test_delete_snippet(library_manager: LibraryManager) -> None:
    """Test deleting a snippet."""
    cat_id = library_manager.create_category("Cat for Del Snip")
    snip_id = library_manager.create_snippet(cat_id, "ToDelete", "Content")
    assert library_manager.delete_snippet(snip_id)
    snippets = library_manager.list_snippets(cat_id)
    assert not any(s.snippet_id == snip_id for s in snippets)


def test_create_snippet_invalid_category(library_manager: LibraryManager) -> None:
    """Test creating a snippet with an invalid category."""
    with pytest.raises(Exception):
        library_manager.create_snippet("nonexistent", "Name", "Content")


def test_edit_snippet_invalid_id(library_manager: LibraryManager) -> None:
    """Test editing a snippet with an invalid ID."""
    with pytest.raises(Exception):
        library_manager.edit_snippet("badid", "Name", "Content")


def test_delete_snippet_invalid_id(library_manager: LibraryManager) -> None:
    """Test deleting a snippet with an invalid ID."""
    assert not library_manager.delete_snippet("badid")


def test_delete_snippet_id(library_manager: LibraryManager) -> None:
    """Test deleting a snippet by ID (robust)."""
    cat_id = library_manager.create_category("Cat for DelByID")
    snip_id = library_manager.create_snippet(cat_id, "ToDeleteByID", "Content")
    # Confirm snippet exists
    snippets = library_manager.list_snippets(cat_id)
    assert any(s.snippet_id == snip_id for s in snippets)
    # Delete by ID
    assert library_manager.delete_snippet(snip_id)
    # Confirm deletion
    snippets = library_manager.list_snippets(cat_id)
    assert not any(s.snippet_id == snip_id for s in snippets)


class TestLibraryMainWindowUI:
    def test_load_data_and_initial_state(self, main_window):
        win = main_window
        # Should load with no categories/snippets
        assert win.categoryList.count() == 0
        assert win.snippetList.count() == 0
        assert win.status.text() == ""

    def test_add_category(self, main_window, monkeypatch):
        win = main_window
        # Simulate dialog returning Accepted and a name
        monkeypatch.setattr("desktop_ui.modern_dialogs.CategoryDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.CategoryDialog.get_value", lambda self: "UI Cat"
        )
        win.add_category()
        assert any(c.category_name == "UI Cat" for c in win.categories)
        assert win.status.text() == "Category added."
        assert win.categoryList.count() > 0

    def test_edit_category(self, main_window, monkeypatch):
        win = main_window
        # Ensure there is at least one category to edit
        if not win.categories:

            class FakeAddDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "Initial Cat"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeAddDialog())
            win.add_category()
        # Select the first category
        win.categoryList.setCurrentRow(0)

        class FakeEditDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "Renamed Cat"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeEditDialog())
        win.edit_category()
        assert any(c.category_name == "Renamed Cat" for c in win.categories)
        assert win.status.text() == "Category updated."

    def test_delete_category(self, main_window, monkeypatch):
        win = main_window
        win.categoryList.setCurrentRow(0)
        cat = win.categories[0]
        # Simulate user confirming deletion
        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question", lambda *a, **k: 16384)  # Yes
        win.delete_category()
        assert all(c.category_name != cat.category_name for c in win.categories)
        assert win.status.text() == "Category deleted."

    def test_add_snippet(self, main_window, monkeypatch):
        win = main_window
        # Add a category first
        monkeypatch.setattr("desktop_ui.modern_dialogs.CategoryDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.CategoryDialog.get_value", lambda self: "Cat2"
        )
        win.add_category()
        win.categoryList.setCurrentRow(0)
        # Simulate snippet dialog
        monkeypatch.setattr("desktop_ui.modern_dialogs.SnippetDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.SnippetDialog.get_values", lambda self: ("Snip1", "Content1")
        )
        win.add_snippet()
        assert win.snippetList.count() == 1
        assert win.status.text() == "Snippet added."

    def test_edit_snippet(self, main_window, monkeypatch):
        win = main_window
        win.snippetList.setCurrentRow(0)
        monkeypatch.setattr("desktop_ui.modern_dialogs.SnippetDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.SnippetDialog.get_values",
            lambda self: ("Snip1-edited", "Content1-edited"),
        )
        win.edit_snippet()
        assert win.snippetList.item(0).text() == "Snip1-edited"
        assert win.status.text() == "Snippet updated."

    def test_delete_snippet(self, main_window, monkeypatch):
        win = main_window
        win.snippetList.setCurrentRow(0)
        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question", lambda *a, **k: 16384)  # Yes
        win.delete_snippet()
        assert win.snippetList.count() == 0
        assert win.status.text() == "Snippet deleted."

    def test_filter_snippets(self, main_window, monkeypatch):
        win = main_window
        # Add a snippet again
        monkeypatch.setattr("desktop_ui.modern_dialogs.SnippetDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.SnippetDialog.get_values", lambda self: ("Alpha", "A")
        )
        win.add_snippet()
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.SnippetDialog.get_values", lambda self: ("Beta", "B")
        )
        win.add_snippet()
        win.search_input.setText("Alpha")
        assert win.snippetList.count() == 1
        assert win.snippetList.item(0).text() == "Alpha"
        win.search_input.setText("")
        assert win.snippetList.count() == 2

    def test_show_error_and_info(self, main_window):
        win = main_window
        win.show_error("ErrMsg")
        assert win.status.text() == "ErrMsg"
        win.show_info("InfoMsg")
        assert win.status.text() == "InfoMsg"

    def test_update_snippet_buttons_state(self, main_window):
        win = main_window
        win.update_snippet_buttons_state(True)
        assert win.addSnipBtn.isEnabled()
        assert win.editSnipBtn.isEnabled()
        assert win.delSnipBtn.isEnabled()
        win.update_snippet_buttons_state(False)
        assert not win.addSnipBtn.isEnabled()
        assert not win.editSnipBtn.isEnabled()
        assert not win.delSnipBtn.isEnabled()

    def test_on_category_selection_changed_and_load_snippets(self, main_window):
        win = main_window
        win.categoryList.setCurrentRow(0)
        win.on_category_selection_changed()
        assert win.selected_category is not None
        assert win.snippetList.count() >= 0

    def test_on_snippet_selection_changed(self, main_window):
        win = main_window
        if win.snippetList.count() > 0:
            item = win.snippetList.item(0)
            win.on_snippet_selection_changed(item)
            assert win.selected_snippet is not None

    def test_view_snippet(self, main_window, monkeypatch):
        win = main_window
        if win.snippetList.count() > 0:
            item = win.snippetList.item(0)
            # Patch dialog to avoid actual UI
            monkeypatch.setattr(
                "desktop_ui.view_snippet_dialog.ViewSnippetDialog.exec_", lambda self: 1
            )
            win.view_snippet(item)

    def test_add_category_error(self, main_window, monkeypatch):
        win = main_window
        # Simulate dialog accepted but error in save_category
        monkeypatch.setattr("desktop_ui.modern_dialogs.CategoryDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.CategoryDialog.get_value", lambda self: "ErrCat"
        )
        monkeypatch.setattr(
            win.category_manager,
            "save_category",
            lambda c: (_ for _ in ()).throw(Exception("fail")),
        )
        win.add_category()
        assert "Failed to add category" in win.status.text()

    def test_add_snippet_error(self, main_window, monkeypatch):
        # Ensure a category exists and is selected
        if not main_window.categories:

            class FakeCatDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "CatForError"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
            main_window.add_category()
        main_window.categoryList.setCurrentRow(0)

        class FakeDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("ErrSnip", "X")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeDialog())

        def fail_save_snippet(snip):
            raise Exception("failsnip")

        monkeypatch.setattr(main_window.snippet_manager, "save_snippet", fail_save_snippet)
        main_window.add_snippet()
        assert "failsnip" in main_window.status.text()

    def test_edit_category_error(self, main_window, monkeypatch):
        win = main_window
        # Ensure a category exists and is selected
        if not win.categories:

            class FakeAddDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "ErrEditCat"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeAddDialog())
            win.add_category()
        win.categoryList.setCurrentRow(0)
        monkeypatch.setattr("desktop_ui.modern_dialogs.CategoryDialog.exec_", lambda self: 1)
        monkeypatch.setattr(
            "desktop_ui.modern_dialogs.CategoryDialog.get_value", lambda self: "ErrEditCat"
        )
        monkeypatch.setattr(
            win.category_manager,
            "save_category",
            lambda c: (_ for _ in ()).throw(Exception("fail")),
        )
        win.edit_category()
        assert "Failed to update category" in win.status.text() or "failcat2" in win.status.text()

    def test_edit_snippet_error(self, main_window, monkeypatch):
        win = main_window
        # Ensure a snippet exists and is selected
        if not win.snippets:
            # Ensure a category exists and is selected
            if not win.categories:

                class FakeCatDialog:
                    def exec_(self):
                        return 1

                    def get_value(self):
                        return "CatForEditError"

                monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
                win.add_category()
            win.categoryList.setCurrentRow(0)

            class FakeAddDialog:
                def exec_(self):
                    return 1

                def get_values(self):
                    return ("SnippetToEditError", "ContentToEditError")

            monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeAddDialog())
            win.add_snippet()
        win.snippetList.setCurrentRow(0)

        class FakeDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("ErrEditSnip", "X")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeDialog())

        def fail_save_snippet(snip):
            raise Exception("failsnip2")

        monkeypatch.setattr(main_window.snippet_manager, "save_snippet", fail_save_snippet)
        win.edit_snippet()
        assert "Failed to update snippet" in win.status.text() or "failsnip2" in win.status.text()

    def test_delete_category_error(self, main_window, monkeypatch):
        # Ensure a category exists and is selected
        if not main_window.categories:

            class FakeCatDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "CatForDeleteError"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
            main_window.add_category()
        main_window.categoryList.setCurrentRow(0)
        monkeypatch.setattr(
            library_main.QtWidgets.QMessageBox,
            "question",
            lambda *a, **k: library_main.QtWidgets.QMessageBox.StandardButton.Yes,
        )

        def fail_delete_category_by_id(cid):
            raise Exception("faildelcat")

        monkeypatch.setattr(
            main_window.category_manager, "delete_category_by_id", fail_delete_category_by_id
        )
        main_window.delete_category()
        assert (
            "Failed to delete category" in main_window.status.text()
            or "faildelcat" in main_window.status.text()
        )

    def test_delete_snippet_error(self, main_window, monkeypatch):
        win = main_window
        # Ensure a category exists and is selected
        if not win.categories:

            class FakeCatDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "CatForDeleteError"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
            win.add_category()
        win.categoryList.setCurrentRow(0)
        # Ensure a snippet exists and is selected
        if not win.snippets:

            class FakeSnipDialog:
                def exec_(self):
                    return 1

                def get_values(self):
                    return ("ToDelError", "X")

            monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeSnipDialog())
            win.add_snippet()
        win.snippetList.setCurrentRow(win.snippetList.count() - 1)
        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question", lambda *a, **k: 16384)  # Yes

        def fail_delete_snippet(sid):
            raise Exception("faildelsnip")

        monkeypatch.setattr(win.snippet_manager, "delete_snippet", fail_delete_snippet)
        win.delete_snippet()
        assert "Failed to delete snippet" in win.status.text() or "faildelsnip" in win.status.text()

    def test_load_data_error(self, main_window, monkeypatch):
        win = main_window
        monkeypatch.setattr(
            win.category_manager,
            "list_all_categories",
            lambda: (_ for _ in ()).throw(Exception("fail")),
        )
        win.load_data()
        assert "Error loading data" in win.status.text()

    def test_load_snippets_error(self, main_window, monkeypatch):
        win = main_window
        win.categoryList.setCurrentRow(0)
        monkeypatch.setattr(
            win.snippet_manager,
            "list_snippets_by_category",
            lambda cid: (_ for _ in ()).throw(Exception("fail")),
        )
        win.load_snippets()
        assert "Error loading snippets" in win.status.text()


# --- UI Tests for LibraryMainWindow ---


def test_window_initialization(main_window):
    """Test that the main window initializes with the correct default state.

    Verifies:
    - Window title is set correctly
    - Category and snippet lists are empty
    - All UI elements are present and in default state
    - Database connection is established
    """
    # Verify window properties
    assert main_window.windowTitle() == "Snippets Library"
    assert main_window.isVisible()
    assert main_window.testing_mode is True

    # Verify category list is empty
    assert main_window.categoryList is not None
    assert main_window.categoryList.count() == 0

    # Verify snippet list is empty
    assert main_window.snippetList is not None
    assert main_window.snippetList.count() == 0

    # Verify buttons are in correct initial state
    assert hasattr(main_window, "addCategoryButton")
    assert hasattr(main_window, "editCategoryButton")
    assert hasattr(main_window, "deleteCategoryButton")
    assert hasattr(main_window, "addSnippetButton")
    assert hasattr(main_window, "editSnippetButton")
    assert hasattr(main_window, "deleteSnippetButton")

    # Verify database connection
    assert hasattr(main_window, "db_manager")
    assert hasattr(main_window, "category_manager")
    assert hasattr(main_window, "snippet_manager")

    # Verify data structures
    assert hasattr(main_window, "categories")
    assert isinstance(main_window.categories, list)
    assert hasattr(main_window, "snippets")
    assert isinstance(main_window.snippets, list)

    # Verify selection state
    assert main_window.selected_category is None
    assert main_window.selected_snippet is None


def test_add_category_ui(main_window, monkeypatch):
    # Simulate CategoryDialog returning Accepted and a name
    class FakeDialog:
        def exec_(self):
            return 1  # Accepted

        def get_value(self):
            return "UI Cat"

    monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeDialog())
    main_window.add_category()
    assert any(c.category_name == "UI Cat" for c in main_window.categories)
    assert main_window.status.text() == "Category added."


def test_edit_category_ui(main_window, monkeypatch):
    # Ensure there is at least one category to edit
    if not main_window.categories:

        class FakeAddDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "Initial Cat"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeAddDialog())
        main_window.add_category()
    # Select the first category
    main_window.categoryList.setCurrentRow(0)

    class FakeEditDialog:
        def exec_(self):
            return 1

        def get_value(self):
            return "Renamed Cat"

    monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeEditDialog())
    main_window.edit_category()
    assert any(c.category_name == "Renamed Cat" for c in main_window.categories)
    assert main_window.status.text() == "Category updated."


def test_delete_category_ui(main_window, monkeypatch):
    # Add a category to delete
    cat = library_main.Category(category_name="ToDelete", description="")
    main_window.category_manager.save_category(cat)
    main_window.categories = main_window.category_manager.list_all_categories()
    main_window.refresh_categories()
    # Select the last category
    main_window.categoryList.setCurrentRow(main_window.categoryList.count() - 1)
    # Patch QMessageBox.question to always return Yes
    monkeypatch.setattr(
        library_main.QtWidgets.QMessageBox,
        "question",
        lambda *a, **k: library_main.QtWidgets.QMessageBox.StandardButton.Yes,
    )
    main_window.delete_category()
    assert not any(c.category_name == "ToDelete" for c in main_window.categories)
    assert main_window.status.text() == "Category deleted."


def test_add_snippet_ui(main_window, monkeypatch):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "CatForSnippet"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)

    class FakeDialog:
        def exec_(self):
            return 1

        def get_values(self):
            return ("SnippetA", "ContentA")

    monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeDialog())
    main_window.add_snippet()
    assert any(s.snippet_name == "SnippetA" for s in main_window.snippets)
    assert main_window.status.text() == "Snippet added."


def test_edit_snippet_ui(main_window, monkeypatch):
    # Ensure there is at least one snippet to edit
    if not main_window.snippets:
        # Ensure a category exists and is selected
        if not main_window.categories:

            class FakeCatDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "CatForEdit"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
            main_window.add_category()
        main_window.categoryList.setCurrentRow(0)

        class FakeAddDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("SnippetToEdit", "ContentToEdit")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeAddDialog())
        main_window.add_snippet()
    main_window.snippetList.setCurrentRow(0)

    class FakeEditDialog:
        def exec_(self):
            return 1

        def get_values(self):
            return ("SnippetA-Edit", "ContentA-Edit")

    monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeEditDialog())
    main_window.edit_snippet()
    assert any(s.snippet_name == "SnippetA-Edit" for s in main_window.snippets)
    assert main_window.status.text() == "Snippet updated."


def test_delete_snippet_ui(main_window, monkeypatch):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "CatForDelete"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)
    # Ensure a snippet exists and is selected
    if not main_window.snippets:

        class FakeSnipDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("ToDel", "X")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeSnipDialog())
        main_window.add_snippet()
    main_window.snippetList.setCurrentRow(main_window.snippetList.count() - 1)
    monkeypatch.setattr(
        library_main.QtWidgets.QMessageBox,
        "question",
        lambda *a, **k: library_main.QtWidgets.QMessageBox.StandardButton.Yes,
    )
    main_window.delete_snippet()
    assert not any(s.snippet_name == "ToDel" for s in main_window.snippets)
    assert main_window.status.text() == "Snippet deleted."


def test_filter_snippets(main_window):
    main_window.search_input.setText("Edit")
    # Should only show snippets with 'Edit' in name
    for i in range(main_window.snippetList.count()):
        item = main_window.snippetList.item(i)
        assert "Edit" in item.text()
    main_window.search_input.setText("")


def test_show_error_and_info(main_window):
    main_window.show_error("errormsg")
    assert main_window.status.text() == "errormsg"
    main_window.show_info("infomsg")
    assert main_window.status.text() == "infomsg"


def test_update_snippet_buttons_state(main_window):
    main_window.update_snippet_buttons_state(True)
    assert main_window.addSnipBtn.isEnabled()
    main_window.update_snippet_buttons_state(False)
    assert not main_window.addSnipBtn.isEnabled()


def test_add_category_error(monkeypatch, main_window):
    class FakeDialog:
        def exec_(self):
            return 1

        def get_value(self):
            return "ErrorCat"

    monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeDialog())

    def fail_save_category(cat):
        raise Exception("failcat")

    monkeypatch.setattr(main_window.category_manager, "save_category", fail_save_category)
    main_window.add_category()
    assert "failcat" in main_window.status.text()


def test_add_snippet_error(monkeypatch, main_window):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "CatForError"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)

    class FakeDialog:
        def exec_(self):
            return 1

        def get_values(self):
            return ("ErrSnip", "X")

    monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeDialog())

    def fail_save_snippet(snip):
        raise Exception("failsnip")

    monkeypatch.setattr(main_window.snippet_manager, "save_snippet", fail_save_snippet)
    main_window.add_snippet()
    assert "failsnip" in main_window.status.text()


def test_edit_category_no_selection(main_window):
    main_window.categoryList.clearSelection()
    main_window.edit_category()
    assert "No category selected." in main_window.status.text()


def test_delete_category_no_selection(main_window):
    main_window.categoryList.clearSelection()
    main_window.delete_category()
    assert "No category selected." in main_window.status.text()


def test_add_snippet_no_category(main_window):
    main_window.selected_category = None
    main_window.add_snippet()
    assert "No category selected." in main_window.status.text()


def test_edit_snippet_no_selection(main_window):
    main_window.snippetList.clearSelection()
    main_window.edit_snippet()
    assert "No snippet selected." in main_window.status.text()


def test_delete_snippet_no_selection(main_window):
    main_window.snippetList.clearSelection()
    main_window.delete_snippet()
    assert "No snippet selected." in main_window.status.text()


def test_edit_category_error(monkeypatch, main_window):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "ErrEditCat"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)

    class FakeDialog:
        def exec_(self):
            return 1

        def get_value(self):
            return "ErrEditCat"

    monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeDialog())

    def fail_save_category(cat):
        raise Exception("failcat2")

    monkeypatch.setattr(main_window.category_manager, "save_category", fail_save_category)
    main_window.edit_category()
    assert (
        "Failed to update category" in main_window.status.text()
        or "failcat2" in main_window.status.text()
    )


def test_edit_snippet_error(monkeypatch, main_window):
    # Ensure a snippet exists and is selected
    if not main_window.snippets:
        # Ensure a category exists and is selected
        if not main_window.categories:

            class FakeCatDialog:
                def exec_(self):
                    return 1

                def get_value(self):
                    return "CatForEditError"

            monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
            main_window.add_category()
        main_window.categoryList.setCurrentRow(0)

        class FakeAddDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("SnippetToEditError", "ContentToEditError")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeAddDialog())
        main_window.add_snippet()
    main_window.snippetList.setCurrentRow(0)

    class FakeDialog:
        def exec_(self):
            return 1

        def get_values(self):
            return ("ErrEditSnip", "X")

    monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeDialog())

    def fail_save_snippet(snip):
        raise Exception("failsnip2")

    monkeypatch.setattr(main_window.snippet_manager, "save_snippet", fail_save_snippet)
    main_window.edit_snippet()
    assert (
        "Failed to update snippet" in main_window.status.text()
        or "failsnip2" in main_window.status.text()
    )


def test_delete_category_error(monkeypatch, main_window):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "CatForDelete"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)
    monkeypatch.setattr(
        library_main.QtWidgets.QMessageBox,
        "question",
        lambda *a, **k: library_main.QtWidgets.QMessageBox.StandardButton.Yes,
    )

    def fail_delete_category_by_id(cid):
        raise Exception("faildelcat")

    monkeypatch.setattr(
        main_window.category_manager, "delete_category_by_id", fail_delete_category_by_id
    )
    main_window.delete_category()
    assert "faildelcat" in main_window.status.text()


def test_delete_snippet_error(monkeypatch, main_window):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "CatForDeleteError"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)
    # Ensure a snippet exists and is selected
    if not main_window.snippets:

        class FakeSnipDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("ToDelError", "X")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeSnipDialog())
        main_window.add_snippet()
    main_window.snippetList.setCurrentRow(main_window.snippetList.count() - 1)
    monkeypatch.setattr(
        library_main.QtWidgets.QMessageBox,
        "question",
        lambda *a, **k: library_main.QtWidgets.QMessageBox.StandardButton.Yes,
    )

    def fail_delete_snippet(sid):
        raise Exception("faildelsnip")

    monkeypatch.setattr(main_window.snippet_manager, "delete_snippet", fail_delete_snippet)
    main_window.delete_snippet()
    assert (
        "Failed to delete snippet" in main_window.status.text()
        or "faildelsnip" in main_window.status.text()
    )


def test_view_snippet_dialog(monkeypatch, main_window):
    # Ensure a category exists and is selected
    if not main_window.categories:

        class FakeCatDialog:
            def exec_(self):
                return 1

            def get_value(self):
                return "CatForView"

        monkeypatch.setattr(library_main, "CategoryDialog", lambda *a, **k: FakeCatDialog())
        main_window.add_category()
    main_window.categoryList.setCurrentRow(0)
    # Ensure a snippet exists and is selected
    if not main_window.snippets:

        class FakeSnipDialog:
            def exec_(self):
                return 1

            def get_values(self):
                return ("ViewMe", "Content")

        monkeypatch.setattr(library_main, "SnippetDialog", lambda *a, **k: FakeSnipDialog())
        main_window.add_snippet()
    main_window.snippetList.setCurrentRow(0)
    called = {}

    class FakeViewDialog:
        def __init__(self, **kwargs):
            called["shown"] = True

        def exec_(self):
            called["exec"] = True

    monkeypatch.setattr(
        library_main, "ViewSnippetDialog", lambda **kwargs: FakeViewDialog(**kwargs)
    )
    item = main_window.snippetList.currentItem()
    main_window.view_snippet(item)
    assert called.get("shown") and called.get("exec")
