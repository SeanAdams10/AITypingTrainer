"""
Database migration script to convert from separate n-gram tables to unified tables.
This script:
1. Creates new unified tables (session_ngram_speed and session_ngram_error)
2. Migrates data from existing n-gram tables (2-6) to the new tables
3. Drops the old tables when migration is complete
"""
import sqlite3
from database_manager import DatabaseManager


def migrate_ngram_tables():
    """Migrate data from separate n-gram tables to unified tables."""
    try:
        db = DatabaseManager()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Create unified tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_speed (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_ngram_error (
                id INTEGER PRIMARY KEY,
                session_id INTEGER NOT NULL,
                ngram_size INTEGER NOT NULL,
                ngram_id INTEGER NOT NULL,
                ngram_time INTEGER NOT NULL,
                ngram_text TEXT NOT NULL,
                UNIQUE(session_id, ngram_size, ngram_id)
            )
        """)

        # Get a list of all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row['name'] for row in cursor.fetchall()]
        print(f"All tables before migration: {all_tables}")

        # Migrate data from each existing n-gram table
        for n in range(2, 7):
            # Check if old tables exist
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='session_{n}gram_speed'")
            speed_table_exists = cursor.fetchone() is not None
            
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='session_{n}gram_error'")
            error_table_exists = cursor.fetchone() is not None
            
            # Migrate speed data if table exists
            if speed_table_exists:
                print(f"Migrating data from session_{n}gram_speed...")
                try:
                    cursor.execute(f"""
                        INSERT OR IGNORE INTO session_ngram_speed 
                        (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                        SELECT session_id, {n}, ngram_id, ngram_time, ngram_text 
                        FROM session_{n}gram_speed
                    """)
                    print(f"  Migrated {cursor.rowcount} records.")
                except sqlite3.Error as e:
                    print(f"  Error migrating speed data: {e}")
            
            # Migrate error data if table exists
            if error_table_exists:
                print(f"Migrating data from session_{n}gram_error...")
                try:
                    cursor.execute(f"""
                        INSERT OR IGNORE INTO session_ngram_error 
                        (session_id, ngram_size, ngram_id, ngram_time, ngram_text)
                        SELECT session_id, {n}, ngram_id, ngram_time, ngram_text 
                        FROM session_{n}gram_error
                    """)
                    print(f"  Migrated {cursor.rowcount} records.")
                except sqlite3.Error as e:
                    print(f"  Error migrating error data: {e}")
        
        # Commit the migration
        conn.commit()
        
        # Drop old tables
        old_tables_dropped = 0
        for n in range(2, 7):
            try:
                speed_table = f"session_{n}gram_speed"
                error_table = f"session_{n}gram_error"
                
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{speed_table}'")
                if cursor.fetchone():
                    cursor.execute(f"DROP TABLE {speed_table}")
                    print(f"Dropped {speed_table}")
                    old_tables_dropped += 1
                
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{error_table}'")
                if cursor.fetchone():
                    cursor.execute(f"DROP TABLE {error_table}")
                    print(f"Dropped {error_table}")
                    old_tables_dropped += 1
                
            except sqlite3.Error as e:
                print(f"Error dropping old tables: {e}")
        
        conn.commit()
        
        # Verify tables were dropped
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        remaining_tables = [row['name'] for row in cursor.fetchall()]
        print(f"All tables after migration: {remaining_tables}")
        
        # Check for any remaining n-gram tables
        remaining_ngram_tables = [t for t in remaining_tables if ('bigram' in t.lower() or 'trigram' in t.lower() or '_2gram' in t.lower() or '_3gram' in t.lower())]
        if remaining_ngram_tables:
            print(f"WARNING: The following old n-gram tables still exist: {remaining_ngram_tables}")
            print("Attempting to drop these tables...")
            
            for table in remaining_ngram_tables:
                try:
                    cursor.execute(f"DROP TABLE {table}")
                    print(f"Dropped {table}")
                    old_tables_dropped += 1
                except sqlite3.Error as e:
                    print(f"Error dropping table {table}: {e}")
            
            conn.commit()
        
        conn.close()
        
        print(f"Migration completed successfully! Dropped {old_tables_dropped} old tables.")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


if __name__ == "__main__":
    migrate_ngram_tables()
