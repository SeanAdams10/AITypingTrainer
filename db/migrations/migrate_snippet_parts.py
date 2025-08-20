#!/usr/bin/env python3
"""
Migration script specifically focused on migrating the snippet_parts table
from SQLite to AWS Aurora PostgreSQL.

This script:
1. Extracts the snippet_parts schema from SQLite
2. Drops and recreates the table in Aurora with identical schema
3. Migrates rows one by one
4. Verifies each row after insertion
5. Alerts on any failures
"""

import argparse
import logging
import os
import sqlite3
import sys
import traceback
import uuid

import boto3
import psycopg2

# Configure logging with both console and file output
log_file = 'snippet_parts_migration.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode='w')
    ]
)

logger = logging.getLogger('snippet_parts_migration')
logger.info(f"Log file will be saved to: {os.path.abspath(log_file)}")


# AWS Aurora connection parameters
AWS_REGION = "us-east-1"
SECRET_NAME = "Aurora/WBTT_Config"
SCHEMA_NAME = "typing"

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
                connect_timeout=30,
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
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database file not found at {db_path}")

    conn = sqlite3.connect(db_path)
    return conn


def get_sqlite_schema(conn):
    """Get the snippet_parts table schema from SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='snippet_parts'")
    schema_sql = cursor.fetchone()
    cursor.close()

    if not schema_sql:
        raise Exception("Could not find snippet_parts table in SQLite database")

    return schema_sql[0]


def recreate_aurora_snippet_parts_table(conn):
    """Drop and recreate the snippet_parts table in Aurora with PostgreSQL-compatible syntax."""
    cursor = conn.cursor()

    try:
        # Drop existing table if it exists
        cursor.execute(f"DROP TABLE IF EXISTS {SCHEMA_NAME}.snippet_parts CASCADE")
        conn.commit()
        logger.info("Dropped existing snippet_parts table in Aurora")

        # Create table with the same schema as SQLite but PostgreSQL compatible
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_NAME}.snippet_parts (
            part_id TEXT PRIMARY KEY,
            snippet_id TEXT NOT NULL,
            part_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (snippet_id) REFERENCES {SCHEMA_NAME}.snippets(snippet_id) ON DELETE CASCADE
        )
        """)
        conn.commit()
        logger.info("Created snippet_parts table in Aurora")
    except Exception as e:
        logger.error(f"Error recreating snippet_parts table: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def row_to_dict(cursor, row):
    """Convert a row tuple to a dictionary with column names as keys."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_all_snippet_parts_rows(conn):
    """Get all rows from the snippet_parts table in SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snippet_parts")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    # Convert to list of dictionaries for easier handling
    rows_as_dicts = []
    for row in rows:
        row_dict = {}
        for i, col in enumerate(columns):
            row_dict[col] = row[i]
        rows_as_dicts.append(row_dict)

    cursor.close()

    return rows_as_dicts, columns


def migrate_and_verify_rows(sqlite_conn, aurora_conn):
    """Migrate rows from SQLite to Aurora one by one, verifying each after insertion."""
    rows, columns = get_all_snippet_parts_rows(sqlite_conn)

    if not rows:
        logger.warning("No rows found in SQLite snippet_parts table")
        return 0, 0, []

    logger.info(f"Found {len(rows)} rows in SQLite snippet_parts table")
    logger.info(f"Columns: {columns}")

    success_count = 0
    failed_count = 0
    failed_rows = []

    # SQLite cursor for row verification
    sqlite_cursor = sqlite_conn.cursor()

    for i, row in enumerate(rows):
        try:
            # If part_id is None, generate a UUID
            if row['part_id'] is None:
                row['part_id'] = str(uuid.uuid4())
                logger.info(f"Generated UUID for missing part_id: {row['part_id']}")

            # Insert into Aurora
            aurora_cursor = aurora_conn.cursor()

            # Build the INSERT statement
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))

            # Values in column order
            values = [row[col] for col in columns]

            try:
                # Insert row
                aurora_cursor.execute(
                    f"INSERT INTO {SCHEMA_NAME}.snippet_parts ({columns_str}) VALUES ({placeholders})",
                    values
                )
                aurora_conn.commit()

                # Verify the inserted row
                aurora_cursor.execute(
                    f"SELECT * FROM {SCHEMA_NAME}.snippet_parts WHERE part_id = %s",
                    (row['part_id'],)
                )
                inserted_row = aurora_cursor.fetchone()

                if not inserted_row:
                    logger.error(f"Row {i+1}/{len(rows)} with part_id {row['part_id']} not found after insert")
                    failed_count += 1
                    failed_rows.append(row)
                    continue

                # Convert inserted row to dictionary
                inserted_row_dict = {}
                for idx, col in enumerate(aurora_cursor.description):
                    inserted_row_dict[col[0]] = inserted_row[idx]

                # Check if rows match
                match = True
                for col in columns:
                    sqlite_val = row[col]
                    aurora_val = inserted_row_dict[col]

                    if sqlite_val != aurora_val:
                        logger.error(f"Row {i+1}/{len(rows)} mismatch in column {col}: SQLite={sqlite_val}, Aurora={aurora_val}")
                        match = False

                if match:
                    success_count += 1
                    if i % 10 == 0 or i == len(rows) - 1:
                        logger.info(f"Successfully migrated and verified row {i+1}/{len(rows)}")
                else:
                    failed_count += 1
                    failed_rows.append(row)

            except Exception as e:
                logger.error(f"Error inserting row {i+1}/{len(rows)}: {e}")
                logger.error(f"Row values: {row}")
                aurora_conn.rollback()
                failed_count += 1
                failed_rows.append(row)

            finally:
                aurora_cursor.close()

        except Exception as e:
            logger.error(f"Error processing row {i+1}/{len(rows)}: {e}")
            failed_count += 1
            failed_rows.append(row)

    sqlite_cursor.close()

    return success_count, failed_count, failed_rows


