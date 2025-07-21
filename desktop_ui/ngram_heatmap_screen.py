"""
NGram Speed Heatmap UI Screen.

This module provides a desktop UI for visualizing n-gram typing speed performance
using a heatmap with filtering, sorting, and color coding capabilities.
"""

import os
import sys
from typing import List, Optional

# Ensure project root is in sys.path before any project imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtCore, QtGui, QtWidgets

from db.database_manager import DatabaseManager
from models.keyboard import Keyboard
from models.ngram_analytics_service import NGramAnalyticsService, NGramHeatmapData
from models.ngram_manager import NGramManager
from models.user import User


class NGramHeatmapDialog(QtWidgets.QDialog):
    """
    N-gram Speed Heatmap visualization screen.

    Features:
    - Interactive heatmap showing n-gram typing speeds
    - Color-coded performance indicators
    - Filtering by n-gram size, speed ranges, and performance levels
    - Sorting options for different metrics
    - Export functionality for analysis data
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        user: User,
        keyboard: Keyboard,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """
        Initialize the NGram Heatmap Dialog.

        Args:
            db_manager: Database manager instance
            user: Current user
            keyboard: Current keyboard
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.user = user
        self.keyboard = keyboard

        # Initialize analytics service
        self.ngram_manager = NGramManager(db_manager)
        self.analytics_service = NGramAnalyticsService(db_manager, self.ngram_manager)

        # Data storage
        self.heatmap_data: List[NGramHeatmapData] = []
        self.filtered_data: List[NGramHeatmapData] = []

        self.setWindowTitle("N-gram Speed Heatmap")
        self.setMinimumSize(1200, 800)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        # Set modal behavior
        self.setModal(True)

        self.setup_ui()
        self.load_data()

    def setup_ui(self) -> None:
        """Set up the user interface components."""
        layout = QtWidgets.QVBoxLayout(self)

        # Header
        header = QtWidgets.QLabel("N-gram Speed Heatmap")
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font = header.font()
        font.setPointSize(18)
        font.setBold(True)
        header.setFont(font)
        layout.addWidget(header)

        # User and keyboard info
        info_layout = QtWidgets.QHBoxLayout()
        user_label = QtWidgets.QLabel(f"User: {self.user.first_name} {self.user.surname}")
        keyboard_label = QtWidgets.QLabel(f"Keyboard: {self.keyboard.keyboard_name}")
        info_layout.addWidget(user_label)
        info_layout.addStretch()
        info_layout.addWidget(keyboard_label)
        layout.addLayout(info_layout)

        # Control panel
        self.setup_control_panel(layout)

        # Heatmap area
        self.setup_heatmap_area(layout)

        # Dialog buttons
        self.button_box = QtWidgets.QDialogButtonBox()

        refresh_btn = QtWidgets.QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_data)
        self.button_box.addButton(refresh_btn, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)

        export_btn = QtWidgets.QPushButton("Export Data")
        export_btn.clicked.connect(self.export_data)
        self.button_box.addButton(export_btn, QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)

        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        self.button_box.addButton(close_btn, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(self.button_box)

        # Status bar
        self.status_label = QtWidgets.QLabel("Ready")
        layout.addWidget(self.status_label)

    def setup_control_panel(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        """Set up the control panel with filters and options."""
        control_group = QtWidgets.QGroupBox("Controls")
        control_layout = QtWidgets.QGridLayout()

        # N-gram size filter
        control_layout.addWidget(QtWidgets.QLabel("N-gram Size:"), 0, 0)
        self.ngram_size_combo = QtWidgets.QComboBox()
        self.ngram_size_combo.addItems(["All", "1", "2", "3", "4", "5"])
        self.ngram_size_combo.setCurrentText("1")
        self.ngram_size_combo.currentTextChanged.connect(self.apply_filters)
        control_layout.addWidget(self.ngram_size_combo, 0, 1)

        # Speed range filter
        control_layout.addWidget(QtWidgets.QLabel("Speed Range (ms):"), 0, 2)
        speed_layout = QtWidgets.QHBoxLayout()
        self.speed_min_spin = QtWidgets.QSpinBox()
        self.speed_min_spin.setMinimum(0)
        self.speed_min_spin.setMaximum(2000)
        self.speed_min_spin.setValue(0)
        self.speed_min_spin.valueChanged.connect(self.apply_filters)
        speed_layout.addWidget(self.speed_min_spin)

        speed_layout.addWidget(QtWidgets.QLabel("to"))

        self.speed_max_spin = QtWidgets.QSpinBox()
        self.speed_max_spin.setMinimum(0)
        self.speed_max_spin.setMaximum(2000)
        self.speed_max_spin.setValue(2000)
        self.speed_max_spin.valueChanged.connect(self.apply_filters)
        speed_layout.addWidget(self.speed_max_spin)

        speed_widget = QtWidgets.QWidget()
        speed_widget.setLayout(speed_layout)
        control_layout.addWidget(speed_widget, 0, 3)

        # Performance level filter
        control_layout.addWidget(QtWidgets.QLabel("Performance:"), 1, 0)
        self.performance_combo = QtWidgets.QComboBox()
        self.performance_combo.addItems(["All", "Excellent", "Good", "Average", "Poor"])
        self.performance_combo.currentTextChanged.connect(self.apply_filters)
        control_layout.addWidget(self.performance_combo, 1, 1)

        # Sort options
        control_layout.addWidget(QtWidgets.QLabel("Sort by:"), 1, 2)
        self.sort_combo = QtWidgets.QComboBox()
        self.sort_combo.addItems(["N-gram Text", "Speed", "Sample Count", "Performance"])
        self.sort_combo.setCurrentText("Speed")
        self.sort_combo.currentTextChanged.connect(self.apply_filters)
        control_layout.addWidget(self.sort_combo, 1, 3)

        # No action buttons here - moved to dialog button box

        control_group.setLayout(control_layout)
        parent_layout.addWidget(control_group)

    def setup_heatmap_area(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        """Set up the heatmap visualization area."""
        heatmap_group = QtWidgets.QGroupBox("N-gram Speed Heatmap")
        heatmap_layout = QtWidgets.QVBoxLayout()

        # Create table widget for heatmap display
        self.heatmap_table = QtWidgets.QTableWidget()
        self.heatmap_table.setColumnCount(6)
        self.heatmap_table.setHorizontalHeaderLabels(
            ["N-gram", "Size", "Avg Speed (ms)", "Sample Count", "Performance", "Color"]
        )

        # Configure table appearance
        self.heatmap_table.setAlternatingRowColors(True)
        self.heatmap_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.heatmap_table.setSortingEnabled(True)

        # Auto-resize columns
        header = self.heatmap_table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(5):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        heatmap_layout.addWidget(self.heatmap_table)

        # Legend
        legend_layout = QtWidgets.QHBoxLayout()
        legend_layout.addWidget(QtWidgets.QLabel("Performance Legend:"))

        # Color legend items
        legend_colors = [
            ("Excellent", "#4CAF50"),  # Green
            ("Good", "#8BC34A"),  # Light Green
            ("Average", "#FFC107"),  # Yellow
            ("Poor", "#F44336"),  # Red
        ]

        for label, color in legend_colors:
            legend_item = QtWidgets.QLabel(label)
            legend_item.setStyleSheet(
                f"background-color: {color}; padding: 2px 8px; border-radius: 3px; color: white;"
            )
            legend_layout.addWidget(legend_item)

        legend_layout.addStretch()
        heatmap_layout.addLayout(legend_layout)

        heatmap_group.setLayout(heatmap_layout)
        parent_layout.addWidget(heatmap_group)

    def load_data(self) -> None:
        """Load n-gram heatmap data from the analytics service."""
        try:
            self.status_label.setText("Loading data...")
            QtWidgets.QApplication.processEvents()

            if self.ngram_size_combo.currentText() == "All":
                ngram_size_filter = None
            else:
                ngram_size_filter = int(self.ngram_size_combo.currentText())

            if self.sort_combo.currentText() == "N-gram Text":
                sort_by = "ngram_text"
            elif self.sort_combo.currentText() == "Speed":
                sort_by = "decaying_average_ms"
            elif self.sort_combo.currentText() == "Sample Count":
                sort_by = "sample_count"
            else:
                sort_by = None

            # Get heatmap data from analytics service
            self.heatmap_data = self.analytics_service.get_speed_heatmap_data(
                user_id=self.user.user_id,
                keyboard_id=self.keyboard.keyboard_id,
                ngram_size_filter=ngram_size_filter,
                sort_order=sort_by,
            )

            self.filtered_data = self.heatmap_data.copy()
            self.update_table()
            self.status_label.setText(f"Loaded {len(self.heatmap_data)} n-grams")

        except Exception as e:
            self.status_label.setText(f"Error loading data: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Data Load Error", f"Failed to load heatmap data: {str(e)}"
            )

    def apply_filters(self) -> None:
        """Apply current filter settings to the heatmap data."""

        self.load_data()

        # Get filter values
        min_speed = self.speed_min_spin.value()
        max_speed = self.speed_max_spin.value()
        ngram_size = self.ngram_size_combo.currentData()

        # Update display
        self.update_heatmap_display()

        # Update status
        total_count = len(self.heatmap_data)
        filtered_count = len(self.filtered_data)
        self.status_label.setText(f"Showing {filtered_count} of {total_count} n-grams")

    def refresh_data(self) -> None:
        """Refresh the heatmap data from the database."""
        self.status_label.setText("Refreshing data...")
        try:
            self.load_data()
            self.status_label.setText("Data refreshed successfully")
        except Exception as e:
            self.status_label.setText(f"Error refreshing data: {str(e)}")

    def export_data(self) -> None:
        """Export the current heatmap data to a CSV file."""
        if not self.filtered_data:
            QtWidgets.QMessageBox.information(self, "No Data", "No data to export.")
            return

        # Get save file path
        default_filename = f"ngram_heatmap_{self.user.user_id}_{self.keyboard.keyboard_id}.csv"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Heatmap Data", default_filename, "CSV files (*.csv)"
        )

        if not file_path:
            return

        try:
            import csv

            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)

                # Write header
                writer.writerow(
                    [
                        "N-gram",
                        "Size",
                        "Average Speed (ms)",
                        "Target Speed (ms)",
                        "Meets Target",
                        "Sample Count",
                        "Last Updated",
                    ]
                )

                # Write data rows
                for item in self.filtered_data:
                    writer.writerow(
                        [
                            item.ngram_text,
                            item.ngram_size,
                            f"{item.average_speed_ms:.2f}",
                            f"{item.target_speed_ms:.2f}",
                            "Yes" if item.meets_target else "No",
                            item.sample_count,
                            item.last_updated.strftime("%Y-%m-%d %H:%M:%S")
                            if item.last_updated
                            else "N/A",
                        ]
                    )

            self.status_label.setText(f"Data exported to {file_path}")
            QtWidgets.QMessageBox.information(
                self,
                "Export Complete",
                f"Data exported successfully to {os.path.basename(file_path)}",
            )
        except Exception as e:
            self.status_label.setText(f"Export failed: {str(e)}")
            QtWidgets.QMessageBox.critical(
                self, "Export Error", f"Failed to export data:\n{str(e)}"
            )

    def update_heatmap_display(self) -> None:
        """Update the heatmap table display."""
        # Sort data
        sort_by = self.sort_combo.currentText()
        if sort_by == "N-gram Text":
            self.filtered_data.sort(key=lambda x: x.ngram_text)
        elif sort_by == "Speed":
            self.filtered_data.sort(key=lambda x: x.decaying_average_ms)
        elif sort_by == "Sample Count":
            self.filtered_data.sort(key=lambda x: x.sample_count, reverse=True)
        elif sort_by == "Performance":
            perf_order = {"green": 1, "amber": 2, "grey": 3}
            self.filtered_data.sort(key=lambda x: perf_order.get(x.performance_category, 4))

        self.update_table()

    def update_table(self) -> None:
        """Update the heatmap table with filtered data."""
        self.heatmap_table.setRowCount(len(self.filtered_data))

        for row, item in enumerate(self.filtered_data):
            # N-gram text
            self.heatmap_table.setItem(row, 0, QtWidgets.QTableWidgetItem(item.ngram_text))

            # Size
            self.heatmap_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item.ngram_size)))

            # Average speed
            speed_item = QtWidgets.QTableWidgetItem(f"{item.decaying_average_ms:.1f}")
            speed_item.setData(QtCore.Qt.ItemDataRole.UserRole, item.decaying_average_ms)
            self.heatmap_table.setItem(row, 2, speed_item)

            # Sample count
            count_item = QtWidgets.QTableWidgetItem(str(item.sample_count))
            count_item.setData(QtCore.Qt.ItemDataRole.UserRole, item.sample_count)
            self.heatmap_table.setItem(row, 3, count_item)

            # Performance level - map category to display text
            perf_display = {"green": "Excellent", "amber": "Average", "grey": "Poor"}
            display_text = perf_display.get(item.performance_category, "Unknown")
            self.heatmap_table.setItem(row, 4, QtWidgets.QTableWidgetItem(display_text))

            # Color indicator
            color_item = QtWidgets.QTableWidgetItem("●")
            color_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            # Set color based on performance category
            if item.performance_category == "green":
                color_item.setForeground(QtGui.QColor("#4CAF50"))
            elif item.performance_category == "amber":
                color_item.setForeground(QtGui.QColor("#FFC107"))
            else:  # grey
                color_item.setForeground(QtGui.QColor("#F44336"))

            self.heatmap_table.setItem(row, 5, color_item)
