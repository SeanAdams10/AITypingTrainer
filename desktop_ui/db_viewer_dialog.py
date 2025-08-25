"""Database Viewer Dialog for AI Typing Trainer (PySide6).

This module provides a GUI for viewing database tables in a read-only interface.
"""

from typing import Optional, cast

from PySide6 import QtGui, QtWidgets
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from services.database_viewer_service import DatabaseViewerService


class DatabaseViewerDialog(QDialog):
    """Dialog for viewing database tables and content.

    Features:
    - Table selection
    - Data display with pagination, sorting, filtering
    - Export to CSV
    - Error handling

    Args:
        service: DatabaseViewerService instance to access table data
        parent: Optional parent widget
    """

    def __init__(
        self,
        service: DatabaseViewerService,
        parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        """Initialize the dialog and build the UI.

        Parameters:
            service: Service used to list tables and fetch data.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.service = service
        # Initialize with empty string, will be set when a table is selected
        self.current_table = ""
        self.page = 1
        self.page_size = 50
        self.total_rows = 0
        self.total_pages = 0
        self.sort_column = ""
        self.sort_order = "asc"
        self.filter_text = ""
        self.filter_column: str | None = None

        self.setWindowTitle("Database Viewer")
        self.resize(900, 600)
        self.setup_ui()
        self.load_tables()
        # Do not select a table automatically during initialization

    def setup_ui(self) -> None:
        """Set up the UI components and layout."""
        main_layout = QVBoxLayout()

        # Top controls
        top_layout = QHBoxLayout()

        # Table selection
        table_label = QLabel("Select Table:")
        self.table_combo = QComboBox()
        # Connecting a signal through a lambda ensures it works in tests
        self.table_combo.currentTextChanged.connect(
            lambda text: self.on_table_selected(text)
        )
        top_layout.addWidget(table_label)
        top_layout.addWidget(self.table_combo)

        # Filter
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter rows...")
        self.filter_input.textChanged.connect(lambda text: self.on_filter_changed(text))
        top_layout.addWidget(filter_label)
        top_layout.addWidget(self.filter_input)

        # Export button
        self.export_btn = QPushButton("Export to CSV")
        self.export_btn.clicked.connect(self.export_to_csv)
        top_layout.addWidget(self.export_btn)

        main_layout.addLayout(top_layout)

        # Table widget
        self.table_widget = QTableWidget()
        # Read-only
        self.table_widget.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )

        # Cast the header to ensure type safety
        header = cast(QHeaderView, self.table_widget.horizontalHeader())
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.sectionClicked.connect(self.on_header_clicked)

        main_layout.addWidget(self.table_widget)

        # Pagination controls
        pagination_layout = QHBoxLayout()

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self.previous_page)

        self.page_label = QLabel("Page 0 of 0")

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self.next_page)

        page_size_label = QLabel("Rows per page:")
        self.page_size_combo = QComboBox()
        for size in [10, 25, 50, 100]:
            self.page_size_combo.addItem(str(size))
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(
            lambda text: self.on_page_size_changed(text)
        )

        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addStretch()
        pagination_layout.addWidget(page_size_label)
        pagination_layout.addWidget(self.page_size_combo)

        main_layout.addLayout(pagination_layout)

        # Status bar
        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def load_tables(self) -> None:
        """Load the list of database tables into the combo box."""
        try:
            tables = self.service.list_tables()
            self.table_combo.clear()

            # Block signals temporarily to prevent automatic selection during loading
            self.table_combo.blockSignals(True)
            self.table_combo.addItems(tables)
            self.table_combo.blockSignals(False)

            if tables:
                self.status_label.setText(f"{len(tables)} tables found.")
                # Auto-select the first table and load its data
                if self.table_combo.count() > 0:
                    self.on_table_selected(self.table_combo.itemText(0))
                    # Visual feedback for the user about what's selected
                    self.table_combo.setCurrentIndex(0)
            else:
                self.status_label.setText("No tables found in database.")
        except Exception as e:
            self.show_error(f"Error loading tables: {str(e)}")

    def on_table_selected(self, table_name: str) -> None:
        """Handle table selection from dropdown."""
        if not table_name:
            return

        self.current_table = table_name
        self.page = 1
        self.sort_column = ""
        self.sort_order = "asc"
        self.load_table_data()

    def on_filter_changed(self, text: str) -> None:
        """Handle filter text changes."""
        self.filter_text = text.strip()
        self.page = 1  # Reset to first page
        self.load_table_data()

    def on_page_size_changed(self, text: str) -> None:
        """Handle page size selection."""
        try:
            self.page_size = int(text)
            self.page = 1  # Reset to first page
            self.load_table_data()
        except ValueError:
            pass

    def on_header_clicked(self, column_index: int) -> None:
        """Handle column header click for sorting."""
        if column_index < 0 or column_index >= self.table_widget.columnCount():
            return

        header_item = self.table_widget.horizontalHeaderItem(column_index)
        if not header_item:
            return

        column_name = header_item.text()

        # Toggle sort order if same column
        if column_name == self.sort_column:
            self.sort_order = "desc" if self.sort_order == "asc" else "asc"
        else:
            self.sort_column = column_name
            self.sort_order = "asc"

        self.load_table_data()

    def load_table_data(self) -> None:
        """Load and display table data with current pagination, sorting, and filtering."""
        if not self.current_table:
            return

        try:
            # Get table data with current settings
            fc = self.filter_column if self.filter_column else ("*" if self.filter_text else None)
            fv = self.filter_text if self.filter_text else None
            results = self.service.get_table_data(
                table_name=self.current_table,
                page=self.page,
                page_size=self.page_size,
                sort_by=self.sort_column if self.sort_column else None,
                sort_order=self.sort_order,
                filter_column=fc,
                filter_value=fv
            )

            if results is None:
                self.show_error(f"No data returned for table '{self.current_table}'")
                return

            data = results.get("rows", [])
            self.total_rows = results.get("total_rows", 0)
            self.total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)

            # Configure table
            self.table_widget.setRowCount(0)  # Clear table

            if not data:
                self.table_widget.setColumnCount(0)
                self.status_label.setText("No data found.")
                self.update_pagination_ui()
                return

            # Get column names from the first row
            columns = list(data[0].keys())
            self.table_widget.setColumnCount(len(columns))
            self.table_widget.setHorizontalHeaderLabels(columns)

            # Add rows
            for row_idx, row_data in enumerate(data):
                self.table_widget.insertRow(row_idx)
                for col_idx, column in enumerate(columns):
                    value = row_data.get(column, "")
                    item = QTableWidgetItem(str(value))
                    self.table_widget.setItem(row_idx, col_idx, item)

            # Update status and pagination
            if self.filter_text:
                self.status_label.setText(
                    f"{self.total_rows} records match filter in '{self.current_table}'"
                )
            else:
                self.status_label.setText(
                    f"{self.total_rows} records in '{self.current_table}'"
                )

            self.update_pagination_ui()

        except Exception as e:
            self.show_error(f"Error loading table data: {str(e)}")

    def apply_filter(self) -> None:
        """Apply current filter settings using the filter input and optional column."""
        self.filter_text = self.filter_input.text().strip()
        self.page = 1
        self.load_table_data()

    def update_pagination_ui(self) -> None:
        """Update pagination controls based on current state."""
        self.page_label.setText(f"Page {self.page} of {self.total_pages}")
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < self.total_pages)

    def previous_page(self) -> None:
        """Navigate to the previous page."""
        if self.page > 1:
            self.page -= 1
            self.load_table_data()

    def next_page(self) -> None:
        """Navigate to the next page."""
        if self.page < self.total_pages:
            self.page += 1
            self.load_table_data()

    def export_to_csv(self) -> None:
        """Export current table data to CSV file."""
        if not self.current_table:
            self.show_error("Please select a table first.")
            return

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export to CSV",
                f"{self.current_table}.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return  # User cancelled

            # Show progress dialog
            progress = QProgressBar(self)
            progress.setWindowTitle("Exporting data...")
            progress.setRange(0, 0)  # Indeterminate
            progress.show()

            try:
                # Export directly to the file through service
                fc = (
                    self.filter_column
                    if self.filter_column
                    else ("*" if self.filter_text else None)
                )
                fv = self.filter_text if self.filter_text else None
                self.service.export_table_to_csv(
                    table_name=self.current_table,
                    output_file=file_path,
                    filter_column=fc,
                    filter_value=fv
                )

                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Data exported successfully to {file_path}"
                )
            finally:
                progress.hide()

        except Exception as e:
            self.show_error(f"Error exporting data: {str(e)}")

    def show_error(self, message: str) -> None:
        """Display error message and update status label."""
        QMessageBox.critical(self, "Error", message)
        self.status_label.setText(f"Error: {message}")

    def closeEvent(self, event: Optional[QtGui.QCloseEvent]) -> None:
        """Handle dialog close event."""
        # Any cleanup needed when dialog is closed
        if event is not None:
            event.accept()
