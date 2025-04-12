"""
Table operations module for database management.
Contains operations for deleting all rows, backing up tables, and
restoring from backups.
"""
import os
import json
import sqlite3
import datetime
from typing import (
    Optional,
    Tuple,
    Callable,
    Dict,
    List,
    Any,
    TypedDict
)


class BackupData(TypedDict):
    """Dictionary representing the structure of a table backup."""

    table_name: str
    backup_date: str
    columns: List[str]
    data: List[Dict[str, Any]]


class TableOperations:
    """Class for database table operations including backup, restore, and delete."""

    def __init__(
        self,
        db_connection_provider: Callable[[], sqlite3.Connection]
    ) -> None:
        """
        Initialize with a connection provider function.

        Args:
            db_connection_provider: Function that returns a SQLite connection
        """
        self.get_connection: Callable[
            [], sqlite3.Connection
        ] = db_connection_provider
        self.backup_dir: str = "DB_Backup"

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            bool: True if table exists, False otherwise
        """
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name=?",
                (table_name,)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error checking if table exists: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def is_table_empty(self, table_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a table is empty.

        Args:
            table_name: Name of the table to check

        Returns:
            Tuple[bool, Optional[str]]: (is_empty, error_message)
                is_empty: True if table exists and is empty, False otherwise
                error_message: Error message if an error occurred, None otherwise
        """
        if not self.table_exists(table_name):
            return False, f"Table '{table_name}' not found"

        conn: Optional[sqlite3.Connection] = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            return count == 0, None
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"
        finally:
            if conn:
                conn.close()

    def delete_all_rows(self, table_name: str) -> Tuple[bool, Optional[str]]:
        """
        Delete all rows from a specified table.

        Args:
            table_name: Name of the table to delete rows from

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        if not self.table_exists(table_name):
            return False, "Table not found"

        conn: Optional[sqlite3.Connection] = None
        try:
            conn = self.get_connection()
            conn.execute("PRAGMA busy_timeout = 5000")  # 5 second timeout
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name}")
            conn.commit()

            is_empty, error = self.is_table_empty(table_name)
            if not is_empty:
                return (
                    False,
                    error or "Failed to delete all rows"
                )

            return True, None
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            return False, f"Database error: {str(e)}"
        finally:
            if conn:
                conn.close()

    def backup_table(
        self, table_name: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Backup a table to a JSON file.

        Args:
            table_name: Name of the table to backup

        Returns:
            Tuple[bool, Optional[str], Optional[str]]:
                (success, error_message, backup_file_path)
        """
        if not self.table_exists(table_name):
            return False, "Table not found", None

        conn: Optional[sqlite3.Connection] = None
        try:
            conn = self.get_connection()
            conn.execute("PRAGMA busy_timeout = 5000")
            cursor = conn.cursor()

            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [dict(row) for row in cursor.fetchall()]
            column_names = [col['name'] for col in columns]

            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            data: List[Dict[str, Any]] = []
            for row in rows:
                row_dict: Dict[str, Any] = {}
                for i, col_name in enumerate(column_names):
                    row_dict[col_name] = row[i]
                data.append(row_dict)

            if not data:
                return False, "Table has no rows to backup", None

            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)

            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"{table_name}_{current_date}.json"
            file_path = os.path.join(self.backup_dir, filename)

            backup_data: BackupData = {
                "table_name": table_name,
                "backup_date": current_date,
                "columns": column_names,
                "data": data
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)

            return True, None, os.path.abspath(file_path)
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}", None
        except Exception as e:
            return False, f"Error backing up table: {str(e)}", None
        finally:
            if conn:
                conn.close()

    def restore_table(
        self, table_name: str, backup_file_path: str
    ) -> Tuple[bool, Optional[str], int]:
        """
        Restore a table from a backup file.

        Args:
            table_name: Name of the table to restore
            backup_file_path: Path to the backup file

        Returns:
            Tuple[bool, Optional[str], int]: (success, error_message, rows_restored)
        """
        if not self.table_exists(table_name):
            return False, "Table not found", 0

        if not os.path.exists(backup_file_path):
            return False, "Backup file not found", 0

        try:
            with open(backup_file_path, 'r', encoding='utf-8') as f:
                backup_data: BackupData = json.load(f)
                
            # Validate backup data structure
            required_keys = ['table_name', 'backup_date', 'columns', 'data']
            if not all(key in backup_data for key in required_keys):
                return False, "Invalid backup file format", 0
                
        except Exception as e:
            return False, f"Invalid backup file: {str(e)}", 0

        conn: Optional[sqlite3.Connection] = None
        try:
            conn = self.get_connection()
            conn.execute("PRAGMA busy_timeout = 5000")
            cursor = conn.cursor()

            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            current_columns = [col[1] for col in columns]  # Index 1 is name

            backup_columns = backup_data["columns"]
            if set(backup_columns) != set(current_columns):
                return (
                    False,
                    "Backup columns do not match table columns",
                    0
                )

            cursor.execute("BEGIN TRANSACTION")
            cursor.execute(f"DELETE FROM {table_name}")

            data = backup_data["data"]
            if data:
                placeholders = ', '.join(['?' for _ in backup_columns])
                columns_str = ', '.join(backup_columns)

                insert_query = (
                    f"INSERT INTO {table_name} ({columns_str}) "
                    f"VALUES ({placeholders})"
                )

                for row in data:
                    values = [row[col] for col in backup_columns]
                    cursor.execute(insert_query, values)

            conn.commit()

            return True, None, len(data)
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            return False, f"Database error: {str(e)}", 0
        finally:
            if conn:
                conn.close()
