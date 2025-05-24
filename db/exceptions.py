"""
Custom database exceptions for the AI Typing Trainer application.
"""

class DatabaseError(Exception):
    """Base class for all database-related exceptions."""
    pass

class ConnectionError(DatabaseError):
    """Raised when there are issues connecting to the database."""
    pass

class ForeignKeyError(DatabaseError):
    """Raised when a foreign key constraint fails."""
    pass

class SchemaError(DatabaseError):
    """Raised when there are issues with the database schema (e.g., missing columns)."""
    pass

class DatabaseTypeError(DatabaseError, TypeError):
    """Raised when there's a type mismatch in database operations."""
    pass

class ConstraintError(DatabaseError):
    """Raised when a database constraint is violated."""
    pass

class IntegrityError(DatabaseError):
    """Raised when database integrity is violated."""
    pass
