"""In-memory implementation of IKeysetRepository for testing.

This implementation stores keysets in memory dictionaries, making tests fast and
deterministic without database dependencies. Perfect for use case unit tests.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from uuid import uuid4

from entities.keyset import Keyset


class InMemoryKeysetRepository:
    """In-memory repository for testing use cases without database dependencies.

    Implements the IKeysetRepository protocol. Stores data in dictionaries,
    simulates SCD-2 history behavior (soft deletes), and validates business rules.

    Usage in tests:
        repo = InMemoryKeysetRepository()
        keyset_collection = KeysetCollection(repo)  # Dependency injection
        # Test business logic without touching a database
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        # Storage: {keyset_id: Keyset}
        self._keysets: Dict[str, Keyset] = {}
        # Track deleted keysets (soft delete simulation)
        self._deleted_ids: set[str] = set()

    def list_for_keyboard(self, keyboard_id: str) -> List[Keyset]:
        """Retrieve all current (active) keysets for a keyboard.

        Args:
            keyboard_id: The keyboard UUID

        Returns:
            List of Keyset entities, ordered by progression_order ASC.
            Excludes soft-deleted keysets.
        """
        if not keyboard_id or not isinstance(keyboard_id, str):
            raise ValueError("keyboard_id must be a non-empty string")

        keysets = [
            ks
            for ks in self._keysets.values()
            if ks.keyboard_id == keyboard_id and ks.keyset_id not in self._deleted_ids
        ]
        return sorted(keysets, key=lambda k: k.progression_order)

    def get_by_id(self, keyset_id: str) -> Optional[Keyset]:
        """Retrieve a single keyset by ID.

        Args:
            keyset_id: The keyset UUID

        Returns:
            Keyset entity or None if not found or deleted
        """
        if not keyset_id or not isinstance(keyset_id, str):
            raise ValueError("keyset_id must be a non-empty string")

        if keyset_id in self._deleted_ids:
            return None

        return self._keysets.get(keyset_id)

    def save(self, keyset: Keyset, *, updated_by: Optional[str] = None) -> None:
        """Save a keyset (create new or update existing).

        Simulates SCD-2 history by storing a deep copy of the keyset state.
        Updates in_db and is_dirty flags appropriately.

        Args:
            keyset: The Keyset entity to save
            updated_by: User ID for audit trail (stored but not used in memory impl)
        """
        if not keyset.keyset_id:
            keyset.keyset_id = str(uuid4())

        # Validate business rules
        new_keys = [k.key_char for k in keyset.keys if k.is_new_key]
        if new_keys:
            self.validate_key_progression_uniqueness(
                keyboard_id=keyset.keyboard_id,
                progression_order=keyset.progression_order,
                keys=new_keys,
                keyset_id=keyset.keyset_id,
            )

        # Deep copy to simulate database storage (prevent mutations)
        stored_keyset = Keyset.from_dict(keyset.to_dict())
        stored_keyset.in_db = True
        stored_keyset.is_dirty = False
        if stored_keyset.keyset_id:
            self._keysets[stored_keyset.keyset_id] = stored_keyset

        # Update original entity flags
        keyset.in_db = True
        keyset.is_dirty = False

    def delete(self, keyset_id: str, *, deleted_by: Optional[str] = None) -> bool:
        """Delete a keyset (soft delete).

        Args:
            keyset_id: The keyset UUID to delete
            deleted_by: User ID for audit trail (stored but not used in memory impl)

        Returns:
            True if deleted, False if keyset not found
        """
        if not keyset_id or not isinstance(keyset_id, str):
            raise ValueError("keyset_id must be a non-empty string")

        if keyset_id not in self._keysets or keyset_id in self._deleted_ids:
            return False

        self._deleted_ids.add(keyset_id)
        return True

    def validate_key_progression_uniqueness(
        self,
        *,
        keyboard_id: str,
        progression_order: int,
        keys: List[str],
        keyset_id: Optional[str] = None,
    ) -> None:
        """Validate that new keys don't conflict with prior progressions.

        Business Rule: A key marked as 'new' in progression N must not appear
        in any keyset with progression_order < N for the same keyboard.

        Args:
            keyboard_id: The keyboard UUID
            progression_order: The progression order being validated
            keys: List of key_char strings to check
            keyset_id: Optional keyset_id to exclude from validation (for updates)

        Raises:
            ValueError: If any keys violate the progression uniqueness rule
        """
        if not keyboard_id or not isinstance(keyboard_id, str):
            raise ValueError("keyboard_id must be a non-empty string")
        if progression_order < 1:
            raise ValueError("progression_order must be >= 1")

        # Get all keysets for this keyboard with lower progression_order
        prior_keysets = [
            ks
            for ks in self._keysets.values()
            if ks.keyboard_id == keyboard_id
            and ks.progression_order < progression_order
            and ks.keyset_id not in self._deleted_ids
            and ks.keyset_id != keyset_id  # Exclude self for updates
        ]

        # Collect all keys from prior progressions
        prior_keys = set()
        for ks in prior_keysets:
            for k in ks.keys:
                prior_keys.add(k.key_char)

        # Check for conflicts
        conflicts = [key for key in keys if key in prior_keys]
        if conflicts:
            raise ValueError(
                f"Keys {conflicts} marked as new in progression {progression_order} "
                f"already exist in earlier progressions for keyboard {keyboard_id}"
            )

    def swap_progression_order(
        self,
        keyset1: Keyset,
        keyset2: Keyset,
        *,
        updated_by: Optional[str] = None,
    ) -> None:
        """Atomically swap the progression_order of two keysets.

        In-memory implementation simply updates both keysets' progression orders.

        Args:
            keyset1: First keyset (with updated progression_order already set)
            keyset2: Second keyset (with updated progression_order already set)
            updated_by: User ID performing the operation (for audit trail)

        Raises:
            ValueError: If keysets belong to different keyboards
        """
        if keyset1.keyboard_id != keyset2.keyboard_id:
            raise ValueError("Cannot swap progression order between different keyboards")

        # Save both keysets with their updated progression orders
        self.save(keyset1, updated_by=updated_by)
        self.save(keyset2, updated_by=updated_by)

    def clear(self) -> None:
        """Clear all stored data (useful for test cleanup)."""
        self._keysets.clear()
        self._deleted_ids.clear()

    def count(self) -> int:
        """Return count of active (non-deleted) keysets (useful for testing)."""
        return len([ks for ks in self._keysets.values() if ks.keyset_id not in self._deleted_ids])
