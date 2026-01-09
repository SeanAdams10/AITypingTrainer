"""KeysetCollection - Use case for managing keysets with business logic.

This is the Use Cases layer of Clean Architecture. It orchestrates business rules,
coordinates entities, and depends only on repository protocols (not implementations).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_protocols import IKeysetRepository


class KeysetValidationError(Exception):
    """Raised when keyset validation fails (duplicate keys in progression, etc.)."""

    pass


class KeysetCollection:
    """In-memory aggregate enforcing business rules for keysets."""

    def __init__(self, repository: IKeysetRepository, *, keyboard_id: Optional[str] = None) -> None:
        """Construct a collection bound to a repository and optional keyboard."""
        self._repo = repository
        self._keyboard_id: Optional[str] = keyboard_id
        self._keysets: Dict[str, Keyset] = {}
        self._deleted_ids: set[str] = set()
        self.is_dirty: bool = False

    def _require_keyset_id(self, keyset: Keyset) -> str:
        """Return keyset_id or raise if missing to satisfy typing and invariants."""
        if keyset.keyset_id is None:
            raise ValueError("keyset_id is required")
        return keyset.keyset_id

    # --- Loading / listing -------------------------------------------------

    def load_for_keyboard(self, *, keyboard_id: str) -> None:
        """Populate collection from repository for a keyboard."""
        keysets = self._repo.list_for_keyboard(keyboard_id)
        self._keyboard_id = keyboard_id
        self._keysets = {
            self._require_keyset_id(ks): ks for ks in keysets if ks.keyset_id is not None
        }
        self._deleted_ids.clear()
        # Loaded state is clean
        for ks in self._keysets.values():
            ks.is_dirty = False
        self.is_dirty = False

    def list_for_keyboard(self, *, keyboard_id: Optional[str] = None) -> List[Keyset]:
        """Return ordered keysets, asserting keyboard matches if provided."""
        if keyboard_id is not None:
            self._ensure_keyboard(keyboard_id)
        return self.get_keysets_ordered()

    def get_keysets_ordered(self) -> List[Keyset]:
        """Return keysets ordered by progression_order."""
        return sorted(self._keysets.values(), key=lambda ks: ks.progression_order)

    def get_by_id(self, *, keyset_id: str) -> Optional[Keyset]:
        """Return a keyset by id if present."""
        return self._keysets.get(keyset_id)

    # --- Collection management --------------------------------------------

    def _next_progression(self) -> int:
        if not self._keysets:
            return 1
        return max(ks.progression_order for ks in self._keysets.values()) + 1

    def _renumber(self) -> bool:
        """Ensure progression_order is contiguous (1..N) and mark dirties when changed."""
        changed = False
        ordered = self.get_keysets_ordered()
        for idx, ks in enumerate(ordered, start=1):
            if ks.progression_order != idx:
                ks.progression_order = idx
                ks.is_dirty = True
                changed = True
        return changed

    def _ensure_keyboard(self, keyboard_id: str) -> None:
        if self._keyboard_id is None:
            self._keyboard_id = keyboard_id
        elif self._keyboard_id != keyboard_id:
            raise ValueError("Collection keyboard_id mismatch")

    def add_keyset(
        self,
        *,
        keyset_name: Optional[str] = None,
        keys: Optional[List[str]] = None,
        keyset: Optional[Keyset] = None,
    ) -> Keyset:
        """Create and stage a new keyset with automatic progression order.

        Accepts either explicit fields (`keyset_name`/`keys`) or an existing
        `Keyset` entity for backward compatibility with adapters/resolvers.
        """
        # Backward compatibility: allow passing an existing Keyset entity
        if keyset is not None:
            self._ensure_keyboard(keyset.keyboard_id)
            # Respect provided progression_order to avoid surprising swaps in callers
            if keyset.progression_order < 1:
                keyset.progression_order = self._next_progression()
            keyset.is_dirty = True
            keyset_id = self._require_keyset_id(keyset)
            self._keysets[keyset_id] = keyset
            self.is_dirty = True
            if self._renumber():
                self.is_dirty = True
            return keyset

        if keyset_name is None:
            raise ValueError("keyset_name is required when keyset is not provided")
        if self._keyboard_id is None:
            raise ValueError("keyboard_id must be set before adding keysets")

        progression = self._next_progression()
        key_entities = [KeysetKey(key_char=k, is_new_key=True) for k in keys or []]
        ks = Keyset(
            keyboard_id=self._keyboard_id,
            keyset_name=keyset_name,
            progression_order=progression,
            keys=key_entities,
            in_db=False,
            is_dirty=True,
        )
        self._keysets[self._require_keyset_id(ks)] = ks
        self.is_dirty = True
        if self._renumber():
            self.is_dirty = True
        return ks

    def insert_keyset_before(
        self,
        *,
        keyset_name: Optional[str] = None,
        before_keyset_id: Optional[str] = None,
        keys: Optional[List[str]] = None,
        keyset: Optional[Keyset] = None,
    ) -> Keyset:
        """Insert a keyset before another (or append if target not provided) and renumber."""
        if before_keyset_id is not None and before_keyset_id not in self._keysets:
            raise ValueError("before_keyset_id not found in collection")

        # Determine target progression slot
        target_progression = None
        if before_keyset_id:
            target = self._keysets[before_keyset_id]
            target_progression = target.progression_order
        else:
            target_progression = self._next_progression()

        # Delegate to add logic but override progression_order to target then renumber
        if keyset is not None:
            keyset.progression_order = target_progression
            added = self.add_keyset(keyset=keyset)
        else:
            added = self.add_keyset(keyset_name=keyset_name, keys=keys)
            added.progression_order = target_progression

        # Renumber to contiguous 1..N regardless of initial ordering
        if self._renumber():
            self.is_dirty = True
        self.is_dirty = True
        return added

    def delete_keyset(self, *, keyset_id: str, deleted_by: Optional[str] = None) -> bool:
        """Delete a keyset and renumber progression ordering."""
        if keyset_id not in self._keysets:
            return False
        del self._keysets[keyset_id]
        self._deleted_ids.add(keyset_id)
        self._renumber()
        self.is_dirty = True
        return True

    def rename_keyset(self, *, keyset_id: str, new_name: str) -> bool:
        """Rename a keyset if it exists."""
        ks = self._keysets.get(keyset_id)
        if not ks:
            return False
        ks.keyset_name = new_name
        ks.is_dirty = True
        self.is_dirty = True
        return True

    # --- Key management ----------------------------------------------------

    def key_exists_in_collection(self, *, key_char: str) -> Optional[str]:
        """Return keyset id containing the key_char if found."""
        for ks in self._keysets.values():
            if ks.has_key(key_char):
                if ks.keyset_id is not None:
                    return ks.keyset_id
        return None

    def add_key_to_keyset(
        self, *, keyset_id: str, key_char: str, is_new_key: bool = True
    ) -> KeysetKey:
        """Add a key enforcing progression uniqueness and move-from-later rule."""
        ks = self._keysets.get(keyset_id)
        if not ks:
            raise ValueError("keyset_id not found")

        # Progressive uniqueness: cannot add as new if exists in earlier progression
        earlier = [
            k for k in self.get_keysets_ordered() if k.progression_order < ks.progression_order
        ]
        if is_new_key:
            if any(k.has_key(key_char) for k in earlier):
                raise KeysetValidationError(
                    f"Key '{key_char}' already exists in an earlier progression"
                )

        # If key exists in later keyset, remove it there (move rule)
        later = [
            k for k in self.get_keysets_ordered() if k.progression_order > ks.progression_order
        ]
        for other in later:
            if other.remove_key(key_char=key_char):
                other.is_dirty = True

        added = ks.add_key(key_char=key_char, is_new_key=is_new_key)
        ks.is_dirty = True
        self.is_dirty = True
        return added

    def remove_key_from_keyset(self, *, keyset_id: str, key_char: str) -> bool:
        """Remove a key from a keyset and mark dirty if changed."""
        ks = self._keysets.get(keyset_id)
        if not ks:
            return False
        removed = ks.remove_key(key_char=key_char)
        if removed:
            self.is_dirty = True
        return removed

    # --- Ordering ----------------------------------------------------------

    def _renumber(self) -> None:
        ordered = self.get_keysets_ordered()
        for idx, ks in enumerate(ordered, start=1):
            if ks.progression_order != idx:
                ks.progression_order = idx
                ks.is_dirty = True

    def _recalc_dirty(self) -> None:
        self.is_dirty = bool(self._deleted_ids) or any(ks.is_dirty for ks in self._keysets.values())

    def promote_keyset(
        self, *, keyset_id: str, keyboard_id: Optional[str] = None, updated_by: Optional[str] = None
    ) -> Tuple[bool, Optional[Keyset]]:
        """Move a keyset earlier in progression, optionally swapping in DB when persisted."""
        if keyboard_id is not None:
            self._ensure_keyboard(keyboard_id)
        ordered = self.get_keysets_ordered()
        for idx, ks in enumerate(ordered):
            if ks.keyset_id == keyset_id:
                if idx == 0:
                    return (False, None)
                prev_ks = ordered[idx - 1]
                ks.progression_order, prev_ks.progression_order = (
                    prev_ks.progression_order,
                    ks.progression_order,
                )
                ks.is_dirty = True
                prev_ks.is_dirty = True

                # If both persisted, use atomic repo swap to avoid unique constraint collisions
                if ks.in_db and prev_ks.in_db and updated_by:
                    self._repo.swap_progression_order(ks, prev_ks, updated_by=updated_by)
                    ks.is_dirty = False
                    prev_ks.is_dirty = False
                    self._recalc_dirty()
                else:
                    self.is_dirty = True
                if self._renumber():
                    self.is_dirty = True
                return (True, prev_ks)
        return (False, None)

    def demote_keyset(
        self, *, keyset_id: str, keyboard_id: Optional[str] = None, updated_by: Optional[str] = None
    ) -> Tuple[bool, Optional[Keyset]]:
        """Move a keyset later in progression, optionally swapping in DB when persisted."""
        if keyboard_id is not None:
            self._ensure_keyboard(keyboard_id)
        ordered = self.get_keysets_ordered()
        for idx, ks in enumerate(ordered):
            if ks.keyset_id == keyset_id:
                if idx == len(ordered) - 1:
                    return (False, None)
                next_ks = ordered[idx + 1]
                ks.progression_order, next_ks.progression_order = (
                    next_ks.progression_order,
                    ks.progression_order,
                )
                ks.is_dirty = True
                next_ks.is_dirty = True

                if ks.in_db and next_ks.in_db and updated_by:
                    self._repo.swap_progression_order(ks, next_ks, updated_by=updated_by)
                    ks.is_dirty = False
                    next_ks.is_dirty = False
                    self._recalc_dirty()
                else:
                    self.is_dirty = True
                if self._renumber():
                    self.is_dirty = True
                return (True, next_ks)
        return (False, None)

    # --- Query helpers ----------------------------------------------------

    def get_mastered_and_current_keys(
        self, *, keyset_id: str, keyboard_id: Optional[str] = None
    ) -> Tuple[List[str], List[str]]:
        """Return mastered keys (earlier progressions) and current keys for a keyset."""
        if keyboard_id is not None:
            self._ensure_keyboard(keyboard_id)
        current = self._keysets.get(keyset_id)
        if not current:
            return ([], [])

        earlier = [
            ks
            for ks in self.get_keysets_ordered()
            if ks.progression_order < current.progression_order
        ]
        mastered = sorted({k.key_char for ks in earlier for k in ks.keys})
        current_keys = sorted([k.key_char for k in current.keys])
        return (mastered, current_keys)

    # --- Persistence ------------------------------------------------------

    def save_all(self, *, updated_by: str) -> None:
        """Validate and persist all keysets plus deletions through the repository."""
        # Ensure contiguous ordering before validations/persistence
        if self._renumber():
            self.is_dirty = True

        # Validate progression uniqueness and names are unique within collection
        names = set()
        for ks in self._keysets.values():
            if ks.keyset_name.lower() in names:
                raise KeysetValidationError("Duplicate keyset name in collection")
            names.add(ks.keyset_name.lower())

        # Validate progressive uniqueness for new keys
        ordered = self.get_keysets_ordered()
        for idx, ks in enumerate(ordered):
            earlier_keys = {k.key_char for prior in ordered[:idx] for k in prior.keys}
            for key in ks.keys:
                if key.is_new_key and key.key_char in earlier_keys:
                    raise KeysetValidationError(
                        f"Key '{key.key_char}' already exists in earlier progression"
                    )

        # Persist all keysets via repository
        for ks in ordered:
            self._repo.save(ks, updated_by=updated_by)
            ks.in_db = True
            ks.is_dirty = False

        # Persist deletions after saves to keep orders intact
        for keyset_id in list(self._deleted_ids):
            self._repo.delete(keyset_id, deleted_by=updated_by)
            self._deleted_ids.discard(keyset_id)

        self.is_dirty = False

    # --- Backward compatibility helpers ----------------------------------

    def update_keyset(self, *, keyset: Keyset, updated_by: Optional[str] = None) -> Keyset:
        """Update an existing keyset in the collection and mark as dirty."""
        if keyset.keyset_id not in self._keysets:
            raise ValueError("keyset_id not found in collection")
        self._ensure_keyboard(keyset.keyboard_id)
        self._keysets[keyset.keyset_id] = keyset
        keyset.is_dirty = True
        self.is_dirty = True
        self._renumber()
        return keyset
