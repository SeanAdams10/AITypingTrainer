"""KeysetCollection - Use case for managing keysets with business logic.

This is the Use Cases layer of Clean Architecture. It orchestrates business rules,
coordinates entities, and depends only on repository protocols (not implementations).

Spec: Requirements/Keyset_req.md Section 3.2
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

    def __init__(
        self, repository: IKeysetRepository, *, keyboard_id: Optional[str] = None
    ) -> None:
        """Construct a collection bound to a repository and optional keyboard."""
        self._repo = repository
        self._keyboard_id: Optional[str] = keyboard_id
        self._keysets: Dict[str, Keyset] = {}
        self._deleted_ids: set[str] = set()
        self.is_dirty: bool = False

    # --- Private helpers ---------------------------------------------------

    def _require_keyset_id(self, keyset: Keyset) -> str:
        """Return keyset_id or raise if missing to satisfy typing and invariants."""
        if keyset.keyset_id is None:
            raise ValueError("keyset_id is required")
        return keyset.keyset_id

    def _next_progression(self) -> int:
        if not self._keysets:
            return 1
        return max(ks.progression_order for ks in self._keysets.values()) + 1

    def _renumber(self) -> bool:
        """Ensure progression_order is contiguous 1..N; return True if any changed."""
        changed = False
        ordered = sorted(self._keysets.values(), key=lambda ks: ks.progression_order)
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

    # --- Loading / listing -------------------------------------------------

    def load_for_keyboard(self, *, keyboard_id: str) -> None:
        """Populate collection from repository for a keyboard."""
        keysets = self._repo.list_for_keyboard(keyboard_id)
        self._keyboard_id = keyboard_id
        self._keysets = {
            self._require_keyset_id(ks): ks
            for ks in keysets
            if ks.keyset_id is not None
        }
        self._deleted_ids.clear()
        for ks in self._keysets.values():
            ks.is_dirty = False
        self.is_dirty = False

    def get_keysets_ordered(self) -> List[Keyset]:
        """Return keysets ordered by progression_order."""
        return sorted(self._keysets.values(), key=lambda ks: ks.progression_order)

    def get_keyset(self, *, keyset_id: str) -> Optional[Keyset]:
        """Return a keyset by id, or None if not present."""
        return self._keysets.get(keyset_id)

    # --- Collection management --------------------------------------------

    def add_keyset(
        self,
        *,
        keyset_name: Optional[str] = None,
        keys: Optional[List[str]] = None,
    ) -> Keyset:
        """Create and stage a new keyset appended at end.

        Args:
            keyset_name: Display name (required, 1-100 chars).
            keys: Optional list of key_char strings to populate.

        Returns:
            The newly created Keyset entity.
        """
        if keyset_name is None:
            raise ValueError("keyset_name is required")
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
        self._renumber()
        return ks

    def insert_keyset_before(
        self,
        *,
        keyset_name: Optional[str] = None,
        before_keyset_id: Optional[str] = None,
        keys: Optional[List[str]] = None,
    ) -> Keyset:
        """Insert a keyset before another (or append if before_keyset_id is None).

        Shifts existing keysets at or after the target position up by one,
        then inserts at the freed slot and renumbers to contiguous 1..N.
        """
        if before_keyset_id is not None and before_keyset_id not in self._keysets:
            raise ValueError("before_keyset_id not found in collection")

        # If no target, just append
        if before_keyset_id is None:
            return self.add_keyset(keyset_name=keyset_name, keys=keys)

        if keyset_name is None:
            raise ValueError("keyset_name is required")
        if self._keyboard_id is None:
            raise ValueError("keyboard_id must be set before adding keysets")

        # Shift existing keysets at or after target position up by 1
        target = self._keysets[before_keyset_id]
        target_order = target.progression_order
        for ks in self._keysets.values():
            if ks.progression_order >= target_order:
                ks.progression_order += 1
                ks.is_dirty = True

        # Create new keyset at the freed slot
        key_entities = [KeysetKey(key_char=k, is_new_key=True) for k in keys or []]
        new_ks = Keyset(
            keyboard_id=self._keyboard_id,
            keyset_name=keyset_name,
            progression_order=target_order,
            keys=key_entities,
            in_db=False,
            is_dirty=True,
        )
        self._keysets[self._require_keyset_id(new_ks)] = new_ks
        self._renumber()
        self.is_dirty = True
        return new_ks

    def delete_keyset(self, *, keyset_id: str) -> bool:
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
        """Return keyset_id containing the key_char, or None."""
        for ks in self._keysets.values():
            if ks.has_key(key_char=key_char):
                if ks.keyset_id is not None:
                    return ks.keyset_id
        return None

    def add_key_to_keyset(
        self, *, keyset_id: str, key_char: str, is_new_key: bool = True
    ) -> KeysetKey:
        """Add a key enforcing progression uniqueness and move-from-later rule (AC-9)."""
        ks = self._keysets.get(keyset_id)
        if not ks:
            raise ValueError("keyset_id not found")

        earlier = [
            k
            for k in self.get_keysets_ordered()
            if k.progression_order < ks.progression_order
        ]
        if is_new_key and any(k.has_key(key_char=key_char) for k in earlier):
            raise KeysetValidationError(
                f"Key '{key_char}' already exists in an earlier progression"
            )

        # If key exists in later keyset, remove it (move rule)
        later = [
            k
            for k in self.get_keysets_ordered()
            if k.progression_order > ks.progression_order
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

    # --- Ordering (AC-11) --------------------------------------------------

    def promote_keyset(
        self, *, keyset_id: str
    ) -> Tuple[bool, Optional[Keyset]]:
        """Swap keyset with the one before it. No-op if already first."""
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
                self.is_dirty = True
                self._renumber()
                return (True, prev_ks)
        return (False, None)

    def demote_keyset(
        self, *, keyset_id: str
    ) -> Tuple[bool, Optional[Keyset]]:
        """Swap keyset with the one after it. No-op if already last."""
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
                self.is_dirty = True
                self._renumber()
                return (True, next_ks)
        return (False, None)

    # --- Query helpers ----------------------------------------------------

    def get_mastered_and_current_keys(
        self, *, keyset_id: str
    ) -> Tuple[List[str], List[str]]:
        """Return (mastered_keys, current_keys) for a keyset.

        Mastered = all keys from earlier progressions (sorted, unique).
        Current  = keys in the requested keyset (sorted).
        """
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
        self._renumber()

        # Validate unique names (case-insensitive)
        names: set[str] = set()
        for ks in self._keysets.values():
            if ks.keyset_name.lower() in names:
                raise KeysetValidationError("Duplicate keyset name in collection")
            names.add(ks.keyset_name.lower())

        # Validate progressive uniqueness for new keys
        ordered = self.get_keysets_ordered()

        # Persist promote/demote swaps atomically to avoid
        # UNIQUE(keyboard_id, progression_order) collisions.
        self._persist_atomic_swap_if_needed(ordered=ordered, updated_by=updated_by)

        for idx, ks in enumerate(ordered):
            earlier_keys = {
                k.key_char for prior in ordered[:idx] for k in prior.keys
            }
            for key in ks.keys:
                if key.is_new_key and key.key_char in earlier_keys:
                    raise KeysetValidationError(
                        f"Key '{key.key_char}' already exists in earlier progression"
                    )

        # Persist all keysets
        for ks in ordered:
            self._repo.save(ks, updated_by=updated_by)
            ks.in_db = True
            ks.is_dirty = False

        # Persist deletions
        for keyset_id in list(self._deleted_ids):
            self._repo.delete(keyset_id, deleted_by=updated_by)
            self._deleted_ids.discard(keyset_id)

        self.is_dirty = False

    def _persist_atomic_swap_if_needed(self, *, ordered: List[Keyset], updated_by: str) -> None:
        """Persist a simple two-keyset progression swap using repository atomic swap."""
        dirty_existing = [ks for ks in ordered if ks.is_dirty and ks.in_db]
        if len(dirty_existing) != 2:
            return

        first, second = dirty_existing
        persisted_first = self._repo.get_by_id(str(first.keyset_id))
        persisted_second = self._repo.get_by_id(str(second.keyset_id))
        if not persisted_first or not persisted_second:
            return

        is_order_swap = (
            persisted_first.progression_order == second.progression_order
            and persisted_second.progression_order == first.progression_order
        )
        if not is_order_swap:
            return

        self._repo.swap_progression_order(first, second, updated_by=updated_by)
