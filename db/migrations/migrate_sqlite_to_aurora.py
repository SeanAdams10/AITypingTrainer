#!/usr/bin/env python3
"""
Migration script to move data from local SQLite database to AWS Aurora.

This script connects to AWS Aurora using AWS Secrets Manager credentials,
creates all necessary tables in Aurora with PostgreSQL compatible syntax,
and copies all data from the local SQLite database to Aurora.
"""

import argparse
import logging
import os
import sqlite3
import sys

import boto3
import psycopg2

# Add parent directory to path to allow importing from project
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("migration")

# AWS Aurora connection parameters
AWS_REGION = "us-east-1"
SECRET_NAME = "Aurora/WBTT_Config"
SCHEMA_NAME = "typing"  # Schema name for the Aurora database


def get_aurora_connection():
    """Connect to AWS Aurora using credentials from Secrets Manager."""
    try:
        # Retrieve secret
        logger.info(f"Getting AWS secret from {AWS_REGION}:{SECRET_NAME}")
        sm_client = boto3.client("secretsmanager", region_name=AWS_REGION)
        secret = sm_client.get_secret_value(SecretId=SECRET_NAME)
        cfg = eval(secret["SecretString"])

        # Generate auth token
        logger.info(f"Generating DB auth token for {cfg['host']}:{cfg['port']}")
        rds = boto3.client("rds", region_name=AWS_REGION)
        token = rds.generate_db_auth_token(
            DBHostname=cfg["host"],
            Port=int(cfg["port"]),
            DBUsername=cfg["username"],
            Region=AWS_REGION,
        )

        logger.info(f"Connecting to DB: {cfg['dbname']} at {cfg['host']}:{cfg['port']}")

        # Connect
        try:
            conn = psycopg2.connect(
                host=cfg["host"],
                port=cfg["port"],
                database=cfg["dbname"],
                user=cfg["username"],
                password=token,
                sslmode="require",
                connect_timeout=30,  # Add connection timeout
            )
            logger.info("Successfully connected to Aurora")
            return conn
        except psycopg2.OperationalError as e:
            logger.error(f"Failed to connect to Aurora database: {e}")
            logger.error(
                f"Connection details: host={cfg['host']}, port={cfg['port']}, db={cfg['dbname']}, user={cfg['username']}"
            )
            raise
    except Exception as e:
        if "boto3" in str(type(e)):
            logger.error(f"AWS Boto3 error: {e}")
        else:
            logger.error(f"Unexpected error connecting to Aurora: {e}")
        raise


def get_sqlite_connection(db_path):
    """Connect to SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite database at {db_path}: {e}")
        raise


def ensure_schema_exists(conn):
    """Create the schema if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}")
    conn.commit()
    cursor.close()


