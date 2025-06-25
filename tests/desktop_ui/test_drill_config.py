"""
Tests for the DrillConfigDialog in the desktop UI.
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Generator, List
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Add project root to Python path to enable imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now we can import project modules
from db.database_manager import DatabaseManager
from desktop_ui.drill_config import DrillConfigDialog
from models.category import Category
from models.category_manager import CategoryManager
from models.keyboard import Keyboard
from models.keyboard_manager import KeyboardManager
from models.snippet import Snippet
from models.snippet_manager import SnippetManager
from models.user import User
from models.user_manager import UserManager


@pytest.fixture(scope="module")
def qtapp() -> QApplication:
    """Fixture to create a QApplication instance.
    Using qtapp name to avoid conflicts with pytest-flask.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app


class QtBot:
    """Simple QtBot class to replace pytest-qt's qtbot when it's not available."""
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.widgets: List[object] = []
        
    def addWidget(self, widget: object) -> object:
        """Keep track of widgets to ensure they don't get garbage collected."""
        self.widgets.append(widget)
        return widget
        
    def mouseClick(self, widget: object, button: Qt.MouseButton = Qt.MouseButton.LeftButton, pos: object = None) -> None:
        """Simulate mouse click."""
        if pos is None and hasattr(widget, 'rect'):
            pos = widget.rect().center()  # type: ignore
        # Here we would normally use QTest.mouseClick, but for our tests
        # we can just directly call the click handler if available
        if hasattr(widget, 'click'):
            widget.click()  # type: ignore
        # Process events to make sure UI updates
        self.app.processEvents()
    
    def waitUntil(self, callback: object, timeout: int = 1000) -> object:
        """Wait until the callback returns True or timeout."""
        # Simpler version, just call the callback directly since our tests are synchronous
        return callback()  # type: ignore
        
    def wait(self, ms: int) -> None:
        """Wait for the specified number of milliseconds."""
        # Process events to make any pending UI updates happen
        self.app.processEvents()


@pytest.fixture
def qtbot(qtapp: QApplication) -> QtBot:
    """Create a QtBot instance for testing when pytest-qt's qtbot isn't available."""
    return QtBot(qtapp)


