"""Adapter to bridge desktop UI with Clean Architecture KeysetCollection.

Provides KeysetManager-compatible interface while delegating to KeysetCollection.
This allows gradual migration of desktop_ui/keysets_dialog.py without breaking changes.
"""

import traceback
from typing import List, Optional, Tuple
from uuid import UUID

from db.database_manager import DatabaseManager
from entities.keyset import Keyset
from helpers.debug_util import DebugUtil
from repositories.keyset_repository_postgres import PostgresKeysetRepository
from use_cases.keyset_collection import KeysetCollection


class KeysetManagerAdapter:
    """Adapter that wraps KeysetCollection to provide KeysetManager interface.

    This temporary adapter allows desktop UI to work with Clean Architecture
    without immediate refactoring. Future work: refactor UI to use KeysetCollection directly.
    """

    def __init__(self, *, db: DatabaseManager, debug_util: DebugUtil) -> None:
        """Initialize adapter with database and debug utility.

        Args:
            db: DatabaseManager instance for PostgreSQL access
            debug_util: Debug utility for logging
        """
        self._db = db
        self._debug_util = debug_util

        # Create repository and use case with dependency injection
        repository = PostgresKeysetRepository(db)
        self._collection = KeysetCollection(repository)

        # Cache for preloaded keysets (mimics old KeysetManager behavior)
        self._cache: dict[str, Keyset] = {}
        self._keyboard_id: Optional[UUID] = None
        self._debug_util.debugMessage("KeysetManagerAdapter: initialized")

    def preload_keysets_for_keyboard(self, *, keyboard_id: str) -> None:
        """Preload all keysets for a keyboard into cache.

        Args:
            keyboard_id: Keyboard UUID as string
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.preload_keysets_for_keyboard: keyboard_id={keyboard_id}"
        )
        self._load_collection(keyboard_id=keyboard_id)

    def get_cached_keysets(self) -> List[Keyset]:
        """Get all cached keysets ordered by progression.

        Returns:
            List of cached keysets sorted by progression_order
        """
        keysets = list(self._cache.values())
        keysets.sort(key=lambda k: k.progression_order)
        return keysets

    def list_keysets_for_keyboard(self, *, keyboard_id: str) -> List[Keyset]:
        """List all keysets for a keyboard from repository.

        Args:
            keyboard_id: Keyboard UUID as string

        Returns:
            List of keysets ordered by progression_order
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.list_keysets_for_keyboard: keyboard_id={keyboard_id}"
        )
        self._load_collection(keyboard_id=keyboard_id)
        ordered = self._collection.get_keysets_ordered()
        self._sync_cache()
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.list_keysets_for_keyboard: returning {len(ordered)} keysets"
        )
        return ordered

    def get_keyset_by_id(self, *, keyset_id: str) -> Optional[Keyset]:
        """Get a keyset by ID from cache or repository.

        Args:
            keyset_id: Keyset UUID as string

        Returns:
            Keyset if found, None otherwise
        """
        # Check cache first
        if keyset_id in self._cache:
            return self._cache[keyset_id]

        # Fallback to collection
        keyset = self._collection.get_keyset(keyset_id=keyset_id)
        if keyset:
            self._cache[keyset_id] = keyset
            return keyset

        # Last resort: fetch directly and hydrate collection/cache
        repo = PostgresKeysetRepository(self._db)
        fetched = repo.get_by_id(keyset_id)
        if fetched:
            self._load_collection(keyboard_id=str(fetched.keyboard_id))
            if fetched.keyset_id is not None:
                self._collection._keysets[str(fetched.keyset_id)] = fetched
            self._sync_cache()
        return fetched

    def get_keyset(self, *, keyset_id: str) -> Optional[Keyset]:
        """Alias for get_keyset_by_id for UI compatibility.

        Args:
            keyset_id: Keyset UUID as string

        Returns:
            Keyset if found, None otherwise
        """
        return self.get_keyset_by_id(keyset_id=keyset_id)

    def get_keys_for_keyset(self, *, keyset_id: str) -> List[Tuple[str, bool]]:
        """Get list of (key_char, is_new_key) tuples for a keyset.

        Args:
            keyset_id: Keyset UUID as string

        Returns:
            List of (key_char, is_new_key) tuples
        """
        keyset = self.get_keyset_by_id(keyset_id=keyset_id)
        if not keyset:
            return []
        return [(k.key_char, bool(k.is_new_key)) for k in keyset.keys]

    def save_keyset(self, *, keyset: Keyset, updated_by: str) -> Keyset:
        """Save keyset to repository (create or update with SCD-2).

        Args:
            keyset: Keyset to save
            updated_by: User ID as string (required, must be valid UUID)

        Returns:
            Saved keyset

        Raises:
            ValueError: If validation fails or updated_by is invalid
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.save_keyset: keyset_id={keyset.keyset_id}, "
            f"name={keyset.keyset_name}, updated_by={updated_by}"
        )
        # Ensure collection is loaded for this keyboard
        self._load_collection(keyboard_id=str(keyset.keyboard_id))

        existing = self._collection.get_keyset(keyset_id=str(keyset.keyset_id))
        if existing is None:
            # New keyset — stage it into the collection directly
            self._debug_util.debugMessage(
                "KeysetManagerAdapter.save_keyset: new keyset, staging into collection"
            )
            self._stage_keyset_into_collection(keyset)
        else:
            # Existing keyset — update the entity in-place
            self._debug_util.debugMessage(
                "KeysetManagerAdapter.save_keyset: updating existing keyset"
            )
            self._update_existing_keyset(existing, keyset)

        self._collection.save_all(updated_by=updated_by)
        self._sync_cache()

        saved = self._collection.get_keyset(keyset_id=str(keyset.keyset_id))
        if not saved:
            raise ValueError(f"Failed to save keyset {keyset.keyset_id}")
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.save_keyset: save complete, keyset_id={saved.keyset_id}"
        )
        return saved

    def save_all_keysets(self, *, keysets: List[Keyset], updated_by: str) -> bool:
        """Save multiple keysets to repository.

        Args:
            keysets: List of keysets to save
            updated_by: User ID as string (required, must be valid UUID)

        Returns:
            True if all keysets saved successfully
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.save_all_keysets: saving {len(keysets)} keysets, "
            f"updated_by={updated_by}"
        )
        try:
            if keysets:
                self._load_collection(keyboard_id=str(keysets[0].keyboard_id))

            for keyset in keysets:
                ks_id = str(keyset.keyset_id) if keyset.keyset_id else "None"
                self._debug_util.debugMessage(
                    f"KeysetManagerAdapter.save_all_keysets: processing keyset "
                    f"id={ks_id}, name={keyset.keyset_name}, "
                    f"order={keyset.progression_order}, keys={len(keyset.keys)}"
                )
                existing = self._collection.get_keyset(keyset_id=ks_id)
                if existing is None:
                    self._debug_util.debugMessage(
                        f"KeysetManagerAdapter.save_all_keysets: staging new keyset "
                        f"name={keyset.keyset_name}"
                    )
                    self._stage_keyset_into_collection(keyset)
                else:
                    self._debug_util.debugMessage(
                        f"KeysetManagerAdapter.save_all_keysets: updating existing keyset "
                        f"name={keyset.keyset_name}"
                    )
                    self._update_existing_keyset(existing, keyset)

            self._debug_util.debugMessage(
                "KeysetManagerAdapter.save_all_keysets: calling collection.save_all"
            )
            self._collection.save_all(updated_by=updated_by)
            self._sync_cache()
            self._debug_util.debugMessage(
                "KeysetManagerAdapter.save_all_keysets: save completed successfully"
            )
            return True
        except Exception as e:
            self._debug_util.debugMessage(
                f"KeysetManagerAdapter.save_all_keysets: FAILED with error: {e}"
            )
            self._debug_util.debugMessage(
                f"KeysetManagerAdapter.save_all_keysets: traceback:\n{traceback.format_exc()}"
            )
            return False

    def delete_keyset(self, *, keyset_id: str, deleted_by: str) -> bool:
        """Delete a keyset (soft delete with history closure).

        Args:
            keyset_id: Keyset UUID as string
            deleted_by: User ID as string (required, must be valid UUID)

        Returns:
            True if deleted, False if not found
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.delete_keyset: keyset_id={keyset_id}, "
            f"deleted_by={deleted_by}"
        )
        # Attempt to load collection based on cached or fetched keyset
        keyset = self.get_keyset_by_id(keyset_id=keyset_id)
        if keyset:
            self._load_collection(keyboard_id=str(keyset.keyboard_id))

        success = self._collection.delete_keyset(keyset_id=keyset_id)
        if success:
            self._collection.save_all(updated_by=deleted_by)
            self._cache.pop(keyset_id, None)
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.delete_keyset: success={success}"
        )
        return success

    def promote_keyset(self, *, keyboard_id: str, keyset_id: str, updated_by: str) -> bool:
        """Promote a keyset by swapping progression order with previous.

        Args:
            keyboard_id: Keyboard UUID as string
            keyset_id: Keyset UUID as string to promote
            updated_by: User ID as string (required, must be valid UUID)

        Returns:
            True if promoted, False if not found or already first
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.promote_keyset: keyset_id={keyset_id}"
        )
        self._load_collection(keyboard_id=keyboard_id)
        success, _swapped = self._collection.promote_keyset(keyset_id=keyset_id)
        if success:
            self._collection.save_all(updated_by=updated_by)
            self._sync_cache()
        return success

    def demote_keyset(self, *, keyboard_id: str, keyset_id: str, updated_by: str) -> bool:
        """Demote a keyset by swapping progression order with next.

        Args:
            keyboard_id: Keyboard UUID as string
            keyset_id: Keyset UUID as string to demote
            updated_by: User ID as string (required, must be valid UUID)

        Returns:
            True if demoted, False if not found or already last
        """
        self._debug_util.debugMessage(
            f"KeysetManagerAdapter.demote_keyset: keyset_id={keyset_id}"
        )
        self._load_collection(keyboard_id=keyboard_id)
        success, _swapped = self._collection.demote_keyset(keyset_id=keyset_id)
        if success:
            self._collection.save_all(updated_by=updated_by)
            self._sync_cache()
        return success

    def get_mastered_and_current_keys(
        self, *, keyboard_id: str, keyset_id: str
    ) -> Tuple[List[str], List[str]]:
        """Get mastered keys (earlier progressions) and current keys.

        Args:
            keyboard_id: Keyboard UUID as string
            keyset_id: Current keyset UUID as string

        Returns:
            Tuple of (mastered_keys, current_keys) as sorted lists
        """
        self._load_collection(keyboard_id=keyboard_id)
        return self._collection.get_mastered_and_current_keys(keyset_id=keyset_id)

    def validate_key_progression_uniqueness(
        self, *, keyboard_id: str, progression_order: int, new_keys: List[str]
    ) -> None:
        """Validate that new keys don't duplicate earlier progressions.

        Args:
            keyboard_id: Keyboard UUID as string
            progression_order: Target progression level
            new_keys: List of new key characters to validate

        Raises:
            ValueError: If any keys violate the progression uniqueness rule
        """
        # Use repository validation directly
        repository = PostgresKeysetRepository(self._db)
        repository.validate_key_progression_uniqueness(
            keyboard_id=keyboard_id,
            progression_order=progression_order,
            keys=new_keys,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_collection(self, *, keyboard_id: str) -> None:
        """Load collection from repository when keyboard changes or cache is empty."""
        if self._keyboard_id is None or str(self._keyboard_id) != keyboard_id:
            self._debug_util.debugMessage(
                f"KeysetManagerAdapter._load_collection: loading keyboard_id={keyboard_id}"
            )
            self._collection.load_for_keyboard(keyboard_id=keyboard_id)
            self._keyboard_id = UUID(keyboard_id)
            self._sync_cache()

    def _sync_cache(self) -> None:
        """Refresh cache from the collection's ordered state."""
        ordered = self._collection.get_keysets_ordered()
        self._cache = {str(ks.keyset_id): ks for ks in ordered}

    def _stage_keyset_into_collection(self, keyset: Keyset) -> None:
        """Stage a pre-built Keyset entity into the collection.

        Used by adapter methods that receive full Keyset entities from the UI.
        Places the entity directly into the collection's internal dict and marks dirty.
        """
        keyset_id = keyset.keyset_id
        if keyset_id is None:
            raise ValueError("Cannot stage keyset without keyset_id")
        keyset.is_dirty = True
        self._collection._keysets[keyset_id] = keyset
        self._collection.is_dirty = True
        self._collection._renumber()

    def _update_existing_keyset(self, existing: Keyset, updated: Keyset) -> None:
        """Update an existing keyset entity in-place from a UI-provided entity.

        Transfers mutable fields (name, keys) from the updated entity to
        the existing one already tracked by the collection.
        """
        if existing.keyset_name != updated.keyset_name:
            existing.keyset_name = updated.keyset_name
        existing.keys = updated.keys
        existing.progression_order = updated.progression_order
        existing.is_dirty = True
        self._collection.is_dirty = True
