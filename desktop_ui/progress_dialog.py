"""Progress dialog for recent improvements and unmet-target trends.

This PySide6 dialog uses ``NGramAnalyticsService`` to:
- Compare the last two sessions and list the 3 most and least improved n-grams
- Show over the last 20 sessions the count of unique n-grams not meeting target

If QtCharts is unavailable, a table fallback is used for the trend.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    # Optional chart support
    from PySide6.QtCharts import (
        QBarCategoryAxis,
        QBarSeries,
        QBarSet,
        QChart,
        QChartView,
        QValueAxis,
    )

    HAS_CHARTS = True
except Exception:  # pragma: no cover - environment dependent
    HAS_CHARTS = False

from db.database_manager import DatabaseManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


class ProgressDialog(QDialog):
    """Dialog that displays recent improvements and progress trend.

    Args:
        db_manager: Active DatabaseManager instance
        user_id: Selected user id
        keyboard_id: Selected keyboard id
        parent: Parent widget
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        user_id: str,
        keyboard_id: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the dialog and load data.

        Args:
            db_manager: Active database connection/manager.
            user_id: Current user identifier.
            keyboard_id: Current keyboard identifier.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.keyboard_id = keyboard_id

        self.setWindowTitle("Recent Progress")
        self.setMinimumSize(800, 600)
        # Context help button off
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        # Services
        self._analytics = NGramAnalyticsService(self.db_manager, NGramManager())

        # UI pieces
        # Columns: N-gram | Size | Improvement (ms) | Before (ms) | After (ms)
        self.top_table = QTableWidget(0, 5)
        self.bottom_table = QTableWidget(0, 5)
        self.trend_container: Optional[QWidget] = None
        self.imp_group: Optional[QGroupBox] = None

        self._build_ui()
        self._load_data()
        # Start maximized per requirement
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Improvements group
        imp_group = QGroupBox("Improvements: Last 2 Sessions")
        self.imp_group = imp_group
        imp_layout = QGridLayout(imp_group)

        self.top_table.setHorizontalHeaderLabels(
            ["N-gram", "Size", "Improvement (ms)", "Before (ms)", "After (ms)"]
        )
        self.top_table.verticalHeader().setVisible(False)
        self.top_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.bottom_table.setHorizontalHeaderLabels(
            ["N-gram", "Size", "Improvement (ms)", "Before (ms)", "After (ms)"]
        )
        self.bottom_table.verticalHeader().setVisible(False)
        self.bottom_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        imp_layout.addWidget(QLabel("Top 3 Most Improved"), 0, 0)
        imp_layout.addWidget(QLabel("Bottom 3 (Least/Negative)"), 0, 1)
        imp_layout.addWidget(self.top_table, 1, 0)
        imp_layout.addWidget(self.bottom_table, 1, 1)

        # Prevent the top group from expanding vertically; it will auto-size to content
        imp_policy = imp_group.sizePolicy()
        imp_policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
        imp_group.setSizePolicy(imp_policy)
        # Ensure tables don't expand vertically
        for tbl in (self.top_table, self.bottom_table):
            pol = tbl.sizePolicy()
            pol.setVerticalPolicy(QSizePolicy.Policy.Fixed)
            tbl.setSizePolicy(pol)
        # Avoid layout row stretch within the improvements group
        imp_layout.setRowStretch(0, 0)
        imp_layout.setRowStretch(1, 0)

        # Trend group
        trend_group = QGroupBox(
            "Over Last 20 Sessions: Count of Unique N-grams Not Meeting Target"
        )
        trend_layout = QVBoxLayout(trend_group)

        if HAS_CHARTS:
            self.trend_container = self._create_chart_placeholder()
        else:
            # Fallback: simple table
            self.trend_container = QTableWidget(0, 2)
            self.trend_container.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            assert isinstance(self.trend_container, QTableWidget)
            self.trend_container.setHorizontalHeaderLabels(
                ["Session Time", "Not Meeting Target (count)"]
            )
            self.trend_container.verticalHeader().setVisible(False)

        trend_layout.addWidget(self.trend_container)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout.addWidget(imp_group)
        layout.addWidget(trend_group)
        layout.addWidget(buttons)

        # Make bottom graph expand and top group remain compact
        layout.setStretch(0, 0)   # imp_group
        layout.setStretch(1, 1)   # trend_group (expands)
        layout.setStretch(2, 0)   # buttons

    def _create_chart_placeholder(self) -> QWidget:
        # Prepare empty chart
        chart = QChart()
        chart.setTitle("Not Meeting Target (last 20 sessions)")
        view = QChartView(chart)
        view.setRenderHint(view.renderHints())
        return view

    def _load_data(self) -> None:
        # Load improvements
        # Use detailed variant to include previous/current decayed averages for display
        top3, bottom3 = self._analytics.get_top_and_bottom_improvements_last_two_sessions_detailed(
            user_id=self.user_id,
            keyboard_id=self.keyboard_id,
            top_n=3,
        )
        self._populate_improvements_detailed(self.top_table, top3)
        self._populate_improvements_detailed(self.bottom_table, bottom3)
        # Auto-size the improvements tables and group to their content (3 rows)
        self._fit_table_height(self.top_table)
        self._fit_table_height(self.bottom_table)
        if self.imp_group is not None:
            self.imp_group.adjustSize()
        self.adjustSize()

        # Load trend data
        series = self._analytics.get_not_meeting_target_counts_last_n_sessions(
            user_id=self.user_id, keyboard_id=self.keyboard_id, n_sessions=20
        )
        self._populate_trend(series)

    def _populate_improvements_detailed(
        self,
        table: QTableWidget,
        rows: List[Tuple[str, int, float, float, float]],
    ) -> None:
        """Populate improvement tables with detailed before/after columns.

        Each row tuple is: (ngram_text, ngram_size, improvement_ms, prev_ms, recent_ms)
        """
        table.setRowCount(0)
        if not rows:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem("No data"))
            table.setItem(0, 1, QTableWidgetItem("-"))
            table.setItem(0, 2, QTableWidgetItem("-"))
            table.setItem(0, 3, QTableWidgetItem("-"))
            table.setItem(0, 4, QTableWidgetItem("-"))
            return

        table.setRowCount(len(rows))
        for r, (ng, size, imp, prev_ms, recent_ms) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(ng))
            table.setItem(r, 1, QTableWidgetItem(str(size)))
            imp_item = QTableWidgetItem(f"{imp:.2f}")
            # Colorize: green for positive improvements, red for regressions
            if imp > 0:
                imp_item.setForeground(QColor("green"))
            elif imp < 0:
                imp_item.setForeground(QColor("red"))
            table.setItem(r, 2, imp_item)
            table.setItem(r, 3, QTableWidgetItem(f"{prev_ms:.2f}"))
            table.setItem(r, 4, QTableWidgetItem(f"{recent_ms:.2f}"))

    def _fit_table_height(self, table: QTableWidget) -> None:
        """Set the table height to fit its header and current rows exactly (no vertical scroll).

        Assumes a small, fixed number of rows (3). This helps the top box auto-size
        to content and prevents it from growing with window size.
        """
        # Disable vertical scrollbar to avoid extra space calculations
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header_h = table.horizontalHeader().height() if table.horizontalHeader() else 0
        rows_h = sum(table.rowHeight(i) for i in range(table.rowCount()))
        frame = table.frameWidth() * 2
        # Some padding to avoid clipping bottom border
        total_h = header_h + rows_h + frame + 4
        table.setFixedHeight(max(0, total_h))

    def _populate_trend(self, series: List[Tuple[str, int]]) -> None:
        if HAS_CHARTS and isinstance(self.trend_container, QChartView):
            chart = self.trend_container.chart()
            chart.removeAllSeries()

            # Build a simple bar chart
            counts = [cnt for _, cnt in series]
            labels = [dt for dt, _ in series]

            bar_set = QBarSet("Not Meeting Target")
            for c in counts:
                bar_set.append(float(c))

            bar_series = QBarSeries()
            bar_series.append(bar_set)

            chart.addSeries(bar_series)

            axis_x = QBarCategoryAxis()
            # To avoid overcrowding, we must still provide one category per bar.
            # Provide sparse labels by blanking most labels but preserving length.
            if labels:
                step = max(1, len(labels) // 10)
                categories = [
                    (labels[i] if i % step == 0 else "") for i in range(len(labels))
                ]
                axis_x.append(categories)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            bar_series.attachAxis(axis_x)

            axis_y = QValueAxis()
            axis_y.setTitleText("Count")
            axis_y.setLabelFormat("%d")
            axis_y.setRange(0, max(counts) if counts else 1)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            bar_series.attachAxis(axis_y)

            chart.legend().setVisible(True)
            chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        else:
            # Fallback table rendering
            assert isinstance(self.trend_container, QTableWidget)
            table = self.trend_container
            table.setRowCount(0)
            if not series:
                table.setRowCount(1)
                table.setItem(0, 0, QTableWidgetItem("No sessions found"))
                table.setItem(0, 1, QTableWidgetItem("-"))
                return

            table.setRowCount(len(series))
            for r, (dt, cnt) in enumerate(series):
                table.setItem(r, 0, QTableWidgetItem(dt))
                table.setItem(r, 1, QTableWidgetItem(str(cnt)))
