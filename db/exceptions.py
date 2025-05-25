"""
Custom database exceptions for the AI Typing Trainer application.
"""


class DatabaseError(Exception):
    """Base class for all database-related exceptions."""


class DBConnectionError(DatabaseError):
    """Raised when there are issues connecting to the database."""


class ForeignKeyError(DatabaseError):
    """Raised when a foreign key constraint fails."""


class ConstraintError(DatabaseError):
    """Raised when a database constraint is violated."""


class DatabaseTypeError(DatabaseError, TypeError):
    """Raised when there's a type mismatch in database operations."""


class IntegrityError(DatabaseError):
    """Raised when database integrity is violated."""


class SchemaError(DatabaseError):
    """Raised when there are schema-related issues."""


class TableNotFoundError(DatabaseError):
    """Raised when a table is not found in the database."""
