"""
Database manager module that handles connection and core DB operations.
"""
import sqlite3
import os
from typing import Optional, Any, Dict, List, Tuple, Union


class DatabaseManager:
    """
    A class to manage database connections and provide utility methods for database operations.
    Acts as a singleton to prevent multiple instances from opening multiple connections.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = 'typing_data.db'
        return cls._instance
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return the results as a list of dictionaries."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the ID of the inserted row."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            row_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return row_id if row_id is not None else -1
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return -1
    
    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """Execute an UPDATE or DELETE query and return True if successful."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """Execute multiple queries as a transaction."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for query, params in queries:
                cursor.execute(query, params)
                
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Transaction error: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def init_db(self) -> bool:
        """Initialize the database with all required tables."""
        # The table creation queries from the original init_db function
        table_queries = [
            # Create practice_sessions table
            '''
            CREATE TABLE IF NOT EXISTS practice_sessions (
                session_id TEXT PRIMARY KEY,
                snippet_id INTEGER NOT NULL,
                snippet_index_start INTEGER NOT NULL,
                snippet_index_end INTEGER NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                total_time REAL,
                session_wpm REAL,
                session_cpm REAL,
                expected_chars INTEGER,
                actual_chars INTEGER,
                errors INTEGER,
                accuracy REAL,
                FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id)
            )
            ''',
            
            # Create practice_session_keystrokes table
            '''
            CREATE TABLE IF NOT EXISTS practice_session_keystrokes (
                session_id TEXT,
                keystroke_id INTEGER,
                keystroke_time DATETIME NOT NULL,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                time_since_previous INTEGER,
                PRIMARY KEY (session_id, keystroke_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
            )
            ''',
            
            # Create practice_session_errors table
            '''
            CREATE TABLE IF NOT EXISTS practice_session_errors (
                session_id TEXT,
                error_id INTEGER,
                keystroke_id INTEGER,
                keystroke_char TEXT NOT NULL,
                expected_char TEXT NOT NULL,
                PRIMARY KEY (session_id, error_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id),
                FOREIGN KEY (session_id, keystroke_id) REFERENCES practice_session_keystrokes(session_id, keystroke_id)
            )
            ''',
            
            # Create words table
            '''
            CREATE TABLE IF NOT EXISTS words (
                word_id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE NOT NULL
            )
            ''',
            
            # Create session_bigram_speed table
            '''
            CREATE TABLE IF NOT EXISTS session_bigram_speed (
                session_id TEXT,
                bigram_id INTEGER,
                bigram_time INTEGER NOT NULL,
                bigram_text TEXT NOT NULL,
                PRIMARY KEY (session_id, bigram_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
            )
            ''',
            
            # Create session_trigram_speed table
            '''
            CREATE TABLE IF NOT EXISTS session_trigram_speed (
                session_id TEXT,
                trigram_id INTEGER,
                trigram_time INTEGER NOT NULL,
                trigram_text TEXT NOT NULL,
                PRIMARY KEY (session_id, trigram_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
            )
            ''',
            
            # Create session_bigram_error table
            '''
            CREATE TABLE IF NOT EXISTS session_bigram_error (
                session_id TEXT,
                bigram_id INTEGER,
                bigram_time INTEGER NOT NULL,
                bigram_text TEXT NOT NULL,
                PRIMARY KEY (session_id, bigram_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
            )
            ''',
            
            # Create session_trigram_error table
            '''
            CREATE TABLE IF NOT EXISTS session_trigram_error (
                session_id TEXT,
                trigram_id INTEGER,
                trigram_time INTEGER NOT NULL,
                trigram_text TEXT NOT NULL,
                PRIMARY KEY (session_id, trigram_id),
                FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id)
            )
            ''',
            
            # Create text_category table
            '''
            CREATE TABLE IF NOT EXISTS text_category (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE
            )
            ''',
            
            # Create text_snippets table (metadata only)
            '''
            CREATE TABLE IF NOT EXISTS text_snippets (
                snippet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                snippet_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES text_category(category_id),
                UNIQUE(category_id, snippet_name)
            )
            ''',
            
            # Create snippet_parts table (actual content)
            '''
            CREATE TABLE IF NOT EXISTS snippet_parts (
                part_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snippet_id INTEGER NOT NULL,
                part_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (snippet_id) REFERENCES text_snippets(snippet_id),
                UNIQUE(snippet_id, part_number)
            )
            '''
        ]
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for query in table_queries:
                cursor.execute(query)
                
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
            return False
