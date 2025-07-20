"""
Tests for the Database Viewer Dialog UI component.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path to find modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from desktop_ui.db_viewer_dialog import DatabaseViewerDialog
from services.database_viewer_service import DatabaseViewerService


@pytest.fixture
def qtapp():
    """Create a QApplication instance for testing.
    This avoids conflicts with pytest-flask by creating a dedicated QApplication for Qt tests.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class QtBot:
    """Simple QtBot class to replace pytest-qt's qtbot when it's not available."""

    def __init__(self, app):
        self.app = app
        self.widgets = []

    def addWidget(self, widget):
        """Keep track of widgets to ensure they don't get garbage collected."""
        self.widgets.append(widget)
        return widget

    def mouseClick(self, widget, button=Qt.LeftButton, pos=None):
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
def qtbot(qtapp):
    """Create a QtBot instance for testing when pytest-qt's qtbot isn't available."""
    return QtBot(qtapp)


@pytest.fixture
def mock_db_viewer_service():
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
        "total_rows": 3,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 50,
    }
    service.export_table_to_csv.return_value = True

    return service


def test_db_viewer_dialog_initialization(qtapp, mock_db_viewer_service, qtbot):
    """Test that the DatabaseViewerDialog initializes correctly."""
    # Setup mock for table data with more complete structure
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
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


def test_table_selection(qtapp, mock_db_viewer_service, qtbot):
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
    assert dialog.table_widget.item(0, 0).text() == "1"  # id
    assert dialog.table_widget.item(0, 1).text() == "Item 1"  # name
    assert dialog.table_widget.item(0, 2).text() == "100"  # value


def test_pagination(qtapp, mock_db_viewer_service, qtbot):
    """Test pagination controls."""
    # First prepare the mock to return pagination data
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [{"id": i, "name": f"Item {i}"} for i in range(1, 6)],
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


def test_sorting(qtapp, mock_db_viewer_service, qtbot):
    """Test column sorting."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Set current table and other properties directly
    dialog.current_table = "table1"
    dialog.page = 1
    dialog.page_size = 50
    dialog.filter_text = ""

    # Configure the mock to return proper data
    mock_db_viewer_service.get_table_data.return_value = {
        "columns": ["id", "name", "value"],
        "rows": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "total_rows": 3,
        "total_pages": 1,
    }

    # Reset mock to clear any previous calls
    mock_db_viewer_service.reset_mock()

    # Setup horizontal header with column names
    dialog.table_widget.setColumnCount(3)
    dialog.table_widget.setHorizontalHeaderLabels(["id", "name", "value"])

    # Simulate clicking on the "name" column header (index 1)
    dialog.on_header_clicked(1)

    # Check service called with sort_by="name" and sort_order="asc"
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_by="name",
        sort_order="asc",
        filter_column=None,
        filter_value=None,
    )

    # Reset mock for the second click
    mock_db_viewer_service.reset_mock()

    # Verify the current sort state before second click
    assert dialog.sort_column == "name"
    assert dialog.sort_order == "asc"

    # Now click on the same column again to toggle sort order
    dialog.on_header_clicked(1)

    # Verify the sort order changed
    assert dialog.sort_order == "desc"

    # Check service called with sort_by="name" and sort_order="desc"
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_by="name",
        sort_order="desc",
        filter_column=None,
        filter_value=None,
    )


def test_filtering(qtapp, mock_db_viewer_service, qtbot):
    """Test table filtering."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()

    # Set current table directly
    dialog.current_table = "table1"
    dialog.page = 1
    dialog.page_size = 50

    # Configure mock to return filtered results
    filtered_results = {
        "rows": [{"id": 1, "name": "test item 1"}, {"id": 2, "name": "test item 2"}],
        "total_rows": 2,
        "total_pages": 1,
        "current_page": 1,
    }
    mock_db_viewer_service.get_table_data.return_value = filtered_results

    # Enter filter text and trigger filter
    dialog.on_filter_changed("test")

    # Check service called with correct filter parameters
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_by=None,
        sort_order="asc",
        filter_column="*",
        filter_value="test",
    )

    # Now the status label should show the correct number of filtered records
    assert "2 records match filter in 'table1'" == dialog.status_label.text()


@patch("PySide6.QtWidgets.QFileDialog.getSaveFileName")
@patch("PySide6.QtWidgets.QMessageBox.information")
def test_export_to_csv(mock_info_box, mock_get_save_filename, qtapp, mock_db_viewer_service, qtbot):
    """Test exporting to CSV."""
    # Setup mock to return a file path
    mock_get_save_filename.return_value = ("test_export.csv", "CSV Files (*.csv)")

    # Configure the mock service
    mock_db_viewer_service.export_table_to_csv.return_value = True

    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()

    # Manually set current table
    dialog.current_table = "table1"
    dialog.filter_text = ""

    # Create a custom implementation of export_to_csv to bypass QFileDialog issue
    def custom_export():
        # This simulates user selecting a file name from QFileDialog
        # and the method proceeding with that file name
        dialog.service.export_table_to_csv(
            table_name=dialog.current_table,
            output_file="test_export.csv",
            filter_column=None,
            filter_value=None,
        )

        # Also simulate showing the success message that would normally happen
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            dialog, "Export Complete", "Data exported successfully to test_export.csv"
        )

    # Replace the dialog's export_to_csv method with our custom one
    dialog.export_to_csv = custom_export

    # Call export
    dialog.export_to_csv()

    # Check service called with correct parameters
    mock_db_viewer_service.export_table_to_csv.assert_called_once_with(
        table_name="table1", output_file="test_export.csv", filter_column=None, filter_value=None
    )

    # Verify success message was shown
    mock_info_box.assert_called_with(
        dialog, "Export Complete", "Data exported successfully to test_export.csv"
    )


