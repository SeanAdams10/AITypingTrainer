"""Tests for the Database Viewer Dialog UI component."""

import os
import sys
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path to find modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget

from desktop_ui.db_viewer_dialog import DatabaseViewerDialog
from services.database_viewer_service import DatabaseViewerService


@pytest.fixture
def qtapp() -> QApplication:
    """Create a QApplication instance for testing.

    This avoids conflicts with pytest-flask by creating a dedicated
    QApplication for Qt tests.
    """
    app = QApplication.instance()
    if isinstance(app, QApplication):
        # Narrow type for mypy; instance() may be typed as QCoreApplication
        return app
    return QApplication([])


class QtBot:
    """Simple QtBot class to replace pytest-qt's qtbot when it's not available."""

    def __init__(self, app: QApplication) -> None:
        """Keep a reference to app and tracked widgets."""
        self.app = app
        self.widgets: List[QWidget] = []

    def addWidget(self, widget: QWidget) -> QWidget:
        """Track a widget to ensure it isn't garbage collected during tests."""
        self.widgets.append(widget)
        return widget

    def mouseClick(
        self,
        widget: QWidget,
        button: Qt.MouseButton = Qt.MouseButton.LeftButton,
        pos: Optional[QPoint] = None,
    ) -> None:
        """Simulate mouse click."""
        if pos is None:
            pos = widget.rect().center()
        # Here we would normally use QTest.mouseClick, but for our tests
        # we can just directly call the click handler
        if hasattr(widget, "click"):
            widget.click()
        # Process events to make sure UI updates
        self.app.processEvents()


@pytest.fixture
def qtbot(qtapp: QApplication) -> QtBot:
    """Create a QtBot instance for testing when pytest-qt's qtbot isn't available."""
    return QtBot(qtapp)


class MockItem:
    """Mock QTableWidgetItem for testing."""

    def __init__(self, text: str = "") -> None:
        """Initialize with a text value."""
        self._text = text

    def text(self) -> str:
        """Return the stored text value."""
        return self._text


@pytest.fixture
def mock_db_viewer_service() -> MagicMock:
    """Create a mock DatabaseViewerService for testing."""
    service = MagicMock(spec=DatabaseViewerService)

    # Set up default mock return values with correct structure
    service.list_tables.return_value = ["table1", "table2", "table3"]
    service.get_table_data.return_value = {
        "rows": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "columns": ["id", "name", "value"],
        "total_rows": 3,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 50,
    }
    service.export_table_to_csv.return_value = True

    return service


def test_db_viewer_dialog_initialization(
    qtapp: QApplication, mock_db_viewer_service: MagicMock, qtbot: QtBot
) -> None:
    """Test that the DatabaseViewerDialog initializes correctly."""
    # Setup mock for table data with more complete structure
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "columns": ["id", "name", "value"],
        "total_rows": 3,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 50,
    }

    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Check that the service methods were called to get tables and the first table's data
    mock_db_viewer_service.list_tables.assert_called_once()
    # Auto-selection happens in load_tables, so get_table_data should be called for table1
    mock_db_viewer_service.get_table_data.assert_called_with(
        table_name="table1",  # First table should be auto-selected
        page=1,
        page_size=50,
        sort_by=None,
        sort_order="asc",
        filter_column=None,
        filter_value=None,
    )

    # Check UI components initialized correctly
    assert dialog.windowTitle() == "Database Viewer"
    assert dialog.table_combo.count() == 3  # Should have 3 items (table1, table2, table3)
    assert dialog.current_table == "table1"  # First table should be auto-selected
    assert dialog.page == 1  # Initial page

    # Dialog should have these key widgets
    assert dialog.table_widget is not None
    assert dialog.filter_input is not None
    assert dialog.export_btn is not None
    assert dialog.prev_btn is not None
    assert dialog.next_btn is not None

    # Table should be populated with data
    assert dialog.table_widget.rowCount() == 3
    assert dialog.table_widget.columnCount() == 3  # id, name, value

    # Status label should show number of records
    assert "3 records in 'table1'" == dialog.status_label.text()


