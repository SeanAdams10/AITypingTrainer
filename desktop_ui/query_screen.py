"""
SQL Query Screen for AI Typing Trainer (PySide6)

This module provides a GUI for executing custom SQL queries on the database and viewing results.
"""

from typing import Any, Dict, List, Optional

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from db.database_manager import DatabaseManager


class QueryScreen(QDialog):
    """
    Dialog for executing custom SQL queries on the database.
    
    Features:
    - User and keyboard ID display
    - SQL query input
    - Dynamic results grid
    - Error handling
    
    Args:
        db_manager: DatabaseManager instance to execute queries
        user_id: ID of the current user
        keyboard_id: ID of the current keyboard
        parent: Optional parent widget
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        user_id: Optional[str] = None,
        keyboard_id: Optional[str] = None,
        parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.keyboard_id = keyboard_id
        
        self.setWindowTitle("SQL Query Tool")
        self.resize(900, 700)
        self.setup_ui()
        
    def setup_ui(self) -> None:
        """Set up the UI components and layout."""
        main_layout = QVBoxLayout()
        
        # User/Keyboard info section
        info_layout = QGridLayout()
        
        # User ID
        user_label = QLabel("User ID:")
        self.user_id_field = QLineEdit()
        self.user_id_field.setReadOnly(True)
        if self.user_id:
            self.user_id_field.setText(str(self.user_id))
        info_layout.addWidget(user_label, 0, 0)
        info_layout.addWidget(self.user_id_field, 0, 1)
        
        # Keyboard ID
        keyboard_label = QLabel("Keyboard ID:")
        self.keyboard_id_field = QLineEdit()
        self.keyboard_id_field.setReadOnly(True)
        if self.keyboard_id:
            self.keyboard_id_field.setText(str(self.keyboard_id))
        info_layout.addWidget(keyboard_label, 0, 2)
        info_layout.addWidget(self.keyboard_id_field, 0, 3)
        
        main_layout.addLayout(info_layout)
        
        # Query input section
        query_label = QLabel("SQL Query:")
        main_layout.addWidget(query_label)
        
        self.query_input = QPlainTextEdit()
        self.query_input.setMinimumHeight(150)
        self.query_input.setPlaceholderText("Enter your SQL query here...")
        main_layout.addWidget(self.query_input)
        
        # Submit button
        button_layout = QHBoxLayout()
        self.submit_btn = QPushButton("Execute Query")
        self.submit_btn.clicked.connect(self.execute_query)
        button_layout.addStretch()
        button_layout.addWidget(self.submit_btn)
        main_layout.addLayout(button_layout)
        
        # Results table
        results_label = QLabel("Query Results:")
        main_layout.addWidget(results_label)
        
        self.results_table = QTableWidget()
        self.results_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Read-only
        
        # Set horizontal header to stretch
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        
        main_layout.addWidget(self.results_table)
        
        # Status bar
        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)
        
        self.setLayout(main_layout)
    
    def execute_query(self) -> None:
        """Execute the SQL query and display results in the table."""
        query = self.query_input.toPlainText().strip()
        
        if not query:
            self.show_error("Please enter a SQL query.")
            return
            
        try:
            # Execute the query directly using DatabaseManager
            results = self._execute_raw_query(query)
            
            if not results:
                self.status_label.setText("Query executed successfully. No results returned.")
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)
                return
                
            # Process results
            self._populate_results_table(results)
            self.status_label.setText(f"Query executed successfully. {len(results)} rows returned.")
            
        except Exception as e:
            self.show_error(f"Error executing query: {str(e)}")
    
    def _execute_raw_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query using the DatabaseManager.
        
        Args:
            query: The SQL query to execute
            
        Returns:
            A list of dictionaries representing the query results
        """
        # Ensure we have a database connection
        if not self.db_manager:
            raise ValueError("No database connection available.")
            
        # Use the fetchall method to execute query and get results
        rows = self.db_manager.fetchall(query)
        
        # Convert sqlite3.Row objects to dictionaries
        results = []
        for row in rows:
            # sqlite3.Row objects can be accessed by index or by name
            result_dict = {key: row[key] for key in row.keys()}
            results.append(result_dict)
            
        return results
    
    def _populate_results_table(self, results: List[Dict[str, Any]]) -> None:
        """
        Populate the results table with query results.
        
        Args:
            results: List of dictionaries representing query results
        """
        if not results:
            return
            
        # Get column names from the first result
        columns = list(results[0].keys())
        
        # Set up the table
        self.results_table.setRowCount(len(results))
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        
        # Populate data
        for row_index, row_data in enumerate(results):
            for col_index, column_name in enumerate(columns):
                value = row_data.get(column_name, "")
                item = QTableWidgetItem(str(value))
                self.results_table.setItem(row_index, col_index, item)
                
        # Resize columns to content
        self.results_table.resizeColumnsToContents()
    
    def show_error(self, message: str) -> None:
        """Display error message and update status label."""
        QMessageBox.critical(self, "Error", message)
        self.status_label.setText(f"Error: {message}")
