"""ProgressDialog: Desktop UI dialog for n-gram progress and trend analysis.

Implements user-driven, configurable analysis of n-gram progress and trends.
Supports dynamic filtering and historical analysis for improved feedback and training.

Features:
- Top controls for minimum occurrences and included keys (settings-backed)
- Grids for most improved and most degraded n-grams (last two sessions)
- Historical trend chart/table for missed targets (last 20 sessions)
- All code passes mypy and ruff checks
"""

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
	QDialog,
	QDialogButtonBox,
	QGridLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QSizePolicy,
	QSpinBox,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)

try:
	from PySide6.QtCharts import (
		QChart,
		QChartView,
		QBarSet,
		QBarSeries,
		QBarCategoryAxis,
		QValueAxis,
	)
	HAS_CHARTS = True
except Exception:
	HAS_CHARTS = False

from db.database_manager import DatabaseManager
from models.setting_manager import SettingManager
from models.ngram_analytics_service import NGramAnalyticsService
from models.ngram_manager import NGramManager


class ProgressDialog(QDialog):
	"""Dialog for n-gram progress and trend analysis."""

	def __init__(
		self,
		db_manager: DatabaseManager,
		setting_manager: SettingManager,
		user_id: str,
		keyboard_id: str,
		parent: Optional[QWidget] = None,
	) -> None:
		"""Initialize ProgressDialog.

		Args:
			db_manager: DatabaseManager instance for DB access.
			setting_manager: SettingManager instance for settings.
			user_id: User identifier.
			keyboard_id: Keyboard identifier.
			parent: Optional parent widget.
		"""
		super().__init__(parent)
		self.db_manager = db_manager
		self.setting_manager = setting_manager
		self.user_id = user_id
		self.keyboard_id = keyboard_id

		# Initialize analytics service
		ngram_manager = NGramManager(db_manager)
		self.analytics_service = NGramAnalyticsService(db_manager, ngram_manager)

		self.setWindowTitle("Progress & Trends")
		self.setMinimumSize(1200, 800)
		self.showMaximized()  # Start maximized to fill screen
		self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

		self.min_occ_spin = QSpinBox()
		self.min_occ_spin.setRange(1, 1000)
		self.keys_edit = QLineEdit()
		self.keys_edit.setPlaceholderText("Enter included keys")

		self.top_table = QTableWidget(0, 5)
		self.bottom_table = QTableWidget(0, 5)
		self.trend_widget: Optional[QWidget] = None

		self._build_ui()
		self._load_settings()
		self._reload_all()

		self.min_occ_spin.valueChanged.connect(self._on_controls_changed)
		self.keys_edit.textChanged.connect(self._on_controls_changed)

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		controls_layout = QHBoxLayout()
		controls_layout.addWidget(QLabel("Min Occurrences:"))
		controls_layout.addWidget(self.min_occ_spin)
		controls_layout.addWidget(QLabel("Included Keys:"))
		controls_layout.addWidget(self.keys_edit)
		layout.addLayout(controls_layout)

		imp_group = QGroupBox("Improvements: Last 2 Sessions")
		imp_layout = QGridLayout(imp_group)
		self.top_table.setHorizontalHeaderLabels([
			"N-gram", "Size", "Improvement (ms)", "Before (ms)", "After (ms)"
		])
		self.top_table.verticalHeader().setVisible(False)
		self.top_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.bottom_table.setHorizontalHeaderLabels([
			"N-gram", "Size", "Improvement (ms)", "Before (ms)", "After (ms)"
		])
		self.bottom_table.verticalHeader().setVisible(False)
		self.bottom_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		
		# Set fixed height for the tables - don't expand vertically
		self.top_table.setFixedHeight(200)
		self.bottom_table.setFixedHeight(200)
		
		imp_layout.addWidget(QLabel("Top 3 Most Improved"), 0, 0)
		imp_layout.addWidget(QLabel("Bottom 3 Most Degraded"), 0, 1)
		imp_layout.addWidget(self.top_table, 1, 0)
		imp_layout.addWidget(self.bottom_table, 1, 1)
		
		# Make both columns expand equally to fill available space horizontally
		imp_layout.setColumnStretch(0, 1)
		imp_layout.setColumnStretch(1, 1)
		
		# Set size policy to expand horizontally only, fixed height
		imp_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

		trend_group = QGroupBox("Missed Targets Trend (Last 20 Sessions)")
		trend_layout = QVBoxLayout(trend_group)
		if HAS_CHARTS:
			chart = QChart()
			chart.setTitle("Missed Targets Trend")
			self.trend_widget = QChartView(chart)
		else:
			table = QTableWidget(0, 2)
			table.setHorizontalHeaderLabels(["Session Time", "Missed Targets"])
			table.verticalHeader().setVisible(False)
			table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
			self.trend_widget = table
		trend_layout.addWidget(self.trend_widget)

		buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		buttons.rejected.connect(self.reject)
		buttons.accepted.connect(self.accept)

		layout.addWidget(imp_group)
		layout.addWidget(trend_group)
		layout.addWidget(buttons)
		
		# Set stretch factors to control how space is distributed
		layout.setStretch(0, 0)  # Controls (fixed size)
		layout.setStretch(1, 0)  # Improvements section (fixed height)
		layout.setStretch(2, 1)  # Trend section (gets all the remaining vertical space)
		layout.setStretch(3, 0)  # Buttons (fixed size)

	def _load_settings(self) -> None:
		min_occ_setting = self.setting_manager.get_setting("NGRMOC", self.keyboard_id, "5")
		included_keys_setting = self.setting_manager.get_setting(
			"NGRKEY", self.keyboard_id, "abcdefghijklmnopqrstuvwxyz"
		)
		self.min_occ_spin.setValue(int(min_occ_setting.setting_value))
		self.keys_edit.setText(str(included_keys_setting.setting_value))

	def _save_settings(self) -> None:
		from models.setting import Setting
		from uuid import uuid4
		
		# Save minimum occurrences setting
		min_occ_setting = Setting(
			setting_id=str(uuid4()),
			setting_type_id="NGRMOC",
			setting_value=str(self.min_occ_spin.value()),
			related_entity_id=self.keyboard_id,
		)
		self.setting_manager.save_setting(min_occ_setting)
		
		# Save included keys setting
		keys_setting = Setting(
			setting_id=str(uuid4()),
			setting_type_id="NGRKEY",
			setting_value=self.keys_edit.text(),
			related_entity_id=self.keyboard_id,
		)
		self.setting_manager.save_setting(keys_setting)

	def _on_controls_changed(self) -> None:
		self._save_settings()
		self._reload_all()

	def _reload_all(self) -> None:
		min_occ = self.min_occ_spin.value()
		included_keys = self.keys_edit.text()
		# Improvements
		top3, bottom3 = self._get_session_comparison(min_occ, included_keys)
		self._populate_table(self.top_table, top3)
		self._populate_table(self.bottom_table, bottom3)
		# Trend
		trend_data = self._get_trend_data(min_occ, included_keys)
		self._populate_trend(trend_data)

	def _get_session_comparison(
		self,
		min_occ: int,
		included_keys: str,
	) -> Tuple[List[List[str | int | float]], List[List[str | int | float]]]:
		"""Get session performance comparison using analytics service.

		Args:
			min_occ: Minimum occurrence threshold.
			included_keys: String of allowed characters for filtering.

		Returns:
			Tuple of (top3_improved, bottom3_degraded) lists.
			Each row: [ngram, size, improvement, before, after]
		"""
		# Use the new analytics service method
		comparisons = self.analytics_service.get_session_performance_comparison(
			keyboard_id=self.keyboard_id,
			keys=included_keys,
			occurrences=min_occ
		)

		if not comparisons:
			return [], []

		# Filter to only include n-grams that have both previous and current data
		valid_comparisons = [
			comp for comp in comparisons 
			if comp.prev_perf is not None and comp.delta_perf is not None
		]

		if not valid_comparisons:
			return [], []

		# Convert to the expected format: [ngram, size, improvement, before, after]
		formatted_data = []
		for comp in valid_comparisons:
			row = [
				comp.ngram_text,
				len(comp.ngram_text),  # ngram size
				comp.delta_perf,  # improvement (prev - latest)
				comp.prev_perf,   # before (previous performance)
				comp.latest_perf  # after (latest performance)
			]
			formatted_data.append(row)

		# Sort by improvement (delta_perf) descending for top improvements
		formatted_data.sort(key=lambda x: x[2], reverse=True)
		
		# Get top 3 improvements and bottom 3 (which could be degradations)
		top3 = formatted_data[:3]
		bottom3 = formatted_data[-3:] if len(formatted_data) >= 3 else []

		return top3, bottom3

	def _get_trend_data(self, min_occ: int, included_keys: str) -> List[Tuple[str, int]]:
		"""
		Query the database for missed targets trend over last 20 sessions using the provided SQL.
		Returns list of (session_time, missed_count)
		"""
		sql = '''
		WITH in_scope_sessions AS (
			SELECT
				ps.session_id,
				ps.start_time,
				ps.keyboard_id
			FROM practice_sessions AS ps
			WHERE ps.keyboard_id = ?
			ORDER BY ps.start_time DESC
			LIMIT 20
		),
		session_match AS (
			SELECT
				ps.session_id,
				ps.start_time AS session_dt,
				nssh.history_id,
				nssh.ngram_text,
				nssh.updated_dt AS history_dt,
				nssh.meets_target,
				nssh.sample_count,
				ROW_NUMBER() OVER (
					PARTITION BY nssh.keyboard_id, nssh.ngram_text, ps.session_id
					ORDER BY nssh.updated_dt DESC
				) AS rownum
			FROM ngram_speed_summary_hist AS nssh
			INNER JOIN in_scope_sessions AS ps
				ON nssh.updated_dt <= ps.start_time
			   AND nssh.keyboard_id = ps.keyboard_id
			WHERE nssh.ngram_text ~ ?
			ORDER BY
				ps.session_id,
				nssh.updated_dt DESC,
				ps.start_time
		)
		SELECT
			sm.session_id,
			sm.session_dt,
			SUM(1-sm.meets_target) AS miss_count
		FROM session_match AS sm
		WHERE 
			sm.rownum = 1
			and sample_count >= ?
		GROUP BY sm.session_id, sm.session_dt
		ORDER BY sm.session_dt DESC;
		'''
		regex = f"^[{included_keys}]+$"
		rows = self.db_manager.fetchall(sql, (self.keyboard_id, regex, min_occ))
		return [(str(row["session_dt"]), int(row["miss_count"])) for row in rows]

	def _populate_table(self, table: QTableWidget, rows: List[List[str | int | float]]) -> None:
		table.setRowCount(0)
		if not rows:
			table.setRowCount(1)
			for c in range(5):
				table.setItem(0, c, QTableWidgetItem("-"))
			return
		table.setRowCount(len(rows))
		for r, row in enumerate(rows):
			for c, val in enumerate(row):
				table.setItem(r, c, QTableWidgetItem(str(val)))

	def _populate_trend(self, series: List[Tuple[str, int]]) -> None:
		if HAS_CHARTS and isinstance(self.trend_widget, QChartView):
			chart = self.trend_widget.chart()
			chart.removeAllSeries()
			bar_set = QBarSet("Missed Targets")
			for _, cnt in series:
				bar_set.append(float(cnt))
			bar_series = QBarSeries()
			bar_series.append(bar_set)
			chart.addSeries(bar_series)
			axis_x = QBarCategoryAxis()
			axis_x.append([dt for dt, _ in series])
			chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
			bar_series.attachAxis(axis_x)
			axis_y = QValueAxis()
			axis_y.setTitleText("Count")
			axis_y.setRange(0, max(cnt for _, cnt in series) if series else 1)
			chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
			bar_series.attachAxis(axis_y)
		elif isinstance(self.trend_widget, QTableWidget):
			table = self.trend_widget
			table.setRowCount(0)
			if not series:
				table.setRowCount(1)
				table.setItem(0, 0, QTableWidgetItem("No data"))
				table.setItem(0, 1, QTableWidgetItem("-"))
				return
			table.setRowCount(len(series))
			for r, (dt, cnt) in enumerate(series):
				table.setItem(r, 0, QTableWidgetItem(dt))
				table.setItem(r, 1, QTableWidgetItem(str(cnt)))
