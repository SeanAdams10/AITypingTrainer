"""
ScaffoldBulkInsertPerformance UI form for benchmarking bulk insert strategies on Aurora PostgreSQL.

This screen connects to the cloud database, creates a temporary test table
`test_bulk_performance`, runs timed inserts (10,000 rows) using several methods,
then drops the table and shows results.
"""

from __future__ import annotations

import os
import random
import string
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from PySide6 import QtWidgets
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QWidget,
)

# Ensure project root is in sys.path before any project imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.database_manager import BulkMethod, ConnectionType, DatabaseManager


@dataclass
class TimingResult:
    label: str
    rows: int
    duration_s: float


class ScaffoldBulkInsertPerformance(QWidget):
    """UI form to benchmark bulk insert performance modes."""

    ROWS_TO_INSERT = 10_000
    TABLE_NAME = "test_bulk_performance"

    def __init__(self, connection_type: ConnectionType = ConnectionType.CLOUD) -> None:
        super().__init__()
        self.setWindowTitle("Bulk Insert Performance Benchmark")

        self.db = DatabaseManager(connection_type=connection_type)

        self.results: List[TimingResult] = []

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)

        header = QLabel("Benchmark inserts using different methods on Aurora Postgres")
        header.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.run_btn = QPushButton("Run Benchmark")
        self.run_btn.clicked.connect(self.on_run)

        rows_label = QLabel("Rows to insert:")
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10_000_000)
        self.rows_spin.setSingleStep(1000)
        self.rows_spin.setValue(self.ROWS_TO_INSERT)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(220)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Method", "Rows", "Seconds"])
        self.table.horizontalHeader().setStretchLastSection(True)

        box = QGroupBox("Results")
        box_layout = QGridLayout(box)
        box_layout.addWidget(self.table, 0, 0)

        layout.addWidget(header, 0, 0, 1, 3)
        layout.addWidget(rows_label, 1, 0)
        layout.addWidget(self.rows_spin, 1, 1)
        layout.addWidget(self.run_btn, 1, 2)
        layout.addWidget(self.log, 2, 0, 1, 3)
        layout.addWidget(box, 3, 0, 1, 3)

        self.setLayout(layout)
        self.resize(800, 600)

    # ----------------------- DB helpers -----------------------
    def _exec(self, sql: str, params: Tuple[object, ...] = ()) -> None:
        self.db.execute(sql, params)

    def _create_table(self) -> None:
        # Explicit Postgres types
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
            id UUID PRIMARY KEY,
            note TEXT NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            score INTEGER NOT NULL
        )
        """
        self._exec(ddl)

    def _drop_table(self) -> None:
        self._exec(f"DROP TABLE IF EXISTS {self.TABLE_NAME}")

    def _random_rows(self, n: int) -> List[Tuple[object, ...]]:
        rows: List[Tuple[object, ...]] = []
        for _ in range(n):
            uid = str(uuid4())
            note = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            ts = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for Postgres timestamp
            score = random.randint(0, 1000)
            rows.append((uid, note, ts, score))
        return rows

    def _timeit(self, label: str, func, rows_count: int) -> float:
        t0 = time.perf_counter()
        func()
        t1 = time.perf_counter()
        dt = t1 - t0
        self.results.append(TimingResult(label, rows_count, dt))
        self.log.append(f"{label}: {dt:.3f}s")
        return dt

    def _append_table_row(self, res: TimingResult) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(res.label))
        self.table.setItem(r, 1, QTableWidgetItem(str(res.rows)))
        self.table.setItem(r, 2, QTableWidgetItem(f"{res.duration_s:.3f}"))

    def _clear_previous(self) -> None:
        self.results.clear()
        self.table.setRowCount(0)
        self.log.clear()

    # ----------------------- Benchmark actions -----------------------
    def on_run(self) -> None:
        self.run_btn.setEnabled(False)
        self._clear_previous()
        try:
            self.log.append("Connecting to cloud DB and preparing table...")
            # Ensure fresh table
            self._drop_table()
            self._create_table()

            # Determine number of rows from UI
            rows_count = int(self.rows_spin.value())
            rows = self._random_rows(rows_count)

            insert_sql_qmarks = (
                f"INSERT INTO {self.TABLE_NAME} (id, note, created_at, score) VALUES (?, ?, ?, ?)"
            )

            # 1) execute (single row loop)
            def do_execute() -> None:
                for row in rows:
                    self._exec(insert_sql_qmarks, row)

            # 2) execute_many AUTO
            def do_auto() -> None:
                self.db.execute_many(insert_sql_qmarks, rows, method=BulkMethod.AUTO)

            # 3) execute_many COPY
            def do_copy() -> None:
                self.db.execute_many(insert_sql_qmarks, rows, method=BulkMethod.COPY)

            # 4) execute_many EXECUTEMANY
            def do_executemany() -> None:
                self.db.execute_many(insert_sql_qmarks, rows, method=BulkMethod.EXECUTEMANY)

            # 5) execute_many VALUES
            def do_values() -> None:
                self.db.execute_many(insert_sql_qmarks, rows, method=BulkMethod.VALUES)

            self.log.append("Running benchmarks (this may take a bit)...\n")

            # Helper: clear table between tests (not timed)
            def _clear_table() -> None:
                try:
                    if getattr(self.db, "is_postgres", False):
                        # Use schema-qualified TRUNCATE for speed
                        self.db.execute(f"TRUNCATE {self.db.SCHEMA_NAME}.{self.TABLE_NAME}")
                    else:
                        self.db.execute(f"DELETE FROM {self.TABLE_NAME}")
                except Exception as e:
                    self.log.append(f"Warning: failed to clear table: {e}")

            self._timeit("execute (loop)", do_execute, rows_count)
            _clear_table()

            self._timeit("execute_many AUTO", do_auto, rows_count)
            _clear_table()

            self._timeit("execute_many COPY", do_copy, rows_count)
            _clear_table()

            self._timeit("execute_many EXECUTEMANY", do_executemany, rows_count)
            _clear_table()

            self._timeit("execute_many VALUES", do_values, rows_count)

            # Show results in table
            for res in self.results:
                self._append_table_row(res)

        except Exception as e:
            self.log.append(f"\nERROR: {e}")
        finally:
            # Cleanup table and close connection
            try:
                self._drop_table()
            except Exception as drop_exc:
                self.log.append(f"Cleanup drop failed: {drop_exc}")
            try:
                self.db.close()
            except Exception as close_exc:
                self.log.append(f"Close failed: {close_exc}")
            self.run_btn.setEnabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt signature)
        try:
            self.db.close()
        except Exception:
            pass
        event.accept()


def launch_scaffold_bulk_insert_performance() -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    window = ScaffoldBulkInsertPerformance()
    window.show()

    if app is not None:
        app.exec()


if __name__ == "__main__":
    launch_scaffold_bulk_insert_performance()
