"""
Tests for the Database Viewer Dialog UI component.
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any

# Add parent directory to path to find modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QFileDialog
from PyQt5.QtCore import Qt

from desktop_ui.db_viewer_dialog import DatabaseViewerDialog
from services.database_viewer_service import DatabaseViewerService
from db.database_manager import DatabaseManager


@pytest.fixture
def app():
    """Create a QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_db_viewer_service():
    """Create a mock DatabaseViewerService for testing."""
    service = MagicMock(spec=DatabaseViewerService)
    
    # Set up default mock return values
    service.list_tables.return_value = ["table1", "table2", "table3"]
    service.get_table_data.return_value = {
        "data": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "total_rows": 3
    }
    service.export_table_to_csv.return_value = "id,name,value\n1,Item 1,100\n2,Item 2,200\n3,Item 3,300"
    
    return service


def test_db_viewer_dialog_initialization(app, mock_db_viewer_service, qtbot):
    """Test that the DatabaseViewerDialog initializes correctly."""
    # Setup mock for table data with more complete structure
    mock_db_viewer_service.get_table_data.return_value = {
        "columns": ["id", "name", "value"],
        "rows": [
            {"id": 1, "name": "Item 1", "value": 100},
            {"id": 2, "name": "Item 2", "value": 200},
            {"id": 3, "name": "Item 3", "value": 300},
        ],
        "total_rows": 3,
        "total_pages": 1,
        "current_page": 1,
        "page_size": 50
    }
    
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)
    
    # Check that the service methods were called to get tables and the first table's data
    mock_db_viewer_service.list_tables.assert_called_once()
    mock_db_viewer_service.get_table_data.assert_called_with(
        table_name="table1",  # First table should be auto-selected
        page=1,
        page_size=50,
        sort_by=None,
        sort_order="asc",
        filter_column=None,
        filter_value=None
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
    
    # Status label should show number of rows
    assert "3 rows" in dialog.status_label.text()


def test_table_selection(app, mock_db_viewer_service, qtbot):
    """Test that selecting a table loads its data."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)
    
    # Since the first table is auto-selected on init, let's select a different table
    # Reset the mock to clear the initial calls
    mock_db_viewer_service.reset_mock()
    
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
        filter_value=None
    )
    
    # Current table should be updated
    assert dialog.current_table == "table2"
    
    # Table widget should be populated
    assert dialog.table_widget.rowCount() == 3  # 3 rows of data
    assert dialog.table_widget.columnCount() == 3  # id, name, value columns
    assert dialog.table_widget.item(0, 0).text() == "1"  # id
    assert dialog.table_widget.item(0, 1).text() == "Item 1"  # name
    assert dialog.table_widget.item(0, 2).text() == "100"  # value


def test_pagination(app, mock_db_viewer_service, qtbot):
    """Test pagination controls."""
    # First prepare the mock to return pagination data
    mock_db_viewer_service.get_table_data.return_value = {
        "rows": [{"id": i, "name": f"Item {i}"} for i in range(1, 6)],
        "total_rows": 15,  # 15 total rows = 3 pages with 5 per page
        "total_pages": 3,
        "current_page": 1,
        "page_size": 5
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
        filter_value=None
    )
    
    # Reset mock and test previous page
    mock_db_viewer_service.reset_mock()
    dialog.previous_page()
    
    # Check service called with page=1
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=5,
        sort_column=None,
        sort_order="asc",
        filter_text=None
    )


def test_sorting(app, mock_db_viewer_service, qtbot):
    """Test column sorting."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)
    
    # Select a table
    dialog.table_combo.setCurrentText("table1")
    
    # Reset mock to clear previous calls
    mock_db_viewer_service.reset_mock()
    
    # Setup horizontal header with column names
    dialog.table_widget.setColumnCount(3)
    dialog.table_widget.setHorizontalHeaderLabels(["id", "name", "value"])
    
    # Simulate clicking on the "name" column header (index 1)
    dialog.on_header_clicked(1)
    
    # Check service called with sort_column="name" and sort_order="asc"
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_column="name",
        sort_order="asc",
        filter_text=None
    )
    
    # Reset mock and click again to test descending order
    mock_db_viewer_service.reset_mock()
    dialog.on_header_clicked(1)
    
    # Check service called with sort_column="name" and sort_order="desc"
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_column="name",
        sort_order="desc",
        filter_text=None
    )


def test_filtering(app, mock_db_viewer_service, qtbot):
    """Test table filtering."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)
    
    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()
    
    # Set current table directly
    dialog.current_table = "table1"
    
    # Enter filter text and trigger filter
    dialog.filter_text = "test"
    dialog.on_filter_changed("test")
    
    # Check service called with correct filter parameters
    mock_db_viewer_service.get_table_data.assert_called_once_with(
        table_name="table1",
        page=1,
        page_size=50,
        sort_by=None,
        sort_order="asc",
        filter_column="*",
        filter_value="test"
    )
    
    # Status should show filtered results message
    assert "match filter" in dialog.status_label.text()


@patch("PyQt5.QtWidgets.QFileDialog.getSaveFileName")
@patch("PyQt5.QtWidgets.QMessageBox.information")
def test_export_to_csv(mock_info_box, mock_get_save_filename, app, mock_db_viewer_service, qtbot):
    """Test exporting to CSV."""
    # Setup mock to return a file path
    mock_get_save_filename.return_value = ("test_export.csv", "CSV Files (*.csv)")
    
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)
    
    # Reset mock to clear initialization calls
    mock_db_viewer_service.reset_mock()
    
    # Manually set current table
    dialog.current_table = "table1"
    
    # Export to CSV (no filter)
    dialog.export_to_csv()
    
    # Check service was called with correct parameters
    mock_db_viewer_service.export_table_to_csv.assert_called_once_with(
        table_name="table1",
        output_file="test_export.csv",
        filter_column=None,
        filter_value=None
    )
    
    # Now test with a filter
    mock_db_viewer_service.reset_mock()
    dialog.filter_text = "test_filter"
    dialog.export_to_csv()
    
    # Check service called with filter parameters
    mock_db_viewer_service.export_table_to_csv.assert_called_once_with(
        table_name="table1",
        output_file="test_export.csv",
        filter_column="*",
        filter_value="test_filter"
    )
    
    # Verify success message was shown
    mock_info_box.assert_called_with(
        dialog,
        "Export Complete", 
        f"Data exported successfully to test_export.csv"
    )
        

def test_error_handling(app, mock_db_viewer_service, qtbot):
    """Test error handling for service exceptions."""
    dialog = DatabaseViewerDialog(service=mock_db_viewer_service)
    qtbot.addWidget(dialog)
    
    # Make the service throw an exception
    mock_db_viewer_service.get_table_data.side_effect = Exception("Test error")
    
    # Mock QMessageBox.critical to prevent actual dialog from showing
    with patch("PyQt5.QtWidgets.QMessageBox.critical") as mock_critical:
        # Call the table selection method directly
        dialog.on_table_selected("table1")
        
        # Check that error dialog was shown
        mock_critical.assert_called_once()
        
        # The error message should contain our test error
        args, kwargs = mock_critical.call_args
        assert "Test error" in args[2]
        
        # Status label should be updated with the error
        assert "Error:" in dialog.status_label.text()
