"""
Tests for the Library Manager UI module.

This module tests the functionality of the library_manager.py module,
ensuring that the UI components work correctly with the database.
"""
import os
import sys
import pytest
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch
import sqlite3
from pathlib import Path
import tempfile
import shutil

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import modules to be tested
from library_manager import LibraryManagerUI, open_library_manager
from db.database_manager import DatabaseManager

# Skip tests if running in a headless environment
pytestmark = pytest.mark.skipif(
    "DISPLAY" not in os.environ and os.name != "nt",
    reason="Tests require a display"
)

@pytest.fixture
def setup_test_db(tmp_path):
    """
    Create a temporary database for testing.
    
    Args:
        tmp_path: pytest fixture that provides a temporary directory
        
    Returns:
        Path to the temporary database
    """
    # Create a temporary database path
    db_path = tmp_path / "test_library.db"
    
    # Create the test database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Create snippets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS snippets (
            snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            snippet_name TEXT NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories (category_id)
        )
    """)
    
    # Add some test data
    cursor.execute("INSERT INTO categories (category_name) VALUES (?)", ("Test Category 1",))
    cursor.execute("INSERT INTO categories (category_name) VALUES (?)", ("Test Category 2",))
    
    cursor.execute(
        "INSERT INTO snippets (category_id, snippet_name, text) VALUES (?, ?, ?)",
        (1, "Test Snippet 1", "This is test snippet 1 content.")
    )
    cursor.execute(
        "INSERT INTO snippets (category_id, snippet_name, text) VALUES (?, ?, ?)",
        (1, "Test Snippet 2", "This is test snippet 2 content.")
    )
    cursor.execute(
        "INSERT INTO snippets (category_id, snippet_name, text) VALUES (?, ?, ?)",
        (2, "Test Snippet 3", "This is test snippet 3 content.")
    )
    
    conn.commit()
    conn.close()
    
    # Patch the DatabaseManager to use our test database
    original_get_instance = DatabaseManager.get_instance
    
    def patched_get_instance(*args, **kwargs):
        instance = original_get_instance()
        instance.db_path = str(db_path)
        return instance
    
    with patch.object(DatabaseManager, 'get_instance', patched_get_instance):
        yield str(db_path)
    
    # Cleanup (already handled by tmp_path fixture, but we can be explicit)
    if db_path.exists():
        os.remove(db_path)


class MockToplevel:
    """Mock Toplevel window for testing."""
    
    def __init__(self, master=None, **kw):
        self.title_text = ""
        self.geometry_text = ""
        self.protocol_handlers = {}
        self.destroyed = False
        self.focus_set_called = False
        self.resizable_called = False
    
    def title(self, title_text):
        self.title_text = title_text
    
    def geometry(self, geometry_text):
        self.geometry_text = geometry_text
    
    def resizable(self, width, height):
        self.resizable_called = True
    
    def protocol(self, name, func):
        self.protocol_handlers[name] = func
    
    def destroy(self):
        self.destroyed = True
    
    def focus_set(self):
        self.focus_set_called = True
    
    def iconbitmap(self, path):
        pass
    
    def withdraw(self):
        pass


class MockTreeview:
    """Mock Treeview widget for testing."""
    
    def __init__(self, master=None, **kw):
        self.items = {}
        self.selected_items = []
        self.column_configs = {}
        self.heading_configs = {}
        self.yscrollcommand = None
    
    def insert(self, parent, index, iid=None, **kw):
        self.items[iid] = kw
        return iid
    
    def delete(self, *items):
        for item in items:
            if item in self.items:
                del self.items[item]
    
    def selection(self):
        return self.selected_items
    
    def selection_set(self, item):
        self.selected_items = [item]
    
    def item(self, item, **kw):
        if 'values' in kw:
            self.items[item] = {'values': kw['values']}
        return self.items.get(item, {'values': []})
    
    def get_children(self):
        return list(self.items.keys())
    
    def column(self, column, **kw):
        self.column_configs[column] = kw
    
    def heading(self, column, **kw):
        self.heading_configs[column] = kw
    
    def configure(self, **kw):
        if 'yscrollcommand' in kw:
            self.yscrollcommand = kw['yscrollcommand']
    
    def see(self, item):
        pass


class MockButton:
    """Mock Button widget for testing."""
    
    def __init__(self, master=None, **kw):
        self.text = kw.get('text', '')
        self.command = kw.get('command', None)
        self.state = tk.NORMAL
        self.packed = False
        self.grid_info = {}
    
    def pack(self, **kw):
        self.packed = True
    
    def grid(self, **kw):
        self.grid_info = kw
    
    def config(self, **kw):
        if 'state' in kw:
            self.state = kw['state']


class MockEntry:
    """Mock Entry widget for testing."""
    
    def __init__(self, master=None, **kw):
        self.textvariable = kw.get('textvariable', None)
        self.focus_set_called = False
        self.select_range_called = False
    
    def focus_set(self):
        self.focus_set_called = True
    
    def select_range(self, start, end):
        self.select_range_called = True
    
    def grid(self, **kw):
        pass


class MockText:
    """Mock Text widget for testing."""
    
    def __init__(self, master=None, **kw):
        self.content = ""
        self.config_options = {}
        self.grid_info = {}
    
    def insert(self, index, text):
        self.content = text
    
    def get(self, start, end):
        return self.content
    
    def delete(self, start, end):
        self.content = ""
    
    def config(self, **kw):
        self.config_options.update(kw)
    
    def configure(self, **kw):
        self.config_options.update(kw)
    
    def grid(self, **kw):
        self.grid_info = kw


class MockFrame:
    """Mock Frame widget for testing."""
    
    def __init__(self, master=None, **kw):
        self.master = master
        self.config_options = {}
        self.pack_info = {}
        self.grid_info = {}
        self.children = []
    
    def pack(self, **kw):
        self.pack_info = kw
    
    def grid(self, **kw):
        self.grid_info = kw
    
    def config(self, **kw):
        self.config_options.update(kw)
    
    def configure(self, **kw):
        self.config_options.update(kw)


class MockPanedWindow:
    """Mock PanedWindow widget for testing."""
    
    def __init__(self, master=None, **kw):
        self.master = master
        self.orient = kw.get('orient', tk.HORIZONTAL)
        self.panes = []
        self.pack_info = {}
    
    def add(self, widget, **kw):
        self.panes.append((widget, kw))
    
    def pack(self, **kw):
        self.pack_info = kw


class MockLabelFrame(MockFrame):
    """Mock LabelFrame widget for testing."""
    
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.text = kw.get('text', '')


@pytest.fixture
def mock_tk_widgets(monkeypatch):
    """Mock various tkinter widgets for testing."""
    # Create mock widgets
    mock_toplevel = MockToplevel
    mock_treeview = MockTreeview
    mock_button = MockButton
    mock_entry = MockEntry
    mock_text = MockText
    mock_frame = MockFrame
    mock_labelframe = MockLabelFrame
    mock_panedwindow = MockPanedWindow
    
    # Create mock string variable
    mock_stringvar = MagicMock()
    mock_stringvar_instance = MagicMock()
    mock_stringvar.return_value = mock_stringvar_instance
    mock_stringvar_instance.get.return_value = "Test Value"
    mock_stringvar_instance.set = MagicMock()
    
    # Create mock style
    mock_style = MagicMock()
    
    # Create mock scrollbar
    mock_scrollbar = MagicMock()
    
    # Create mock messagebox functions
    mock_showerror = MagicMock()
    mock_askyesno = MagicMock()
    mock_askyesno.return_value = True
    
    # Patch all required tkinter classes and functions
    monkeypatch.setattr('tkinter.Toplevel', mock_toplevel)
    monkeypatch.setattr('tkinter.ttk.Treeview', mock_treeview)
    monkeypatch.setattr('tkinter.ttk.Button', mock_button)
    monkeypatch.setattr('tkinter.ttk.Entry', mock_entry)
    monkeypatch.setattr('tkinter.Text', mock_text)
    monkeypatch.setattr('tkinter.StringVar', mock_stringvar)
    monkeypatch.setattr('tkinter.ttk.Style', lambda: mock_style)
    monkeypatch.setattr('tkinter.ttk.Scrollbar', lambda *args, **kwargs: mock_scrollbar)
    monkeypatch.setattr('tkinter.ttk.Frame', mock_frame)
    monkeypatch.setattr('tkinter.ttk.LabelFrame', mock_labelframe)
    monkeypatch.setattr('tkinter.ttk.Label', MagicMock())
    monkeypatch.setattr('tkinter.ttk.PanedWindow', mock_panedwindow)
    monkeypatch.setattr('tkinter.messagebox.showerror', mock_showerror)
    monkeypatch.setattr('tkinter.messagebox.askyesno', mock_askyesno)
    monkeypatch.setattr('tkinter.filedialog.askopenfilename', MagicMock(return_value="test_file.txt"))
    
    return {
        'toplevel': mock_toplevel,
        'treeview': mock_treeview,
        'button': mock_button,
        'entry': mock_entry,
        'text': mock_text,
        'stringvar': mock_stringvar,
        'style': mock_style,
        'scrollbar': mock_scrollbar,
        'showerror': mock_showerror,
        'askyesno': mock_askyesno
    }


class TestLibraryManagerUI:
    """Test cases for the LibraryManagerUI class."""
    
    def test_init(self, setup_test_db, mock_tk_widgets):
        """Test initialization of the LibraryManagerUI."""
        # Create a mock callback
        on_close_callback = MagicMock()
        
        # Create a mock root
        root = MockToplevel()
        
        # Initialize the UI
        ui = LibraryManagerUI(root, on_close_callback)
        
        # Check that the UI was properly initialized
        assert ui.root == root
        assert ui.on_close_callback == on_close_callback
        assert ui.selected_category_id is None
        assert ui.selected_snippet_id is None
        
        # Verify window title
        assert root.title_text == "Library Management - AI Typing Trainer"
        assert root.geometry_text == "900x600"
        assert root.resizable_called is True
    
    def test_on_category_select(self, setup_test_db, mock_tk_widgets):
        """Test handling category selection events."""
        # Create a mock root
        root = MockToplevel()
        
        # Initialize the UI
        ui = LibraryManagerUI(root, MagicMock())
        
        # Create mock buttons
        ui.rename_cat_btn = MockButton()
        ui.add_snippet_btn = MockButton()
        
        # Replace the treeview with our mock
        ui.cat_tree = MockTreeview()
        
        # Mock load_snippets method
        original_load_snippets = ui.load_snippets
        ui.load_snippets = MagicMock()
        
        # Test with no selection
        ui.cat_tree.selected_items = []
        ui.on_category_select(None)
        assert ui.selected_category_id is None
        assert ui.rename_cat_btn.state == tk.DISABLED
        assert ui.add_snippet_btn.state == tk.DISABLED
        
        # Test with a selection
        ui.cat_tree.selected_items = ["1"]
        ui.on_category_select(None)
        assert ui.selected_category_id == 1
        assert ui.rename_cat_btn.state == tk.NORMAL
        assert ui.add_snippet_btn.state == tk.NORMAL
        ui.load_snippets.assert_called_once_with(1)
        
        # Restore original method
        ui.load_snippets = original_load_snippets
    
    def test_on_snippet_select(self, setup_test_db, mock_tk_widgets):
        """Test handling snippet selection events."""
        # Create a mock root
        root = MockToplevel()
        
        # Initialize the UI
        ui = LibraryManagerUI(root, MagicMock())
        
        # Create mock buttons
        ui.view_snippet_btn = MockButton()
        ui.edit_snippet_btn = MockButton()
        ui.delete_snippet_btn = MockButton()
        
        # Replace the treeview with our mock
        ui.snippet_tree = MockTreeview()
        
        # Test with no selection
        ui.snippet_tree.selected_items = []
        ui.on_snippet_select(None)
        assert ui.selected_snippet_id is None
        assert ui.view_snippet_btn.state == tk.DISABLED
        assert ui.edit_snippet_btn.state == tk.DISABLED
        assert ui.delete_snippet_btn.state == tk.DISABLED
        
        # Test with a selection
        ui.snippet_tree.selected_items = ["1"]
        ui.on_snippet_select(None)
        assert ui.selected_snippet_id == 1
        assert ui.view_snippet_btn.state == tk.NORMAL
        assert ui.edit_snippet_btn.state == tk.NORMAL
        assert ui.delete_snippet_btn.state == tk.NORMAL
    
    def test_on_window_close(self, setup_test_db, mock_tk_widgets):
        """Test handling window close events."""
        # Create a mock callback
        on_close_callback = MagicMock()
        
        # Create a mock root
        root = MockToplevel()
        
        # Initialize the UI
        ui = LibraryManagerUI(root, on_close_callback)
        
        # Call the method
        ui.on_window_close()
        
        # Verify that destroy was called on the root
        assert root.destroyed is True
        
        # Verify that the callback was called
        on_close_callback.assert_called_once()
        
    def test_load_categories_with_db(self, setup_test_db, mock_tk_widgets):
        """Test loading categories with a real database connection."""
        # Create a mock root
        root = MockToplevel()
        
        # Initialize the UI
        ui = LibraryManagerUI(root, MagicMock())
        
        # Replace the treeview with our mock
        ui.cat_tree = MockTreeview()
        
        # Call the method
        ui.load_categories()
        
        # We should have 2 categories from our test data
        assert len(ui.cat_tree.items) == 2
        
        # Verify category IDs
        assert "1" in ui.cat_tree.items
        assert "2" in ui.cat_tree.items
    
    def test_load_snippets_with_db(self, setup_test_db, mock_tk_widgets):
        """Test loading snippets with a real database connection."""
        # Create a mock root
        root = MockToplevel()
        
        # Initialize the UI
        ui = LibraryManagerUI(root, MagicMock())
        
        # Replace the treeview with our mock
        ui.snippet_tree = MockTreeview()
        
        # Call the method with category ID 1
        ui.load_snippets(1)
        
        # We should have 2 snippets for category 1
        assert len(ui.snippet_tree.items) == 2
        
        # Verify snippet IDs
        assert "1" in ui.snippet_tree.items
        assert "2" in ui.snippet_tree.items
        
        # Test with category ID 2
        ui.snippet_tree = MockTreeview()  # Reset treeview
        ui.load_snippets(2)
        
        # We should have 1 snippet for category 2
        assert len(ui.snippet_tree.items) == 1
        assert "3" in ui.snippet_tree.items