def test_table_selection(
    qtapp: QApplication, mock_db_viewer_service: MagicMock, qtbot: QtBot
) -> None:
    """Test that selecting a table loads its data."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Since the first table is auto-selected on init, let's select a different table
    # Reset the mock to clear the initial calls
    mock_db_viewer_service.reset_mock()

    # Configure the mock to return proper data for table2
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "columns": ["id", "name", "value"],
        "total_rows": 3,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 50,
    }

    # Select a different table by directly calling the handler
    dialog.on_table_selected("table2")

    # Check that the service method was called to get table data for the newly selected table
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table2",
        page=1,
        page_size=50,
        sort_by=None,
        sort_order="asc",
        filter_column=None,
        filter_value=None,
    )

    # Current table should be updated
    assert dialog.current_table == "table2"

    # Table widget should be populated
    assert dialog.table_widget.rowCount() == 3  # 3 rows of data
    assert dialog.table_widget.columnCount() == 3  # id, name, value columns

    # Check table content with proper null handling
    item_0_0 = dialog.table_widget.item(0, 0)
    item_0_1 = dialog.table_widget.item(0, 1)
    item_0_2 = dialog.table_widget.item(0, 2)

    assert (item_0_0.text() if item_0_0 else "") == "1"  # id
    assert (item_0_1.text() if item_0_1 else "") == "Item 1"  # name
    assert (item_0_2.text() if item_0_2 else "") == "100"  # value


def test_pagination(qtapp: QApplication, mock_db_viewer_service: MagicMock, qtbot: QtBot) -> None:
    """Test pagination controls."""
    # First prepare the mock to return pagination data
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [{"id": i, "name": f"Item {i}"} for i in range(1, 6)],
        "columns": ["id", "name"],
        "total_rows": 15,  # 15 total rows = 3 pages with 5 per page
        "total_pages": 3,
        "current_page": 1,
        "page_size": 5,
    }

    # Create dialog with pagination-ready mock
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()

    # Set up state for pagination test
    dialog.page_size = 5
    dialog.current_table = "table1"
    dialog.total_pages = 3  # Simulate having multiple pages
    dialog.page = 1

    # Test next page button
    dialog.next_page()

    # Check that page was incremented
    assert dialog.page == 2

    # Verify service was called with the new page number
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=2,
        page_size=5,
        sort_by=None,
        sort_order="asc",
        filter_column=None,
        filter_value=None,
    )

    # Reset mock and test previous page
    mock_db_viewer_service.reset_mock()
    dialog.previous_page()

    # Check service called with page=1
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=5,
        sort_by=None,
        sort_order="asc",
        filter_column=None,
        filter_value=None,
    )


@patch("PySide6.QtWidgets.QMessageBox.information")
@patch("PySide6.QtWidgets.QFileDialog.getSaveFileName")
def test_export_functionality(
    mock_get_save_filename: MagicMock,
    mock_info_box: MagicMock,
    qtapp: QApplication,
    mock_db_viewer_service: MagicMock,
    qtbot: QtBot,
) -> None:
    """Test CSV export functionality."""
    # Setup mocks
    mock_get_save_filename.return_value = ("test_export.csv", "CSV Files (*.csv)")
    mock_db_viewer_service.export_table_to_csv.return_value = True

    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Set current table
    dialog.current_table = "table1"

    # Trigger export
    dialog.export_to_csv()

    # Verify file dialog was called
    mock_get_save_filename.assert_called_once()

    # Verify export service was called
    mock_db_viewer_service.export_table_to_csv.assert_called_with(
        table_name="table1",
        output_file="test_export.csv",
        filter_column=None,
        filter_value=None,
    )

    # Verify success message was shown
    mock_info_box.assert_called_once()


def test_filtering(qtapp: QApplication, mock_db_viewer_service: MagicMock, qtbot: QtBot) -> None:
    """Test table filtering functionality."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()

    # Set up filter test
    dialog.current_table = "table1"
    dialog.filter_column = "name"
    dialog.filter_input.setText("Item 1")

    # Trigger filter
    dialog.apply_filter()

    # Verify service was called with filter parameters
    mock_db_viewer_service.get_table_data.assert_called_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_by=None,
        sort_order="asc",
        filter_column="name",
        filter_value="Item 1",
    )
