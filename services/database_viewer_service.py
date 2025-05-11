from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError
import sqlite3
import csv
from io import StringIO


class TableDataRequest(BaseModel):
    table_name: str
    page: int = 1
    page_size: int = 50
    sort_by: Optional[str] = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
    filters: Optional[Dict[str, Any]] = None


class DatabaseViewerService:
    """
    Service for database viewing operations: list tables, fetch data (with pagination, sorting, filtering), export CSV.
    """

    def __init__(self, db_connection_provider):
        self.get_connection = db_connection_provider

    def list_tables(self) -> List[str]:
        """Return a list of table names in the database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        with open("dbviewer_list_tables_debug.txt", "a") as f:
            f.write(f"list_tables found: {tables}\n")
        print(f"[DBVIEWER DEBUG] list_tables found: {tables}")
        conn.close()
        return tables

    def fetch_table_data(
        self, req: TableDataRequest
    ) -> Tuple[List[str], List[Dict[str, str]], int]:
        """Fetch table data with pagination, sorting, and filtering."""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Validate table name
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (req.table_name,),
        )
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Table '{req.table_name}' not found.")
        # Get columns
        cursor.execute(f"PRAGMA table_info({req.table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        columns_str = [str(c) for c in columns]
        # Build query
        sql = f"SELECT * FROM {req.table_name}"
        params: List[Any] = []
        # Filtering
        where_clauses = []
        if req.filters:
            for col, val in req.filters.items():
                if col in columns:
                    where_clauses.append(f"{col} LIKE ?")
                    params.append(f"%{val}%")
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        # Sorting
        if req.sort_by and req.sort_by in columns:
            sql += f" ORDER BY {req.sort_by} {req.sort_order.upper()}"
        # Pagination
        offset = (req.page - 1) * req.page_size
        sql += f" LIMIT ? OFFSET ?"
        params.extend([req.page_size, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        # Get total count for pagination
        count_sql = f"SELECT COUNT(*) FROM {req.table_name}"
        count_params = []
        if where_clauses:
            count_sql += " WHERE " + " AND ".join(where_clauses)
            count_params = params[:-2]  # Exclude LIMIT/OFFSET
        cursor.execute(count_sql, count_params)
        total_count = cursor.fetchone()[0]
        conn.close()
        row_dicts = [
            {str(k): str(v) if v is not None else "" for k, v in zip(columns_str, row)}
            for row in rows
        ]
        return columns_str, row_dicts, total_count

    def export_csv(self, req: TableDataRequest) -> str:
        """Export the current (filtered) table view to CSV (returns CSV string)."""
        columns, rows, _ = self.fetch_table_data(req)
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue()
