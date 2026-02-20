"""Strawberry GraphQL types for Keyset domain.

Maps Clean Architecture entities to GraphQL schema types.
All types are immutable and validation-free (validation happens in use cases).
"""

from typing import TYPE_CHECKING, Optional

import strawberry

if TYPE_CHECKING:
    from entities.keyset import Keyset
    from entities.keyset_key import KeysetKey


@strawberry.type
class KeysetKeyType:
    """GraphQL type for individual key in a keyset."""

    key_id: strawberry.ID
    key_char: str
    is_new_key: bool

    @staticmethod
    def from_entity(key: "KeysetKey") -> "KeysetKeyType":
        """Convert entity to GraphQL type."""
        return KeysetKeyType(
            key_id=strawberry.ID(str(key.key_id)),
            key_char=key.key_char,
            is_new_key=key.is_new_key,
        )


@strawberry.type
class KeysetType:
    """GraphQL type for keyset with progression tracking."""

    keyset_id: strawberry.ID
    keyboard_id: strawberry.ID
    keyset_name: str
    progression_order: int
    keys: list[KeysetKeyType]
    is_dirty: bool

    @staticmethod
    def from_entity(keyset: "Keyset") -> "KeysetType":
        """Convert entity to GraphQL type."""
        return KeysetType(
            keyset_id=strawberry.ID(str(keyset.keyset_id)),
            keyboard_id=strawberry.ID(str(keyset.keyboard_id)),
            keyset_name=keyset.keyset_name,
            progression_order=keyset.progression_order,
            keys=[KeysetKeyType.from_entity(k) for k in keyset.keys],
            is_dirty=keyset.is_dirty,
        )


@strawberry.input
class KeysetKeyInput:
    """Input type for creating/updating keys."""

    key_char: str
    is_new_key: bool
    key_id: Optional[strawberry.ID] = None

    def to_entity(self) -> "KeysetKey":
        """Convert input to entity."""
        from entities.keyset_key import KeysetKey

        if self.key_id:
            return KeysetKey(
                key_id=str(self.key_id),
                key_char=self.key_char,
                is_new_key=self.is_new_key,
            )
        return KeysetKey(key_char=self.key_char, is_new_key=self.is_new_key)


@strawberry.input
class CreateKeysetInput:
    """Input type for creating a new keyset."""

    keyboard_id: strawberry.ID
    keyset_name: str
    keys: list[KeysetKeyInput]


@strawberry.input
class InsertKeysetBeforeInput:
    """Input type for inserting a keyset before an existing one."""

    keyboard_id: strawberry.ID
    keyset_name: str
    before_keyset_id: Optional[strawberry.ID] = None
    keys: Optional[list[str]] = None


@strawberry.input
class UpdateKeysetInput:
    """Input type for updating an existing keyset."""

    keyset_id: strawberry.ID
    keyset_name: Optional[str] = None
    progression_order: Optional[int] = None
    keys: Optional[list[KeysetKeyInput]] = None


@strawberry.type
class MutationResult:
    """Standard result type for keyset mutations (per spec Section 8.2)."""

    success: bool
    keyset: Optional[KeysetType] = None
    error: Optional[str] = None


# Alias for backward compatibility
KeysetMutationResult = MutationResult


@strawberry.type
class DeleteKeysetResult:
    """Result type for delete mutations."""

    success: bool
    error: Optional[str] = None


@strawberry.type
class PromoteKeysetResult:
    """Result type for promotion (swap progression order)."""

    success: bool
    promoted_keyset: Optional[KeysetType] = None
    swapped_keyset: Optional[KeysetType] = None
    error: Optional[str] = None


@strawberry.type
class MasteredAndCurrentKeys:
    """Result type for getMasteredAndCurrentKeys query (per spec Section 8.2)."""

    mastered_keys: list[str]
    current_keys: list[str]


@strawberry.type
class KeyProgressionInfo:
    """Information about key progression across keysets."""

    mastered_keys: list[str]
    current_keys: list[str]
    total_mastered_count: int
    total_current_count: int
