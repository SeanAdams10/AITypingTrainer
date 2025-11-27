"""Repositories layer - Persistence adapters.

This package contains:
- Repository protocols (interfaces) in keyset_protocols.py
- Concrete repository implementations (PostgreSQL, in-memory)

Repositories handle:
- Database operations (CRUD)
- SCD-2 history tracking
- Checksum-based no-op detection
- Row-to-entity mapping
"""
