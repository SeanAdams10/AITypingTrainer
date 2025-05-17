"""
Migration to remove the 'count' and 'occurrence' fields from n-gram tables.

This migration:
1. Creates new tables without the 'count' and 'occurrence' fields
2. Copies data from old tables to new tables
3. Drops the old tables
4. Renames the new tables to the original names
5. Recreates indexes
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Create and return a database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def migrate_database(db_path: Optional[str] = None) -> None:
    """
    Migrate the database to remove 'count' and 'occurrence' fields from n-gram tables.
    
    Args:
        db_path: Path to the SQLite database file. If None, uses the default path.
    """
    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "typing_data.db")
    
    logger.info("Starting database migration: Remove count/occurrence from n-gram tables")
    
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION;")
            
            try:
                # Create new tables without the count/occurrence fields
                logger.info("Creating new n-gram tables...")
                
                # New session_ngram_speed table without 'count' field
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS new_session_ngram_speed (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        ngram_size INTEGER NOT NULL,
                        ngram TEXT NOT NULL,
                        ngram_time_ms REAL NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                        UNIQUE(session_id, ngram)
                    );
                """)
                
                # New session_ngram_errors table without 'occurrences' field
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS new_session_ngram_errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        ngram_size INTEGER NOT NULL,
                        ngram TEXT NOT NULL,
                        error_count INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (session_id) REFERENCES practice_sessions(session_id) ON DELETE CASCADE,
                        UNIQUE(session_id, ngram)
                    );
                """)
                
                # Copy data from old tables to new tables
                logger.info("Migrating data to new tables...")
                
                # Copy data to new_session_ngram_speed (excluding 'count' field)
                cursor.execute("""
                    INSERT INTO new_session_ngram_speed 
                    (id, session_id, ngram_size, ngram, ngram_time_ms)
                    SELECT id, session_id, ngram_size, ngram, ngram_time_ms
                    FROM session_ngram_speed;
                """)
                
                # Copy data to new_session_ngram_errors (excluding 'occurrences' field)
                cursor.execute("""
                    INSERT INTO new_session_ngram_errors 
                    (id, session_id, ngram_size, ngram, error_count)
                    SELECT id, session_id, ngram_size, ngram, error_count
                    FROM session_ngram_errors;
                """)
                
                # Drop old tables
                logger.info("Dropping old tables...")
                cursor.execute("DROP TABLE IF EXISTS session_ngram_speed;")
                cursor.execute("DROP TABLE IF EXISTS session_ngram_errors;")
                
                # Rename new tables to original names
                logger.info("Renaming new tables...")
                cursor.execute("ALTER TABLE new_session_ngram_speed RENAME TO session_ngram_speed;")
                cursor.execute("ALTER TABLE new_session_ngram_errors RENAME TO session_ngram_errors;")
                
                # Recreate indexes
                logger.info("Recreating indexes...")
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ngram_speed_session 
                    ON session_ngram_speed(session_id);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ngram_errors_session 
                    ON session_ngram_errors(session_id);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ngram_speed_ngram 
                    ON session_ngram_speed(ngram);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ngram_errors_ngram 
                    ON session_ngram_errors(ngram);
                """)
                
                # Commit the transaction
                conn.commit()
                logger.info("Database migration completed successfully.")
                
            except Exception as e:
                conn.rollback()
                logger.error("Error during migration: %s", str(e), exc_info=True)
                raise
                
    except sqlite3.Error as e:
        logger.error("Database error during migration: %s", str(e), exc_info=True)
        raise

def rollback_migration(db_path: Optional[str] = None) -> None:
    """
    Rollback the migration by dropping the new tables if they exist.
    
    Args:
        db_path: Path to the SQLite database file. If None, uses the default path.
    """
    if db_path is None:
        db_path = str(Path(__file__).parent.parent / "typing_data.db")
    
    logger.warning("Rolling back database migration...")
    
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Drop new tables if they exist
            cursor.execute("DROP TABLE IF EXISTS new_session_ngram_speed;")
            cursor.execute("DROP TABLE IF EXISTS new_session_ngram_errors;")
            
            # Check if old tables still exist, if not, try to recreate them from backup
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_ngram_speed';")
            if not cursor.fetchone():
                logger.warning("Original session_ngram_speed table not found. Cannot roll back.")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_ngram_errors';")
            if not cursor.fetchone():
                logger.warning("Original session_ngram_errors table not found. Cannot roll back.")
            
            conn.commit()
            logger.warning("Rollback completed. Note: You may need to restore from backup.")
            
    except sqlite3.Error as e:
        logger.error("Error during rollback: %s", str(e), exc_info=True)
        raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate database to remove count/occurrence from n-gram tables.")
    parser.add_argument("--db-path", help="Path to the SQLite database file")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration(args.db_path)
    else:
        migrate_database(args.db_path)