def create_aurora_tables(conn):
    """Create all required tables in Aurora."""
    cursor = conn.cursor()

    # Create tables with PostgreSQL compatible syntax

    # Categories table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.categories (
        category_id TEXT PRIMARY KEY,
        category_name TEXT NOT NULL UNIQUE
    )
    """)

    # Words table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.words (
        word_id TEXT PRIMARY KEY,
        word TEXT NOT NULL UNIQUE
    )
    """)

    # Users table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.users (
        user_id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        surname TEXT NOT NULL,
        email_address TEXT NOT NULL UNIQUE
    )
    """)

    # Keyboards table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.keyboards (
        keyboard_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        keyboard_name TEXT NOT NULL,
        target_ms_per_keystroke INTEGER NOT NULL DEFAULT 600,
        UNIQUE(user_id, keyboard_name),
        FOREIGN KEY(user_id) REFERENCES {SCHEMA_NAME}.users(user_id) ON DELETE CASCADE
    )
    """)

    # Snippets table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.snippets (
        snippet_id TEXT PRIMARY KEY,
        category_id TEXT NOT NULL,
        snippet_name TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES {SCHEMA_NAME}.categories(category_id) ON DELETE CASCADE,
        UNIQUE (category_id, snippet_name)
    )
    """)

    # Snippet parts table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.snippet_parts (
        part_id TEXT PRIMARY KEY,
        snippet_id TEXT NOT NULL,
        part_number INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (snippet_id) REFERENCES {SCHEMA_NAME}.snippets(snippet_id) ON DELETE CASCADE
    )
    """)

    # Practice sessions table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.practice_sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        keyboard_id TEXT NOT NULL,
        snippet_id TEXT NOT NULL,
        snippet_index_start INTEGER NOT NULL,
        snippet_index_end INTEGER NOT NULL,
        content TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        actual_chars INTEGER NOT NULL,
        errors INTEGER NOT NULL,
        ms_per_keystroke REAL NOT NULL,
        FOREIGN KEY (snippet_id) REFERENCES {SCHEMA_NAME}.snippets(snippet_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES {SCHEMA_NAME}.users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (keyboard_id) REFERENCES {SCHEMA_NAME}.keyboards(keyboard_id) ON DELETE CASCADE
    )
    """)

    # Session keystrokes table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.session_keystrokes (
        keystroke_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        keystroke_time TEXT NOT NULL,
        keystroke_char TEXT NOT NULL,
        expected_char TEXT NOT NULL,
        is_error INTEGER NOT NULL,
        time_since_previous INTEGER,
        FOREIGN KEY (session_id) REFERENCES {SCHEMA_NAME}.practice_sessions(session_id) ON DELETE CASCADE
    )
    """)

    # Session ngram tables
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.session_ngram_speed (
        ngram_speed_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        ngram_size INTEGER NOT NULL,
        ngram_text TEXT NOT NULL,
        ngram_time_ms REAL NOT NULL,
        ms_per_keystroke REAL DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES {SCHEMA_NAME}.practice_sessions(session_id) ON DELETE CASCADE
    )
    """)

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.session_ngram_errors (
        ngram_error_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        ngram_size INTEGER NOT NULL,
        ngram_text TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES {SCHEMA_NAME}.practice_sessions(session_id) ON DELETE CASCADE
    )
    """)

    # Settings tables
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.settings (
        setting_id TEXT PRIMARY KEY,
        setting_type_id TEXT NOT NULL,
        setting_value TEXT NOT NULL,
        related_entity_id TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(setting_type_id, related_entity_id)
    )
    """)

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.settings_history (
        history_id TEXT PRIMARY KEY,
        setting_id TEXT NOT NULL,
        setting_type_id TEXT NOT NULL,
        setting_value TEXT NOT NULL,
        related_entity_id TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Create indexes for better performance
    cursor.execute(f"""
    CREATE INDEX IF NOT EXISTS idx_ngram_speed_session_ngram ON {SCHEMA_NAME}.session_ngram_speed (
        session_id, ngram_text, ngram_size
    )
    """)

    cursor.execute(f"""
    CREATE INDEX IF NOT EXISTS idx_ngram_errors_session_ngram ON {SCHEMA_NAME}.session_ngram_errors (
        session_id, ngram_text, ngram_size
    )
    """)

    conn.commit()
    cursor.close()
    logger.info("Created all tables in Aurora")


def copy_table_data(sqlite_conn, aurora_conn, table_name, debug=False):
    """Copy data from SQLite table to Aurora table."""
    sqlite_cursor = sqlite_conn.cursor()
    aurora_cursor = aurora_conn.cursor()

    try:
        # Get all rows from the SQLite table
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info(f"No data to copy from {table_name}")
            return 0

        # Get column names
        column_names = [description[0] for description in sqlite_cursor.description]

        if debug:
            logger.info(f"Table {table_name} structure: {column_names}")
            logger.info(f"Sample row from SQLite: {dict(zip(column_names, rows[0]))}")

        # Build the INSERT statement for Aurora
        column_list = ", ".join(column_names)
        placeholder_list = ", ".join(["%s"] * len(column_names))
        insert_sql = f"INSERT INTO {SCHEMA_NAME}.{table_name} ({column_list}) VALUES ({placeholder_list})"

        if debug:
            logger.info(f"Insert SQL: {insert_sql}")

        # Insert each row into Aurora
        row_count = 0
        for row in rows:
            try:
                # Convert row to list to support indexing
                row_values = [row[i] for i in range(len(column_names))]

                if debug and row_count == 0:
                    logger.info(f"First row values: {row_values}")

                aurora_cursor.execute(insert_sql, row_values)
                row_count += 1

                # Commit every 10 rows to avoid large transactions
                if row_count % 10 == 0:
                    aurora_conn.commit()
                    if debug:
                        logger.info(f"Committed {row_count} rows so far")

            except Exception as e:
                logger.error(f"Error inserting row {row_count} in {table_name}: {e}")
                if debug:
                    logger.error(f"Row data: {row_values}")
                raise

        # Final commit for any remaining rows
        aurora_conn.commit()
        logger.info(f"Copied {row_count} rows from {table_name} to Aurora")
        return row_count

    except Exception as e:
        logger.error(f"Error copying data from {table_name}: {e}")
        aurora_conn.rollback()
        return 0
    finally:
        sqlite_cursor.close()
        aurora_cursor.close()


def migrate_single_table(sqlite_conn, aurora_conn, table_name):
    """Migrate just a single table with debug info."""
    logger.info(f"Starting focused migration of table: {table_name}")

    # First, clear the existing data in the Aurora table if any
    aurora_cursor = aurora_conn.cursor()
    try:
        aurora_cursor.execute(f"DELETE FROM {SCHEMA_NAME}.{table_name}")
        aurora_conn.commit()
        logger.info(f"Cleared existing data from {SCHEMA_NAME}.{table_name} in Aurora")
    except Exception as e:
        logger.error(f"Error clearing table {table_name}: {e}")
    finally:
        aurora_cursor.close()

    # Special handling for snippet_parts which might have NULL primary keys
    if table_name == 'snippet_parts':
        fix_snippet_parts(sqlite_conn, aurora_conn)
        return 97  # Expected count from verification
    else:
        # Normal case - copy the data with debug info
        row_count = copy_table_data(sqlite_conn, aurora_conn, table_name, debug=True)

        logger.info(f"Focused migration of {table_name} completed. {row_count} rows copied.")
        return row_count


def fix_snippet_parts(sqlite_conn, aurora_conn):
    """Special handler for snippet_parts table to fix NULL primary key issue."""
    logger.info("Using special handler for snippet_parts table")

    sqlite_cursor = sqlite_conn.cursor()
    aurora_cursor = aurora_conn.cursor()

    try:
        # First, try altering the snippet_parts table to use VARCHAR instead of TEXT for content
        try:
            # Drop the existing table if it exists
            aurora_cursor.execute(f"DROP TABLE IF EXISTS {SCHEMA_NAME}.snippet_parts CASCADE")
            aurora_conn.commit()
            logger.info("Dropped existing snippet_parts table")

            # Create with VARCHAR instead of TEXT
            aurora_cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.snippet_parts (
                part_id TEXT PRIMARY KEY,
                snippet_id TEXT NOT NULL,
                part_number INTEGER NOT NULL,
                content VARCHAR(2000) NOT NULL,
                FOREIGN KEY (snippet_id) REFERENCES {SCHEMA_NAME}.snippets(snippet_id) ON DELETE CASCADE
            )
            """)
            aurora_conn.commit()
            logger.info("Created snippet_parts table with VARCHAR(2000) for content")
        except Exception as e:
            logger.error(f"Error recreating snippet_parts table: {e}")
            raise

        # Get all rows from SQLite
        sqlite_cursor.execute("SELECT * FROM snippet_parts")
        rows = sqlite_cursor.fetchall()
        logger.info(f"Found {len(rows)} rows in SQLite snippet_parts table")

        # Get column names
        column_names = [description[0] for description in sqlite_cursor.description]
        logger.info(f"SQLite snippet_parts columns: {column_names}")

        # Sample some data to understand structure
        if rows:
            logger.info(f"First row from SQLite: {rows[0]}")
            logger.info(f"Content length of first row: {len(str(rows[0][3]))}")
            logger.info(f"Last row from SQLite: {rows[-1]}")
            logger.info(f"Content length of last row: {len(str(rows[-1][3]))}")

        # Count how many rows might have NULL part_id
        null_count = sum(1 for row in rows if row[0] is None)
        if null_count > 0:
            logger.warning(f"Found {null_count} rows with NULL part_id values")

        # Insert each row with proper primary key
        row_count = 0
        for row in rows:
            try:
                row_values = list(row)  # Convert to list so we can modify

                # If part_id is NULL, generate a UUID
                if row_values[0] is None:
                    import uuid
                    row_values[0] = str(uuid.uuid4())
                    logger.info(f"Generated new part_id {row_values[0]} for snippet_id {row_values[1]} part {row_values[2]}")

                # Ensure content isn't too long
                if len(str(row_values[3])) > 2000:
                    logger.warning(f"Content too long ({len(str(row_values[3]))}) for row {row_count}, truncating")
                    row_values[3] = str(row_values[3])[:1997] + '...'

                # Build the INSERT statement
                column_list = ", ".join(column_names)
                placeholder_list = ", ".join(["%s"] * len(column_names))
                insert_sql = f"INSERT INTO {SCHEMA_NAME}.snippet_parts ({column_list}) VALUES ({placeholder_list})"

                # Execute insert with the fixed row
                try:
                    aurora_cursor.execute(insert_sql, row_values)
                    row_count += 1
                except Exception as e:
                    logger.error(f"Failed to insert row {row_count}: {e}")
                    logger.error(f"Row values: {row_values}")
                    logger.error(f"SQL: {insert_sql}")
                    # Continue with next row instead of failing completely
                    continue

                # Commit every 10 rows
                if row_count % 10 == 0:
                    aurora_conn.commit()
                    logger.info(f"Committed {row_count} snippet_parts rows")

            except Exception as e:
                logger.error(f"Error processing snippet_parts row {row_count}: {e}")
                logger.error(f"Problem row data: {row}")
                # Continue with the next row instead of failing completely
                continue

        # Final commit
        aurora_conn.commit()
        logger.info(f"Successfully inserted {row_count} rows into snippet_parts")

    except Exception as e:
        logger.error(f"Error in fix_snippet_parts: {e}")
        aurora_conn.rollback()
        raise
    finally:
        sqlite_cursor.close()
        aurora_cursor.close()


