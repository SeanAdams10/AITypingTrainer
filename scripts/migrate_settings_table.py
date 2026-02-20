#!/usr/bin/env python3
"""DEPRECATED: This script was for SQLite migrations.
The project is now PostgreSQL-only. Use db/SQL/schema.sql for PostgreSQL schema.

Legacy migration script to add missing columns to existing settings table.
This script adds created_at, updated_at, created_user_id, updated_user_id, valid_from, valid_to, and row_checksum columns.
"""

raise NotImplementedError(
    "This script is deprecated. The project is now PostgreSQL-only. "
    "Use db/SQL/schema.sql for PostgreSQL schema."
)
