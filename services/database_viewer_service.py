"""Database Viewer Service Module

This module provides functionality for viewing and exploring database tables,
including listing tables, fetching table data with pagination, sorting, filtering,
and exporting to CSV.

The service provides a read-only interface to access the database structure and content.
"""

import csv
import math
from typing import Any, Dict, List, Optional, TextIO, Union

from pydantic import BaseModel, Field

from db.database_manager import DatabaseManager


class DatabaseViewerError(Exception):
    """Base exception class for database viewer errors."""
    pass


class TableNotFoundError(DatabaseViewerError):
    """Exception raised when a requested table does not exist."""
    pass


class InvalidParameterError(DatabaseViewerError):
    """Exception raised when invalid parameters are provided."""
    pass


class TableDataRequest(BaseModel):
    """Pydantic model for table data request parameters."""
    table_name: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None


class DatabaseViewerService:
    """
    Service for database viewing operations: list tables, fetch data (with pagination,
    sorting, filtering), and export to CSV.

    This service provides a read-only interface to inspect database tables and their contents.
    It handles pagination, sorting, and filtering of data, as well as exporting to CSV format.
    All operations are performed in a secure, read-only manner with proper input validation.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the DatabaseViewerService with a database manager.

        Args:
            db_manager: An instance of DatabaseManager for database access
        """
        self.db_manager = db_manager

    def list_tables(self) -> List[str]:
        """
        Return a list of all table names in the database.

        Returns:
            A list of table names as strings
        """
        tables_query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
        rows = self.db_manager.fetchall(tables_query)
        return [row[0] for row in rows]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get schema information for the specified table.

        Args:
            table_name: The name of the table to get schema for

        Returns:
            A list of column definitions with name, type, etc.

        Raises:
            TableNotFoundError: If the specified table doesn't exist
        """
        # Verify table exists
        if not self._table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' not found")

        # Get table schema
        schema_query = f"PRAGMA table_info({table_name})"
        rows = self.db_manager.fetchall(schema_query)

        schema = []
        for row in rows:
            schema.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": row[3],
                "default_value": row[4],
                "pk": row[5]
            })

        return schema

    def get_table_data(self,
                      table_name: str,
                      page: int = 1,
                      page_size: int = 50,
                      sort_by: Optional[str] = None,
                      sort_order: str = "asc",
                      filter_column: Optional[str] = None,
                      filter_value: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch table data with pagination, sorting, and filtering.

        Args:
            table_name: Name of the table to query
            page: Page number (1-based)
            page_size: Number of rows per page
            sort_by: Column to sort by
            sort_order: Sort direction ('asc' or 'desc')
            filter_column: Column to filter on
            filter_value: Value to filter by (uses LIKE %value%)

        Returns:
            Dict containing columns, rows, pagination info, etc.

        Raises:
            TableNotFoundError: If table doesn't exist
            InvalidParameterError: If invalid parameters are provided
        """
        # Input validation
        if page < 1:
            raise InvalidParameterError("Page number must be at least 1")

        if sort_order not in ("asc", "desc"):
            raise InvalidParameterError("Sort order must be 'asc' or 'desc'")

        # Verify table exists
        if not self._table_exists(table_name):
            raise TableNotFoundError(f"Table '{table_name}' not found")

        # Get table columns
        schema = self.get_table_schema(table_name)
        columns = [col["name"] for col in schema]

        # Validate sort_by if provided
        if sort_by and sort_by not in columns:
            raise InvalidParameterError(f"Sort column '{sort_by}' not found in table '{table_name}'")

        # Validate filter_column if provided
        if filter_column and filter_column not in columns:
            raise InvalidParameterError(f"Filter column '{filter_column}' not found in table '{table_name}'")

        # Build query
        base_query = f"SELECT * FROM {table_name}"
        params: List[Any] = []

        # Add WHERE clause if filtering
        where_clause = ""
        if filter_column and filter_value is not None:
            where_clause = f"WHERE {filter_column} LIKE ?"
            params.append(f"%{filter_value}%")

        # Add ORDER BY clause if sorting
        order_clause = ""
        if sort_by:
            order_clause = f"ORDER BY {sort_by} {sort_order.upper()}"

        # Calculate pagination
        offset = (page - 1) * page_size
        limit_clause = "LIMIT ? OFFSET ?"

        # Construct full query with all clauses
        query_parts = [base_query]
        if where_clause:
            query_parts.append(where_clause)
        if order_clause:
            query_parts.append(order_clause)
        query_parts.append(limit_clause)

        query = " ".join(query_parts)
        params.extend([page_size, offset])

        # Execute query to get page data
        rows = self.db_manager.fetchall(query, tuple(params))

        # Convert rows to list of dicts
        row_dicts = []
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = row[i]
            row_dicts.append(row_dict)

        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        count_params = []
        if where_clause:
            count_query += f" {where_clause}"
            count_params = params[:-2]  # Remove LIMIT/OFFSET params

        total_rows = self.db_manager.fetchone(count_query, tuple(count_params))[0]
        total_pages = math.ceil(total_rows / page_size)

        # Return complete result
        return {
            "columns": columns,
            "rows": row_dicts,
            "total_rows": total_rows,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size
        }

    def export_table_to_csv(self,
                           table_name: str,
                           output_file: Union[str, TextIO],
                           filter_column: Optional[str] = None,
                           filter_value: Optional[str] = None) -> None:
        """
        Export the table data to CSV format.

        Args:
            table_name: Name of the table to export
            output_file: File path or file-like object to write CSV to
            filter_column: Optional column to filter on
            filter_value: Optional value to filter by

        Raises:
            TableNotFoundError: If table doesn't exist
            InvalidParameterError: If invalid parameters are provided
        """
        # Get table data without pagination to export all rows
        table_data = self.get_table_data(
            table_name=table_name,
            page=1,
            page_size=1000000,  # Large number to get all rows
            filter_column=filter_column,
            filter_value=filter_value
        )

        columns = table_data["columns"]
        rows = table_data["rows"]

        # Determine if we need to open a file or use the provided file-like object
        close_file = False
        if isinstance(output_file, str):
            f = open(output_file, 'w', newline='')
            close_file = True
        else:
            f = output_file

        try:
            # Write CSV data
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        finally:
            # Close file if we opened it
            if close_file:
                f.close()

    def _table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if the table exists, False otherwise
        """
        query = """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name=?
        """
        result = self.db_manager.fetchone(query, (table_name,))
        return result is not None