@pytest.fixture(scope="session")
def session_temp_db() -> Generator[str, None, None]:
    """Create a session-scoped temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        temp_db_path = tmp_file.name
    yield temp_db_path
    # Clean up
    if os.path.exists(temp_db_path):
        try:
            os.unlink(temp_db_path)
        except PermissionError:
            # If we can't delete it now, leave it for OS cleanup
            pass


@pytest.fixture
def temp_db(session_temp_db: str) -> Generator[str, None, None]:
    """Create a fresh database for each test by copying session db."""
    # Create a unique temporary file for this test
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Initialize fresh database
    manager = DatabaseManager(test_db_path)
    manager.init_tables()
    manager.close()
    
    yield test_db_path
    
    # Clean up
    if os.path.exists(test_db_path):
        try:
            os.unlink(test_db_path)
        except PermissionError:
            # If we can't delete it now, leave it for OS cleanup
            pass


@pytest.fixture
def db_manager(temp_db: str) -> Generator[DatabaseManager, None, None]:
    """Create a DatabaseManager with a temporary database."""
    manager = DatabaseManager(temp_db)
    yield manager
    # Ensure the database connection is closed before temp file cleanup
    try:
        manager.close()
    except Exception:
        pass  # Ignore errors during cleanup


@pytest.fixture
def dialog_factory(qtapp: QApplication, qtbot: QtBot) -> Generator[object, None, None]:
    """Factory to create DrillConfigDialog instances with proper cleanup."""
    dialogs = []
    
    def create_dialog(db_manager: DatabaseManager, user_id: str, keyboard_id: str) -> DrillConfigDialog:
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=user_id,
            keyboard_id=keyboard_id
        )
        qtbot.addWidget(dialog)
        dialogs.append(dialog)
        return dialog
    
    yield create_dialog
    
    # Clean up all dialogs
    for dialog in dialogs:
        try:
            if hasattr(dialog, 'close'):
                dialog.close()
            if hasattr(dialog, 'db_manager') and dialog.db_manager:
                try:
                    dialog.db_manager.close()
                except Exception:
                    pass
        except Exception:
            pass


@pytest.fixture
def test_user(db_manager: DatabaseManager) -> User:
    """Create a test user in the database."""
    user_manager = UserManager(db_manager)
    user = User(
        user_id="12345678-1234-1234-1234-123456789abc",
        first_name="Test",
        surname="User",
        email_address="test@example.com"
    )
    user_manager.save_user(user)
    # Ensure the user_id is properly set
    assert user.user_id is not None
    return user


@pytest.fixture
def test_keyboard(db_manager: DatabaseManager, test_user: User) -> Keyboard:
    """Create a test keyboard in the database."""
    keyboard_manager = KeyboardManager(db_manager)
    # Assert that user_id is not None before using it
    assert test_user.user_id is not None
    keyboard = Keyboard(
        keyboard_id="87654321-4321-4321-4321-9876543210ef",
        user_id=test_user.user_id,
        keyboard_name="Test QWERTY Keyboard"
    )
    keyboard_manager.save_keyboard(keyboard)
    # Ensure the keyboard_id is properly set
    assert keyboard.keyboard_id is not None
    return keyboard


@pytest.fixture
def test_categories(db_manager: DatabaseManager) -> List[Category]:
    """Create test categories in the database."""
    category_manager = CategoryManager(db_manager)
    categories = [
        Category(
            category_id="11111111-1111-1111-1111-111111111111",
            category_name="Programming",
            description="Programming code snippets"
        ),
        Category(
            category_id="22222222-2222-2222-2222-222222222222", 
            category_name="Literature",
            description="Classic literature excerpts"
        ),
        Category(
            category_id="33333333-3333-3333-3333-333333333333",
            category_name="Technical",
            description="Technical documentation"
        )    ]
    for category in categories:
        category_manager.save_category(category)
        # Ensure category_id is properly set
        assert category.category_id is not None
    return categories


@pytest.fixture
def test_snippets(db_manager: DatabaseManager, test_categories: List[Category]) -> List[Snippet]:
    """Create test snippets in the database."""
    snippet_manager = SnippetManager(db_manager)
    # Assert that category IDs are not None before using them
    assert test_categories[0].category_id is not None
    assert test_categories[1].category_id is not None
    assert test_categories[2].category_id is not None
    
    snippets = [
        Snippet(
            snippet_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            category_id=test_categories[0].category_id,
            snippet_name="Hello World Python",
            content='print("Hello, World!")\n# This is a simple Python program\nfor i in range(5):\n    print(f"Number: {i}")',
            description="Basic Python hello world with loop"
        ),
        Snippet(
            snippet_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            category_id=test_categories[0].category_id,
            snippet_name="JavaScript Function",
            content='function greetUser(name) {\n    return `Hello, ${name}!`;\n}\n\nconst user = "Alice";\nconsole.log(greetUser(user));',
            description="Simple JavaScript function"
        ),
        Snippet(
            snippet_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
            category_id=test_categories[1].category_id,
            snippet_name="Shakespeare Quote",
            content="To be, or not to be, that is the question:\nWhether 'tis nobler in the mind to suffer\nThe slings and arrows of outrageous fortune,\nOr to take arms against a sea of troubles\nAnd, by opposing, end them.",
            description="Famous Hamlet soliloquy"
        ),
        Snippet(
            snippet_id="dddddddd-dddd-dddd-dddd-dddddddddddd",
            category_id=test_categories[2].category_id,
            snippet_name="API Documentation",
            content="GET /api/users/{id}\n\nReturns user information for the specified ID.\n\nParameters:\n- id (string): The unique identifier for the user\n\nResponse:\n200 OK - User found\n404 Not Found - User does not exist",
            description="REST API endpoint documentation"
        )
    ]
    for snippet in snippets:
        snippet_manager.save_snippet(snippet)
        # Ensure snippet_id is properly set
        assert snippet.snippet_id is not None
    return snippets


# Test parameter sets for comprehensive testing
DRILL_CONFIG_TEST_CASES = [
    # (category_name, snippet_name, start_index, end_index, expected_length, test_description)
    ("Programming", "Hello World Python", 0, 50, 50, "Programming category, first snippet, start range"),
    ("Programming", "JavaScript Function", 10, 80, 70, "Programming category, second snippet, middle range"),
    ("Literature", "Shakespeare Quote", 0, 100, 100, "Literature category, full range"),
    ("Technical", "API Documentation", 5, 150, 145, "Technical category, large range"),
]

INVALID_RANGE_TEST_CASES = [
    # (start_index, end_index, expected_error_type, test_description)
    (50, 40, "end_less_than_start", "End index less than start index"),
    (-1, 50, "negative_start", "Negative start index"),
    (0, 0, "zero_length", "Zero length range"),
]


class TestDrillConfigDialog:
    """Test cases for the DrillConfigDialog functionality."""
    
    def test_dialog_initialization(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test that the dialog initializes correctly with database data."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Check basic UI initialization
        assert dialog.windowTitle() == "Configure Typing Drill"
        assert dialog.user_id == test_user.user_id
        assert dialog.keyboard_id == test_keyboard.keyboard_id
        
        # Check that categories are loaded
        assert dialog.category_selector.count() == len(test_categories)
        
        # Check that UI components exist
        assert hasattr(dialog, 'category_selector')
        assert hasattr(dialog, 'snippet_selector')
        assert hasattr(dialog, 'start_index')
        assert hasattr(dialog, 'end_index')
        assert hasattr(dialog, 'snippet_preview')
        assert hasattr(dialog, 'start_button')
        
        # Verify user and keyboard are loaded correctly
        assert dialog.current_user is not None
        assert dialog.current_user.user_id == test_user.user_id
        assert dialog.current_keyboard is not None
        assert dialog.current_keyboard.keyboard_id == test_keyboard.keyboard_id
    
    def test_category_loading(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test that categories are loaded correctly from the database."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Check that all categories are loaded
        assert dialog.category_selector.count() == len(test_categories)
          # Verify category names match
        category_names = [dialog.category_selector.itemText(i) for i in range(dialog.category_selector.count())]
        expected_names = [cat.category_name for cat in test_categories]
        assert set(category_names) == set(expected_names)
        
        # Check that category data is properly stored
        for i in range(dialog.category_selector.count()):
            category_data = dialog.category_selector.itemData(i)
            assert isinstance(category_data, Category)
            assert category_data.category_name in expected_names
    
    @pytest.mark.parametrize("category_name,expected_snippet_count", [
        ("Programming", 2),  # Programming category has 2 snippets
        ("Literature", 1),   # Literature category has 1 snippet
        ("Technical", 1),    # Technical category has 1 snippet
    ])
    def test_category_selection_loads_snippets(self, qtapp, qtbot, db_manager, test_user, test_keyboard, 
                                               test_categories, test_snippets, category_name, expected_snippet_count):
        """Test that selecting a category loads the correct snippets."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Find the category by name
        category_index = -1
        for i in range(dialog.category_selector.count()):
            if dialog.category_selector.itemText(i) == category_name:
                category_index = i
                break
        
        assert category_index != -1, f"Category '{category_name}' not found in selector"
        
        # Select the category
        dialog.category_selector.setCurrentIndex(category_index)
        dialog._on_category_changed(category_index)
          # Check that correct number of snippets are loaded
        assert dialog.snippet_selector.count() == expected_snippet_count
        
        # Verify snippets belong to the selected category
        selected_category = dialog.category_selector.itemData(category_index)
        for i in range(dialog.snippet_selector.count()):
            snippet_data = dialog.snippet_selector.itemData(i)
            assert isinstance(snippet_data, Snippet)
            assert snippet_data.category_id == selected_category.category_id
    
    @pytest.mark.parametrize("category_name,snippet_name,start_index,end_index,expected_length,test_description", DRILL_CONFIG_TEST_CASES)
    def test_snippet_range_configuration(self, qtapp, qtbot, db_manager, test_user, test_keyboard,
                                         test_categories, test_snippets, category_name, snippet_name,
                                         start_index, end_index, expected_length, test_description):
        """Test configuring snippet ranges with various parameters."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Find the category by name
        category_index = -1
        for i in range(dialog.category_selector.count()):
            if dialog.category_selector.itemText(i) == category_name:
                category_index = i
                break
        
        assert category_index != -1, f"Category '{category_name}' not found in selector"
        
        # Select category and load snippets
        dialog.category_selector.setCurrentIndex(category_index)
        dialog._on_category_changed(category_index)
        
        # Find the snippet by name
        snippet_index = -1
        for i in range(dialog.snippet_selector.count()):
            if dialog.snippet_selector.itemText(i) == snippet_name:
                snippet_index = i
                break
        
        assert snippet_index != -1, f"Snippet '{snippet_name}' not found in selector for category '{category_name}'"
        
        # Select snippet
        dialog.snippet_selector.setCurrentIndex(snippet_index)
        dialog._on_snippet_changed()
        
        # Set range values
        dialog.start_index.setValue(start_index)
        dialog.end_index.setValue(end_index)
        
        # Update preview
        dialog._update_preview()
        
        # Verify preview content length
        preview_text = dialog.snippet_preview.toPlainText()
        actual_length = len(preview_text)
        
        # The actual length might be different if end_index exceeds content length
        snippet_data = dialog.snippet_selector.itemData(snippet_index)
        max_end = min(end_index, len(snippet_data.content))
        expected_actual_length = max_end - start_index
        
        assert actual_length == expected_actual_length, f"Test case: {test_description}"
        
        # Verify preview content matches the expected slice
        expected_content = snippet_data.content[start_index:max_end]
        assert preview_text == expected_content
    
    def test_start_index_change_updates_end_minimum(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test that changing start index updates the minimum value for end index."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Select a category and snippet
        dialog.category_selector.setCurrentIndex(0)
        dialog._on_category_changed(0)
        dialog.snippet_selector.setCurrentIndex(0)
        dialog._on_snippet_changed()
        
        # Set start index to 20
        dialog.start_index.setValue(20)
        dialog._on_start_index_changed()
        
        # End index minimum should be start + 1
        assert dialog.end_index.minimum() == 21
        
        # If end index value is less than minimum, it should be updated
        if dialog.end_index.value() < 21:
            assert dialog.end_index.value() == 21
    
    def test_custom_text_functionality(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test the custom text input functionality."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Initially custom text should be disabled
        assert not dialog.custom_text.isEnabled()
        assert not dialog.use_custom_text.isChecked()
        
        # Enable custom text
        dialog.use_custom_text.setChecked(True)
        dialog._toggle_custom_text(True)
        
        # Check that custom text is enabled and snippet controls are disabled
        assert dialog.custom_text.isEnabled()
        assert not dialog.snippet_selector.isEnabled()
        assert not dialog.start_index.isEnabled()
        assert not dialog.end_index.isEnabled()
        
        # Set custom text
        custom_content = "This is custom typing practice text for testing purposes."
        dialog.custom_text.setPlainText(custom_content)
        dialog._update_preview()
        
        # Verify preview shows custom text
        assert dialog.snippet_preview.toPlainText() == custom_content
    
    def test_status_bar_displays_user_and_keyboard_info(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test that the status bar displays correct user and keyboard information."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Check status bar message
        status_message = dialog.status_bar.currentMessage()
        
        # Should contain user name
        assert test_user.first_name in status_message
        assert test_user.surname in status_message
        
        # Should contain keyboard name
        assert test_keyboard.keyboard_name in status_message
    
    @patch('desktop_ui.drill_config.TypingDrillScreen')
    def test_start_drill_with_snippet(self, mock_typing_drill, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test starting a drill with a selected snippet."""
        # Setup mock
        mock_drill_instance = MagicMock()
        mock_drill_instance.exec_.return_value = 0
        mock_typing_drill.return_value = mock_drill_instance
        
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Select category and snippet
        dialog.category_selector.setCurrentIndex(0)
        dialog._on_category_changed(0)
        dialog.snippet_selector.setCurrentIndex(0)
        dialog._on_snippet_changed()
        
        # Set range
        dialog.start_index.setValue(0)
        dialog.end_index.setValue(50)
        
        # Start drill
        with patch.object(dialog, 'accept') as mock_accept:
            dialog._start_drill()
            
            # Verify TypingDrillScreen was created with correct parameters
            mock_typing_drill.assert_called_once()
            call_kwargs = mock_typing_drill.call_args[1]
            
            assert call_kwargs['db_manager'] == db_manager
            assert call_kwargs['user_id'] == test_user.user_id
            assert call_kwargs['keyboard_id'] == test_keyboard.keyboard_id
            assert call_kwargs['start'] == 0
            assert call_kwargs['end'] == 50
            assert len(call_kwargs['content']) == 50
            
            # Verify dialog was accepted and drill was executed
            mock_accept.assert_called_once()
            mock_drill_instance.exec_.assert_called_once()
    
    @patch('desktop_ui.drill_config.TypingDrillScreen')
    def test_start_drill_with_custom_text(self, mock_typing_drill, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test starting a drill with custom text."""
        # Setup mock
        mock_drill_instance = MagicMock()
        mock_drill_instance.exec_.return_value = 0
        mock_typing_drill.return_value = mock_drill_instance
        
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Enable custom text
        dialog.use_custom_text.setChecked(True)
        dialog._toggle_custom_text(True)
        
        # Set custom text
        custom_content = "This is a custom typing practice text for the drill test."
        dialog.custom_text.setPlainText(custom_content)
        
        # Start drill
        with patch.object(dialog, 'accept') as mock_accept:
            dialog._start_drill()
            
            # Verify TypingDrillScreen was created with custom content
            mock_typing_drill.assert_called_once()
            call_kwargs = mock_typing_drill.call_args[1]
            
            assert call_kwargs['content'] == custom_content
            assert call_kwargs['start'] == 0
            assert call_kwargs['end'] == len(custom_content)
            
            # Verify dialog was accepted and drill was executed
            mock_accept.assert_called_once()
            mock_drill_instance.exec_.assert_called_once()
    
    def test_cancel_button_functionality(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test that the cancel button properly closes the dialog."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        with patch.object(dialog, 'reject') as mock_reject:
            dialog._on_cancel_clicked()
            mock_reject.assert_called_once()
    
    def test_empty_custom_text_validation(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test validation prevents starting drill with empty custom text."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Enable custom text but leave it empty
        dialog.use_custom_text.setChecked(True)
        dialog._toggle_custom_text(True)
        dialog.custom_text.setPlainText("")
        
        # Try to start drill - should show error message
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._start_drill()
            mock_warning.assert_called_once()
            
            # Check that warning message mentions empty text
            args = mock_warning.call_args[0]
            assert "empty" in args[2].lower() or "text" in args[2].lower()
    
    def test_invalid_range_validation(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test validation prevents starting drill with invalid ranges."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Select category and snippet
        dialog.category_selector.setCurrentIndex(0)
        dialog._on_category_changed(0)
        dialog.snippet_selector.setCurrentIndex(0)
        dialog._on_snippet_changed()
        
        # Set invalid range (start >= end)
        dialog.start_index.setValue(50)
        dialog.end_index.setValue(50)
        
        # Try to start drill - should show error message
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._start_drill()
            mock_warning.assert_called_once()
            
            # Check that warning message mentions invalid range
            args = mock_warning.call_args[0]
            assert "range" in args[2].lower() or "index" in args[2].lower()
    
    def test_no_snippet_selected_validation(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test validation prevents starting drill without selecting a snippet."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Don't select any snippet (snippet_selector should be empty initially)
        # Clear any auto-selection
        dialog.snippet_selector.clear()
        
        # Try to start drill - should show error message
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._start_drill()
            mock_warning.assert_called_once()
            
            # Check that warning message mentions snippet selection
            args = mock_warning.call_args[0]
            assert "snippet" in args[2].lower() or "select" in args[2].lower()
    
    def test_database_error_handling(self, qtapp, qtbot, test_user, test_keyboard):
        """Test handling of database connection errors."""
        # Create dialog with None database manager
        with patch('PySide6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog = DrillConfigDialog(
                db_manager=None,
                user_id=test_user.user_id,
                keyboard_id=test_keyboard.keyboard_id
            )
            
            # Dialog should handle None database gracefully
            assert dialog.db_manager is None
            assert dialog.current_user is None
            assert dialog.current_keyboard is None
    
    def test_snippet_preview_updates_correctly(self, qtapp, qtbot, db_manager, test_user, test_keyboard, test_categories, test_snippets):
        """Test that snippet preview updates correctly when selections change."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Select category and snippet
        dialog.category_selector.setCurrentIndex(0)
        dialog._on_category_changed(0)
        dialog.snippet_selector.setCurrentIndex(0)
        dialog._on_snippet_changed()
        
        # Get the selected snippet content
        snippet_data = dialog.snippet_selector.itemData(0)
        
        # Test different ranges
        test_ranges = [(0, 25), (10, 50), (5, 30)]
        
        for start, end in test_ranges:
            dialog.start_index.setValue(start)
            dialog.end_index.setValue(end)
            dialog._update_preview()
            
            preview_text = dialog.snippet_preview.toPlainText()
            expected_text = snippet_data.content[start:end]
            
            assert preview_text == expected_text, f"Preview mismatch for range {start}:{end}"


# Additional edge case tests
class TestDrillConfigEdgeCases:
    """Test edge cases and error conditions for DrillConfigDialog."""
    
    def test_empty_database_handling(self, qtapp, qtbot, db_manager, test_user, test_keyboard):
        """Test behavior when database has no categories or snippets."""
        # Create dialog with empty database (no test_categories or test_snippets fixtures)
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Category selector should be empty and disabled
        assert dialog.category_selector.count() == 0
        assert not dialog.category_selector.isEnabled()
        
        # Snippet selector should be empty and disabled
        assert dialog.snippet_selector.count() == 0
        assert not dialog.snippet_selector.isEnabled()
    
    def test_invalid_user_id_handling(self, qtapp, qtbot, db_manager, test_keyboard, test_categories, test_snippets):
        """Test handling of invalid user ID."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id="nonexistent-user",
            keyboard_id=test_keyboard.keyboard_id
        )
        qtbot.addWidget(dialog)
        
        # Current user should be None due to invalid ID
        assert dialog.current_user is None
        
        # Status bar should indicate no user selected
        status_message = dialog.status_bar.currentMessage()
        assert "No user" in status_message or "selected" in status_message
    
    def test_invalid_keyboard_id_handling(self, qtapp, qtbot, db_manager, test_user, test_categories, test_snippets):
        """Test handling of invalid keyboard ID."""
        dialog = DrillConfigDialog(
            db_manager=db_manager,
            user_id=test_user.user_id,
            keyboard_id="nonexistent-keyboard"
        )
        qtbot.addWidget(dialog)
        
        # Current keyboard should be None due to invalid ID
        assert dialog.current_keyboard is None
        
        # Status bar should indicate no keyboard selected
        status_message = dialog.status_bar.currentMessage()
        assert "No" in status_message and ("keyboard" in status_message or "selected" in status_message)
