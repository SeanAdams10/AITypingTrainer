"""Repository protocols (interfaces) for Clean Architecture.

This module defines the contracts that use cases depend on. Concrete implementations
live in separate files (e.g., keyset_repository_postgres.py, keyset_repository_memory.py).

Following the Dependency Inversion Principle: use cases depend on these abstractions,
not on concrete implementations.
"""

from __future__ import annotations

from typing import List, Optional, Protocol

from entities.keyset import Keyset


class IKeysetRepository(Protocol):
    """Protocol defining the contract for Keyset persistence operations.

    Use cases depend on this protocol, not on concrete implementations.
    This enables:
    - Testing with in-memory fakes (no database needed)
    - Swapping databases without changing business logic
    - Dependency injection in Lambda handlers

    All methods raise ValueError for validation errors or if operations fail.
    """

    def list_for_keyboard(self, keyboard_id: str) -> List[Keyset]:
        """Retrieve all current (active) keysets for a keyboard.

        Args:
            keyboard_id: The keyboard UUID

        Returns:
            List of Keyset entities with keys loaded, ordered by progression_order ASC.
            Empty list if no keysets exist.

        Raises:
            ValueError: If keyboard_id is invalid
        """
        ...

    def get_by_id(self, keyset_id: str) -> Optional[Keyset]:
        """Retrieve a single keyset by ID.

        Args:
            keyset_id: The keyset UUID

        Returns:
            Keyset entity with keys loaded, or None if not found

        Raises:
            ValueError: If keyset_id is invalid
        """
        ...

    def save(self, keyset: Keyset, *, updated_by: Optional[str] = None) -> None:
        """Save a keyset (create new or update existing with SCD-2 history).

        For new keysets (in_db=False):
        - Inserts new keyset record
        - Inserts keyset_key records
        - Inserts history records
        - Sets keyset.in_db = True, keyset.is_dirty = False

        For existing keysets (in_db=True, is_dirty=True):
        - Closes current history records (valid_to_dt = now, is_current=0)
        - Inserts new history version with version_no incremented
        - Updates keyset and keys if changed
        - Sets keyset.is_dirty = False

        For unchanged keysets (in_db=True, is_dirty=False):
        - No-op (checksum comparison detects no changes)

        Args:
            keyset: The Keyset entity to save
            updated_by: User ID performing the operation (for audit trail)

        Raises:
            ValueError: If validation fails (duplicate keys in progression, etc.)
        """
        ...

    def delete(self, keyset_id: str, *, deleted_by: Optional[str] = None) -> bool:
        """Delete a keyset (soft delete via SCD-2 history).

        Closes history records by setting valid_to_dt and is_current=0.
        The keyset record remains in the database for audit purposes.

        Args:
            keyset_id: The keyset UUID to delete
            deleted_by: User ID performing the operation (for audit trail)

        Returns:
            True if deleted, False if keyset not found

        Raises:
            ValueError: If keyset_id is invalid
        """
        ...

    def validate_key_progression_uniqueness(
        self,
        *,
        keyboard_id: str,
        progression_order: int,
        keys: List[str],
        keyset_id: Optional[str] = None,
    ) -> None:
        """Validate that new keys in this progression don't conflict with prior progressions.

        Business Rule: A key marked as 'new' (is_new_key=True) in progression N must not
        appear in any keyset with progression_order < N for the same keyboard.

        Args:
            keyboard_id: The keyboard UUID
            progression_order: The progression order being validated
            keys: List of key_char strings to check for conflicts
            keyset_id: Optional keyset_id to exclude from validation (for updates)

        Raises:
            ValueError: If any keys violate the progression uniqueness rule
        """
        ...