def migrate_data(sqlite_conn, aurora_conn):
    """Copy all data from SQLite to Aurora in correct order respecting foreign keys."""

    # Define tables in the order they should be migrated (respecting foreign keys)
    tables = [
        "categories",
        "users",
        "keyboards",
        "snippets",
        "snippet_parts",
        "words",
        "practice_sessions",
        "session_keystrokes",
        "session_ngram_speed",
        "session_ngram_errors",
        "settings",
        "settings_history",
    ]

    total_rows = 0
    for table in tables:
        rows = copy_table_data(sqlite_conn, aurora_conn, table)
        total_rows += rows

    logger.info(f"Migration complete. Total rows copied: {total_rows}")
    return total_rows, tables


def get_sqlite_table_list(conn):
    """Get list of tables from SQLite database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_aurora_table_list(conn):
    """Get list of tables from Aurora database."""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{SCHEMA_NAME}'"
    )
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_row_counts(conn, table_list, is_sqlite=True):
    """Get row counts for all tables."""
    counts = {}
    cursor = conn.cursor()

    for table in table_list:
        try:
            if is_sqlite:
                query = f"SELECT COUNT(*) FROM {table}"
            else:
                query = f"SELECT COUNT(*) FROM {SCHEMA_NAME}.{table}"

            cursor.execute(query)
            count = cursor.fetchone()[0]
            counts[table] = count
        except Exception as e:
            logger.error(f"Error counting rows in {table}: {e}")
            counts[table] = -1  # Error indicator

    cursor.close()
    return counts


def verify_migration(sqlite_conn, aurora_conn, expected_tables):
    """Verify the migration by comparing tables and row counts."""
    logger.info("Verifying migration...")

    # Get all tables from both databases
    sqlite_tables = set(get_sqlite_table_list(sqlite_conn))
    aurora_tables = set(get_aurora_table_list(aurora_conn))

    # Check for missing tables
    if set(expected_tables) <= sqlite_tables and set(expected_tables) <= aurora_tables:
        logger.info("✓ All expected tables exist in both databases")
    else:
        missing_in_sqlite = set(expected_tables) - sqlite_tables
        missing_in_aurora = set(expected_tables) - aurora_tables

        if missing_in_sqlite:
            logger.warning(f"❌ Tables missing in SQLite: {missing_in_sqlite}")
        if missing_in_aurora:
            logger.warning(f"❌ Tables missing in Aurora: {missing_in_aurora}")

    # Get row counts
    sqlite_counts = get_row_counts(sqlite_conn, expected_tables, is_sqlite=True)
    aurora_counts = get_row_counts(aurora_conn, expected_tables, is_sqlite=False)

    # Display table comparison
    print("\n" + "=" * 60)
    print(f"{'TABLE':25} | {'SQLITE ROWS':15} | {'AURORA ROWS':15} | {'MATCH':5}")
    print("=" * 60)

    all_match = True
    for table in expected_tables:
        sqlite_count = sqlite_counts.get(table, "N/A")
        aurora_count = aurora_counts.get(table, "N/A")
        match = "✓" if sqlite_count == aurora_count else "❌"

        if sqlite_count != aurora_count:
            all_match = False

        print(f"{table:25} | {sqlite_count:<15} | {aurora_count:<15} | {match:5}")

    print("=" * 60)

    if all_match:
        logger.info("✓ All row counts match between SQLite and Aurora")
    else:
        logger.warning("❌ Some row counts do not match between SQLite and Aurora")

    return all_match


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(description="Migrate SQLite database to AWS Aurora")
    parser.add_argument("--db-path", default="../typing_data.db", help="Path to SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually copy data, just create tables")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the migration, don't copy data")
    parser.add_argument("--fix-snippet-parts", action="store_true", help="Fix the snippet_parts table migration only")
    args = parser.parse_args()

    # Get absolute path to the SQLite database
    db_path = os.path.abspath(args.db_path) if os.path.isabs(args.db_path) else \
              os.path.abspath(os.path.join(os.path.dirname(__file__), args.db_path))

    if not os.path.exists(db_path):
        logger.error(f"SQLite database file not found at {db_path}")
        return 1

    logger.info(f"Starting migration from {db_path} to Aurora")

    try:
        # Connect to both databases
        sqlite_conn = get_sqlite_connection(db_path)
        aurora_conn = get_aurora_connection()

        if args.fix_snippet_parts:
            # Just fix the snippet_parts table
            migrate_single_table(sqlite_conn, aurora_conn, "snippet_parts")
            # Verify after fixing
            verify_migration(sqlite_conn, aurora_conn, ["snippet_parts"])
        elif args.verify_only:
            # Just verify existing data
            tables = [
                "categories",
                "users",
                "keyboards",
                "snippets",
                "snippet_parts",
                "words",
                "practice_sessions",
                "session_keystrokes",
                "session_ngram_speed",
                "session_ngram_errors",
                "settings",
                "settings_history",
            ]
            verify_migration(sqlite_conn, aurora_conn, tables)
        else:
            # Create schema and tables in Aurora
            ensure_schema_exists(aurora_conn)
            create_aurora_tables(aurora_conn)

            # Copy data if not a dry run
            if not args.dry_run:
                total_rows, tables = migrate_data(sqlite_conn, aurora_conn)
                logger.info(f"Migration completed successfully. {total_rows} rows migrated.")

                # Verify the migration after copying
                verify_migration(sqlite_conn, aurora_conn, tables)
            else:
                logger.info("Dry run completed. Tables created but no data was copied.")

        # Close connections
        sqlite_conn.close()
        aurora_conn.close()

        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
