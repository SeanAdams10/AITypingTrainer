#!/usr/bin/env python

import logging
import os
import sqlite3
import sys

import boto3
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('snippet_parts_check')

# AWS Aurora connection parameters
AWS_REGION = "us-east-1"
SECRETS_ID = "Aurora/WBTT_Config"
SCHEMA_NAME = "typing"

def get_aurora_connection():
    """Get a connection to AWS Aurora PostgreSQL."""
    try:
        # Get secrets from AWS Secrets Manager
        sm_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        secret = sm_client.get_secret_value(SecretId=SECRETS_ID)
        config = eval(secret['SecretString'])

        logger.info(f"Connecting to DB: {config['dbname']} at {config['host']}:{config['port']}")

        # Generate auth token for Aurora serverless
        rds = boto3.client('rds', region_name=AWS_REGION)
        token = rds.generate_db_auth_token(
            DBHostname=config['host'],
            Port=int(config['port']),
            DBUsername=config['username'],
            Region=AWS_REGION
        )

        # Connect to Aurora
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['dbname'],
            user=config['username'],
            password=token,
            sslmode='require'
        )

        # Set search_path to schema
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO {SCHEMA_NAME}")
        conn.commit()
        cursor.close()

        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Aurora: {e}")
        raise

def get_sqlite_connection(db_path):
    """Get a connection to SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQLite: {e}")
        raise

def main():
    """Main entry point for checking snippet_parts row counts."""
    if len(sys.argv) != 2:
        logger.error("Usage: python check_snippet_parts_count.py <path-to-sqlite-db>")
        return 1

    db_path = os.path.abspath(sys.argv[1])

    if not os.path.exists(db_path):
        logger.error(f"SQLite database file not found at {db_path}")
        return 1

    try:
        # Connect to both databases
        sqlite_conn = get_sqlite_connection(db_path)
        aurora_conn = get_aurora_connection()

        # SQLite count
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT COUNT(*) FROM snippet_parts")
        sqlite_count = sqlite_cursor.fetchone()[0]

        # Aurora count
        aurora_cursor = aurora_conn.cursor()
        aurora_cursor.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.snippet_parts")
        aurora_count = aurora_cursor.fetchone()[0]

        logger.info("=" * 60)
        logger.info("SNIPPET_PARTS ROW COUNT COMPARISON")
        logger.info("=" * 60)
        logger.info(f"SQLite row count: {sqlite_count}")
        logger.info(f"Aurora row count: {aurora_count}")
        logger.info(f"Counts match: {sqlite_count == aurora_count}")

        # Close connections
        sqlite_cursor.close()
        aurora_cursor.close()
        sqlite_conn.close()
        aurora_conn.close()

        return 0 if sqlite_count == aurora_count else 1

    except Exception as e:
        logger.error(f"Error checking row counts: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