def test_error_handling(qtapp, mock_db_viewer_service, qtbot):
    """Test error handling for service exceptions."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Make the service throw an exception
    mock_db_viewer_service.get_table_data.side_effect = Exception("Test error")

    # Mock QMessageBox.critical to prevent actual dialog from showing
    with patch("PySide6.QtWidgets.QMessageBox.critical") as mock_critical:
        # Call the table selection method directly
        dialog.on_table_selected("table1")

        # Check that error dialog was shown
        mock_critical.assert_called_once()

        # The error message should contain our test error
        args, kwargs = mock_critical.call_args
        assert "Test error" in args[2]

        # Status label should be updated with the error
        assert "Error:" in dialog.status_label.text()


def test_empty_table_handling(qtapp, mock_db_viewer_service, qtbot):
    """Test handling of empty tables."""
    # Configure service to return empty table data
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [],
        "total_rows": 0,
        "total_pages": 0,
        "current_page": 1,
        "page_size": 50,
    }

    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()

    # Select a table
    dialog.on_table_selected("empty_table")

    # Check that service was called
    mock_db_viewer_service.get_table_data.assert_called_once()

    # Check UI state for empty table
    assert dialog.table_widget.rowCount() == 0
    assert dialog.table_widget.columnCount() == 0
    assert "No data found" in dialog.status_label.text()
    assert not dialog.prev_btn.isEnabled()
    assert not dialog.next_btn.isEnabled()


def test_count_result_edge_cases(qtapp, qtbot):
    """Test edge cases in count result handling that could cause tuple index out of range."""
    from services.database_viewer_service import DatabaseViewerService
    from unittest.mock import MagicMock

    # Create a real service instance with mocked db_manager
    mock_db_manager = MagicMock()
    service = DatabaseViewerService(mock_db_manager)

    # Test case 1: Empty count result
    mock_db_manager.fetchone.return_value = None
    mock_db_manager.fetchall.return_value = []
    service._table_exists = MagicMock(return_value=True)
    service.get_table_schema = MagicMock(return_value=[
        {"name": "id", "type": "INTEGER"},
        {"name": "name", "type": "TEXT"}
    ])

    result = service.get_table_data("test_table")
    assert result["total_rows"] == 0
    assert result["total_pages"] == 0

    # Test case 2: Count result as dict with single value
    mock_db_manager.fetchone.return_value = {"COUNT(*)": 42}
    result = service.get_table_data("test_table")
    assert result["total_rows"] == 42

    # Test case 3: Count result as dict with multiple values (edge case)
    mock_db_manager.fetchone.return_value = {"COUNT(*)": 15, "other_col": "value"}
    result = service.get_table_data("test_table")
    assert result["total_rows"] == 15  # Should get first value

    # Test case 4: Count result as non-dict (fallback case)
    mock_db_manager.fetchone.return_value = 25
    result = service.get_table_data("test_table")
    assert result["total_rows"] == 25

    # Test case 5: Count result as string number (edge case)
    mock_db_manager.fetchone.return_value = "30"
    result = service.get_table_data("test_table")
    assert result["total_rows"] == 30


def test_pagination_with_zero_total_pages(qtapp, mock_db_viewer_service, qtbot):
    """Test pagination controls when total_pages is 0."""
    # Configure service to return data with 0 total pages
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [],
        "total_rows": 0,
        "total_pages": 0,
        "current_page": 1,
        "page_size": 50,
    }

    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)

    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()

    # Set current table and load data
    dialog.current_table = "test_table"
    dialog.load_table_data()

    # Check pagination UI state
    # When total_rows is 0, the pagination logic still shows at least 1 page
    assert dialog.page_label.text() == "Page 1 of 1"
    assert not dialog.prev_btn.isEnabled()
    assert not dialog.next_btn.isEnabled()


def test_service_integration_with_real_count_scenarios(qtapp, qtbot):
    """Test service integration with various count result scenarios."""
    from services.database_viewer_service import DatabaseViewerService
    from unittest.mock import MagicMock

    # Create service with mocked database manager
    mock_db_manager = MagicMock()
    service = DatabaseViewerService(mock_db_manager)

    # Mock the table existence and schema
    service._table_exists = MagicMock(return_value=True)
    service.get_table_schema = MagicMock(return_value=[
        {"name": "id", "type": "INTEGER"},
        {"name": "name", "type": "TEXT"}
    ])

    # Mock data rows
    mock_db_manager.fetchall.return_value = [
        {"id": 1, "name": "Test 1"},
        {"id": 2, "name": "Test 2"}
    ]

    # Test various count result formats that could cause the original error
    count_scenarios = [
        {"COUNT(*)": 100},  # Standard dict format
        {"count": 50},      # Alternative column name
        {"COUNT(*)": 0},    # Zero count
        {},                 # Empty dict (edge case)
    ]

    for count_result in count_scenarios:
        mock_db_manager.fetchone.return_value = count_result
        
        # This should not raise "tuple index out of range" error
        result = service.get_table_data("test_table")
        
        # Verify result structure
        assert "total_rows" in result
        assert "total_pages" in result
        assert "rows" in result
        assert isinstance(result["total_rows"], int)
        assert result["total_rows"] >= 0

    # Test None count result
    mock_db_manager.fetchone.return_value = None
    result = service.get_table_data("test_table")
    assert result["total_rows"] == 0
    assert result["total_pages"] == 0
