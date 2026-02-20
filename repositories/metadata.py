"""Shared SQLAlchemy metadata for all repositories.

This module provides a single MetaData instance used by all repository
implementations. This enables:
- Unified schema management via Alembic migrations
- Consistency across all table definitions
- Single source of truth for database schema

Usage in repositories:
    from repositories.metadata import metadata

    keyset_table = Table('keyset', metadata,
        Column('keyset_id', String(36), primary_key=True),
        ...
    )
"""

from sqlalchemy import MetaData

# Shared metadata instance for all repositories
# All table definitions should use this metadata
metadata = MetaData()
