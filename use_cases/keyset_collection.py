"""KeysetCollection - Use case for managing keysets with business logic.

This is the Use Cases layer of Clean Architecture. It orchestrates business rules,
coordinates entities, and depends only on repository protocols (not implementations).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from entities.keyset import Keyset
from repositories.keyset_protocols import IKeysetRepository


class KeysetValidationError(Exception):
    """Raised when keyset validation fails (duplicate keys in progression, etc.)."""

    pass


class KeysetCollection:
    """Aggregate for managing keysets with business logic enforcement.

    This use case implements business rules for keyset management:
    - Key progression uniqueness validation
    - Keyset ordering and retrieval
    - Batch operations with transactional semantics

    Depends on IKeysetRepository protocol for persistence, enabling:
    - Testing with in-memory fakes (no database)
    - Swapping persistence implementations (PostgreSQL, MongoDB, etc.)
    - Dependency injection in Lambda handlers

    Usage:
        repo = PostgresKeysetRepository(db)  # Or InMemoryKeysetRepository()
        collection = KeysetCollection(repo)
        keysets = collection.list_for_keyboard(keyboard_id)
        collection.add_keyset(keyset)
    """

    def __init__(self, repository: IKeysetRepository) -> None:
        """Initialize collection with repository dependency.

        Args:
            repository: Implementation of IKeysetRepository protocol
        """
        self._repo = repository

    def list_for_keyboard(self, *, keyboard_id: str) -> List[Keyset]:
        """List all active keysets for a keyboard, ordered by progression.

        Args:
            keyboard_id: The keyboard UUID

        Returns:
            List of Keyset entities ordered by progression_order ASC

        Raises:
            ValueError: If keyboard_id is invalid
        """
        return self._repo.list_for_keyboard(keyboard_id)

    def get_by_id(self, *, keyset_id: str) -> Optional[Keyset]:
        """Retrieve a single keyset by ID.

        Args:
            keyset_id: The keyset UUID

        Returns:
            Keyset entity or None if not found

        Raises:
            ValueError: If keyset_id is invalid
        """
        return self._repo.get_by_id(keyset_id)

    def add_keyset(self, keyset: Keyset, *, updated_by: str) -> None:
        """Add a new keyset with business rule validation.

        Business Rules Enforced:
        1. Key progression uniqueness: New keys cannot appear in earlier progressions
        2. Keyset name must be unique within keyboard (delegated to repository)
        3. Progression order must be positive

        Args:
            keyset: The Keyset entity to add
            updated_by: User ID performing the operation (required, must be valid UUID)

        Raises:
            KeysetValidationError: If business rules are violated
            ValueError: If entity validation fails or updated_by is invalid
        """
        # Validate entity constraints (done by Pydantic)
        if not keyset.keyboard_id:
            raise ValueError("keyboard_id is required")
        if not keyset.keyset_name:
            raise ValueError("keyset_name is required")
        if keyset.progression_order < 1:
            raise ValueError("progression_order must be >= 1")

        # Validate business rule: key progression uniqueness
        new_keys = [k.key_char for k in keyset.keys if k.is_new_key]
        if new_keys:
            try:
                self._repo.validate_key_progression_uniqueness(
                    keyboard_id=keyset.keyboard_id,
                    progression_order=keyset.progression_order,
                    keys=new_keys,
                    keyset_id=None,  # New keyset, no ID yet
                )
            except ValueError as e:
                raise KeysetValidationError(str(e)) from e

        # Persist
        self._repo.save(keyset, updated_by=updated_by)

    def update_keyset(self, keyset: Keyset, *, updated_by: str) -> None:
        """Update an existing keyset with business rule validation.

        Business Rules Enforced:
        1. Key progression uniqueness (excluding self from validation)
        2. Keyset must exist in database (in_db=True)
        3. Changes trigger dirty flag

        Args:
            keyset: The Keyset entity to update
            updated_by: User ID performing the operation (required, must be valid UUID)

        Raises:
            KeysetValidationError: If business rules are violated
            ValueError: If entity not found, validation fails, or updated_by is invalid
        """
        if not keyset.in_db:
            raise ValueError(
                f"Keyset {keyset.keyset_id} not found in database. "
                "Use add_keyset() for new keysets."
            )

        # Validate business rule: key progression uniqueness (excluding self)
        new_keys = [k.key_char for k in keyset.keys if k.is_new_key]
        if new_keys:
            try:
                self._repo.validate_key_progression_uniqueness(
                    keyboard_id=keyset.keyboard_id,
                    progression_order=keyset.progression_order,
                    keys=new_keys,
                    keyset_id=keyset.keyset_id,  # Exclude self from validation
                )
            except ValueError as e:
                raise KeysetValidationError(str(e)) from e

        # Persist
        self._repo.save(keyset, updated_by=updated_by)

    def delete_keyset(self, *, keyset_id: str, deleted_by: str) -> bool:
        """Delete a keyset (soft delete via SCD-2 history).

        Args:
            keyset_id: The keyset UUID to delete
            deleted_by: User ID performing the operation (required, must be valid UUID)

        Returns:
            True if deleted, False if keyset not found

        Raises:
            ValueError: If keyset_id is invalid or deleted_by is invalid
        """
        return self._repo.delete(keyset_id, deleted_by=deleted_by)

    def save_all(self, keysets: List[Keyset], *, updated_by: str) -> None:
        """Save multiple keysets in batch with validation.

        All keysets are validated before any are saved, providing transactional semantics.
        If any validation fails, none are saved.

        Args:
            keysets: List of Keyset entities to save
            updated_by: User ID performing the operation (required, must be valid UUID)

        Raises:
            KeysetValidationError: If any business rules are violated
            ValueError: If entity validation fails or updated_by is invalid
        """
        # Validate all keysets first
        for keyset in keysets:
            new_keys = [k.key_char for k in keyset.keys if k.is_new_key]
            if new_keys:
                try:
                    self._repo.validate_key_progression_uniqueness(
                        keyboard_id=keyset.keyboard_id,
                        progression_order=keyset.progression_order,
                        keys=new_keys,
                        keyset_id=keyset.keyset_id if keyset.in_db else None,
                    )
                except ValueError as e:
                    raise KeysetValidationError(
                        f"Validation failed for keyset '{keyset.keyset_name}': {e}"
                    ) from e

        # All validated, now save
        for keyset in keysets:
            self._repo.save(keyset, updated_by=updated_by)

    def get_mastered_and_current_keys(
        self, *, keyboard_id: str, keyset_id: str
    ) -> Tuple[List[str], List[str]]:
        """Get mastered keys (from earlier keysets) and current keyset keys.

        This supports UI features showing which keys have been learned in earlier
        progressions vs which are being introduced in the current keyset.

        Args:
            keyboard_id: The keyboard UUID
            keyset_id: The current keyset UUID

        Returns:
            Tuple of (mastered_keys, current_keys) where:
            - mastered_keys: Sorted list of unique key_char from keysets with lower progression_order
            - current_keys: Sorted list of key_char from the current keyset

        Raises:
            ValueError: If keyboard_id or keyset_id is invalid
        """
        # Get current keyset
        current_keyset = self._repo.get_by_id(keyset_id)
        if not current_keyset:
            return ([], [])

        # Verify keyboard matches
        if current_keyset.keyboard_id != keyboard_id:
            raise ValueError(f"Keyset {keyset_id} does not belong to keyboard {keyboard_id}")

        # Get all keysets for keyboard
        all_keysets = self._repo.list_for_keyboard(keyboard_id)

        # Filter keysets with lower progression order
        earlier_keysets = [
            ks for ks in all_keysets if ks.progression_order < current_keyset.progression_order
        ]

        # Collect unique keys from earlier keysets
        mastered_keys_set = set()
        for ks in earlier_keysets:
            for k in ks.keys:
                mastered_keys_set.add(k.key_char)

        mastered_keys = sorted(list(mastered_keys_set))

        # Get keys from current keyset
        current_keys = sorted([k.key_char for k in current_keyset.keys])

        return (mastered_keys, current_keys)

    def promote_keyset(
        self, *, keyboard_id: str, keyset_id: str, updated_by: str
    ) -> Tuple[bool, Optional[Keyset]]:
        """Promote a keyset by swapping its progression order with the previous keyset.

        Promotion moves a keyset UP in the progression (to a lower progression_order),
        meaning it will be practiced earlier in the learning sequence.

        Business Logic:
        1. Find target keyset and previous keyset (by progression_order)
        2. Swap their progression_order values
        3. Save both with updated_by for audit trail

        Args:
            keyboard_id: The keyboard UUID
            keyset_id: The keyset UUID to promote
            updated_by: User ID performing the operation (required, must be valid UUID)

        Returns:
            Tuple of (success, swapped_keyset):
            - (True, swapped_keyset) if promoted successfully
            - (False, None) if keyset is already first or not found

        Raises:
            ValueError: If keyboard_id, keyset_id, or updated_by is invalid
        """
        # Get all keysets for keyboard
        keysets = self._repo.list_for_keyboard(keyboard_id)

        # Find target keyset
        target = None
        for ks in keysets:
            if ks.keyset_id == keyset_id:
                target = ks
                break

        if not target:
            return (False, None)

        # Find previous keyset (lower progression_order, closest to target)
        prev_keyset = None
        for ks in keysets:
            if ks.progression_order < target.progression_order:
                if prev_keyset is None or ks.progression_order > prev_keyset.progression_order:
                    prev_keyset = ks

        if not prev_keyset:
            return (False, None)  # Already first

        # Swap progression orders
        target.progression_order, prev_keyset.progression_order = (
            prev_keyset.progression_order,
            target.progression_order,
        )

        # Mark as dirty to trigger save
        target.is_dirty = True
        prev_keyset.is_dirty = True

        # Use atomic swap to avoid unique constraint violation
        self._repo.swap_progression_order(target, prev_keyset, updated_by=updated_by)

        return (True, prev_keyset)

    def demote_keyset(
        self, *, keyboard_id: str, keyset_id: str, updated_by: str
    ) -> Tuple[bool, Optional[Keyset]]:
        """Demote a keyset by swapping its progression order with the next keyset.

        Demotion moves a keyset DOWN in the progression (to a higher progression_order),
        meaning it will be practiced later in the learning sequence.

        Business Logic:
        1. Find target keyset and next keyset (by progression_order)
        2. Swap their progression_order values
        3. Save both with updated_by for audit trail

        Args:
            keyboard_id: The keyboard UUID
            keyset_id: The keyset UUID to demote
            updated_by: User ID performing the operation (required, must be valid UUID)

        Returns:
            Tuple of (success, swapped_keyset):
            - (True, swapped_keyset) if demoted successfully
            - (False, None) if keyset is already last or not found

        Raises:
            ValueError: If keyboard_id, keyset_id, or updated_by is invalid
        """
        # Get all keysets for keyboard
        keysets = self._repo.list_for_keyboard(keyboard_id)

        # Find target keyset
        target = None
        for ks in keysets:
            if ks.keyset_id == keyset_id:
                target = ks
                break

        if not target:
            return (False, None)

        # Find next keyset (higher progression_order, closest to target)
        next_keyset = None
        for ks in keysets:
            if ks.progression_order > target.progression_order:
                if next_keyset is None or ks.progression_order < next_keyset.progression_order:
                    next_keyset = ks

        if not next_keyset:
            return (False, None)  # Already last

        # Swap progression orders
        target.progression_order, next_keyset.progression_order = (
            next_keyset.progression_order,
            target.progression_order,
        )

        # Mark as dirty to trigger save
        target.is_dirty = True
        next_keyset.is_dirty = True

        # Use atomic swap to avoid unique constraint violation
        self._repo.swap_progression_order(target, next_keyset, updated_by=updated_by)

        return (True, next_keyset)