def verify_only(sqlite_conn, aurora_conn):
    """Check and compare row counts between SQLite and Aurora without migration."""
    # SQLite count
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT COUNT(*) FROM snippet_parts")
    sqlite_count = sqlite_cursor.fetchone()[0]
    logger.info(f"SQLite snippet_parts count: {sqlite_count}")

    # Aurora count
    aurora_cursor = aurora_conn.cursor()
    aurora_cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.snippet_parts")
    aurora_count = aurora_cursor.fetchone()[0]
    logger.info(f"Aurora snippet_parts count: {aurora_count}")

    # Compare counts
    if sqlite_count == aurora_count:
        logger.info(f"VERIFICATION SUCCESS: Row counts match! ({sqlite_count} rows in both databases)")
    else:
        logger.error(f"VERIFICATION FAILED: Row counts don't match! SQLite: {sqlite_count}, Aurora: {aurora_count}")

    sqlite_cursor.close()
    aurora_cursor.close()

    return sqlite_count == aurora_count


def main():
    """Main entry point for the snippet_parts migration script."""
    parser = argparse.ArgumentParser(description="Migrate snippet_parts table from SQLite to AWS Aurora")
    parser.add_argument("--db-path", required=True, help="Path to SQLite database")
    parser.add_argument("--verify-only", action="store_true", help="Only verify row counts without performing migration")
    args = parser.parse_args()

    # Ensure db_path is absolute
    db_path = os.path.abspath(args.db_path)

    if not os.path.exists(db_path):
        logger.error(f"SQLite database file not found at {db_path}")
        return 1

    try:
        # Connect to both databases
        sqlite_conn = get_sqlite_connection(db_path)
        aurora_conn = get_aurora_connection()

        if args.verify_only:
            # Only verify row counts
            logger.info(f"Running verification only between {db_path} and Aurora")
            success = verify_only(sqlite_conn, aurora_conn)

            # Close connections
            sqlite_conn.close()
            aurora_conn.close()

            return 0 if success else 1
        else:
            # Full migration
            logger.info(f"Starting snippet_parts migration from {db_path} to Aurora")

            # Get SQLite schema for snippet_parts
            sqlite_schema = get_sqlite_schema(sqlite_conn)
            logger.info(f"SQLite snippet_parts schema: {sqlite_schema}")

            # Recreate table in Aurora
            recreate_aurora_snippet_parts_table(aurora_conn)

            # Migrate and verify rows
            success_count, failed_count, failed_rows = migrate_and_verify_rows(sqlite_conn, aurora_conn)

            # Print summary
            logger.info("=" * 60)
            logger.info("MIGRATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total rows processed: {success_count + failed_count}")
            logger.info(f"Successfully migrated rows: {success_count}")
            logger.info(f"Failed rows: {failed_count}")

            if failed_count > 0:
                logger.error("=" * 60)
                logger.error("FAILED ROWS")
                logger.error("=" * 60)
                for i, row in enumerate(failed_rows):
                    logger.error(f"Failed row {i+1}: {row}")

            # Close connections
            sqlite_conn.close()
            aurora_conn.close()

            if failed_count > 0:
                logger.error("Migration completed with errors. See above for details.")
                return 1
            else:
                logger.info("Migration completed successfully.")
                return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
