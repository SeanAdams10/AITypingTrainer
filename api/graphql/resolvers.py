"""GraphQL resolvers for Keyset domain using dependency injection.

Resolvers delegate to use cases (business logic layer) and never access
repositories directly. This maintains Clean Architecture boundaries.
"""

from typing import Optional

import strawberry

from api.graphql.types import (
    CreateKeysetInput,
    DeleteKeysetResult,
    InsertKeysetBeforeInput,
    KeyProgressionInfo,
    KeysetMutationResult,
    KeysetType,
    MasteredAndCurrentKeys,
    PromoteKeysetResult,
    UpdateKeysetInput,
)
from repositories.keyset_protocols import IKeysetRepository
from use_cases.keyset_collection import KeysetCollection, KeysetValidationError


def _load_for_keyset_id(*, keyset_id: strawberry.ID, info: strawberry.Info) -> Optional[object]:
    """Load collection for keyset keyboard and return tracked keyset entity."""
    collection: KeysetCollection = info.context["keyset_collection"]
    repository: IKeysetRepository = info.context["repository"]
    persisted = repository.get_by_id(str(keyset_id))
    if not persisted:
        return None
    collection.load_for_keyboard(keyboard_id=str(persisted.keyboard_id))
    return collection.get_keyset(keyset_id=str(keyset_id))


@strawberry.type
class Query:
    """GraphQL queries for Keyset domain."""

    @strawberry.field
    def list_keysets_for_keyboard(
        self, keyboard_id: strawberry.ID, info: strawberry.Info
    ) -> list[KeysetType]:
        """List all keysets for a keyboard ordered by progression."""
        collection: KeysetCollection = info.context["keyset_collection"]
        collection.load_for_keyboard(keyboard_id=str(keyboard_id))
        keysets = collection.get_keysets_ordered()
        return [KeysetType.from_entity(k) for k in keysets]

    @strawberry.field
    def get_keyset(self, keyset_id: strawberry.ID, info: strawberry.Info) -> Optional[KeysetType]:
        """Get a single keyset by ID."""
        repository: IKeysetRepository = info.context["repository"]
        keyset = repository.get_by_id(str(keyset_id))
        return KeysetType.from_entity(keyset) if keyset else None

    @strawberry.field
    def get_mastered_and_current_keys(
        self, keyset_id: strawberry.ID, info: strawberry.Info
    ) -> MasteredAndCurrentKeys:
        """Return mastered/current keys for a keyset ID."""
        collection: KeysetCollection = info.context["keyset_collection"]
        repository: IKeysetRepository = info.context["repository"]

        keyset = repository.get_by_id(str(keyset_id))
        if not keyset:
            return MasteredAndCurrentKeys(mastered_keys=[], current_keys=[])

        collection.load_for_keyboard(keyboard_id=str(keyset.keyboard_id))
        mastered, current = collection.get_mastered_and_current_keys(keyset_id=str(keyset_id))
        return MasteredAndCurrentKeys(mastered_keys=sorted(mastered), current_keys=sorted(current))

    @strawberry.field
    def get_key_progression_info(
        self, keyboard_id: strawberry.ID, progression_order: int, info: strawberry.Info
    ) -> KeyProgressionInfo:
        """Get mastered and current keys for a progression level."""
        collection: KeysetCollection = info.context["keyset_collection"]
        collection.load_for_keyboard(keyboard_id=str(keyboard_id))
        # Find keyset by progression_order
        keysets = collection.get_keysets_ordered()
        target_keyset = None
        for ks in keysets:
            if ks.progression_order == progression_order:
                target_keyset = ks
                break

        if not target_keyset:
            return KeyProgressionInfo(
                mastered_keys=[],
                current_keys=[],
                total_mastered_count=0,
                total_current_count=0,
            )

        mastered, current = collection.get_mastered_and_current_keys(
            keyset_id=str(target_keyset.keyset_id)
        )
        return KeyProgressionInfo(
            mastered_keys=sorted(mastered),
            current_keys=sorted(current),
            total_mastered_count=len(mastered),
            total_current_count=len(current),
        )


@strawberry.type
class Mutation:
    """GraphQL mutations for Keyset domain."""

    @strawberry.mutation
    def create_keyset(
        self,
        input: CreateKeysetInput,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> KeysetMutationResult:
        """Create a new keyset with keys.

        Args:
            input: The keyset creation input
            info: Strawberry context info
            updated_by: User ID for audit trail (required, must be valid UUID)
        """
        try:
            collection: KeysetCollection = info.context["keyset_collection"]

            # Add to collection using the clean API
            collection.load_for_keyboard(keyboard_id=str(input.keyboard_id))
            key_chars = [k.key_char for k in input.keys]
            new_keyset = collection.add_keyset(
                keyset_name=input.keyset_name,
                keys=key_chars,
            )
            collection.save_all(updated_by=str(updated_by))

            return KeysetMutationResult(
                success=True, keyset=KeysetType.from_entity(new_keyset)
            )
        except (ValueError, KeysetValidationError) as e:
            return KeysetMutationResult(success=False, error=str(e))
        except Exception as e:
            return KeysetMutationResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def update_keyset(
        self,
        input: UpdateKeysetInput,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> KeysetMutationResult:
        """Update an existing keyset.

        Args:
            input: The keyset update input
            info: Strawberry context info
            updated_by: User ID for audit trail (required, must be valid UUID)
        """
        try:
            collection: KeysetCollection = info.context["keyset_collection"]

            keyset = _load_for_keyset_id(keyset_id=input.keyset_id, info=info)
            if not keyset:
                return KeysetMutationResult(
                    success=False, error=f"Keyset {input.keyset_id} not found"
                )

            # Apply updates in-place on the tracked entity
            if input.keyset_name is not None:
                keyset.keyset_name = input.keyset_name
            if input.progression_order is not None:
                keyset.progression_order = input.progression_order
            if input.keys is not None:
                keyset.keys = [k.to_entity() for k in input.keys]
            keyset.is_dirty = True
            collection.is_dirty = True

            collection.save_all(updated_by=str(updated_by))

            return KeysetMutationResult(success=True, keyset=KeysetType.from_entity(keyset))
        except (ValueError, KeysetValidationError) as e:
            return KeysetMutationResult(success=False, error=str(e))
        except Exception as e:
            return KeysetMutationResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def delete_keyset(
        self,
        keyset_id: strawberry.ID,
        info: strawberry.Info,
        deleted_by: strawberry.ID,
    ) -> DeleteKeysetResult:
        """Delete a keyset.

        Args:
            keyset_id: The keyset UUID to delete
            info: Strawberry context info
            deleted_by: User ID for audit trail (required, must be valid UUID)
        """
        try:
            collection: KeysetCollection = info.context["keyset_collection"]
            keyset = _load_for_keyset_id(keyset_id=keyset_id, info=info)
            if not keyset:
                return DeleteKeysetResult(success=False, error=f"Keyset {keyset_id} not found")

            success = collection.delete_keyset(keyset_id=str(keyset_id))
            if success:
                collection.save_all(updated_by=str(deleted_by))

            if not success:
                return DeleteKeysetResult(success=False, error=f"Keyset {keyset_id} not found")

            return DeleteKeysetResult(success=True)
        except Exception as e:
            return DeleteKeysetResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def promote_keyset(
        self,
        keyset_id: strawberry.ID,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> PromoteKeysetResult:
        """Promote a keyset by swapping progression order with previous.

        Args:
            keyset_id: The keyset UUID to promote
            info: Strawberry context info
            updated_by: User ID for audit trail (required, must be valid UUID)
        """
        try:
            collection: KeysetCollection = info.context["keyset_collection"]

            keyset = _load_for_keyset_id(keyset_id=keyset_id, info=info)
            if not keyset:
                return PromoteKeysetResult(success=False, error=f"Keyset {keyset_id} not found")
            success, swapped = collection.promote_keyset(keyset_id=str(keyset_id))

            if not success:
                return PromoteKeysetResult(
                    success=False, error=f"Cannot promote keyset {keyset_id}"
                )

            # Get updated promoted keyset
            promoted = collection.get_keyset(keyset_id=str(keyset_id))
            collection.save_all(updated_by=str(updated_by))

            return PromoteKeysetResult(
                success=True,
                promoted_keyset=KeysetType.from_entity(promoted) if promoted else None,
                swapped_keyset=KeysetType.from_entity(swapped) if swapped else None,
            )
        except ValueError as e:
            return PromoteKeysetResult(success=False, error=str(e))
        except Exception as e:
            return PromoteKeysetResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def demote_keyset(
        self,
        keyset_id: strawberry.ID,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> PromoteKeysetResult:
        """Demote a keyset by swapping progression order with next."""
        try:
            collection: KeysetCollection = info.context["keyset_collection"]
            keyset = _load_for_keyset_id(keyset_id=keyset_id, info=info)
            if not keyset:
                return PromoteKeysetResult(success=False, error=f"Keyset {keyset_id} not found")

            success, swapped = collection.demote_keyset(keyset_id=str(keyset_id))
            if not success:
                return PromoteKeysetResult(success=False, error=f"Cannot demote keyset {keyset_id}")

            promoted = collection.get_keyset(keyset_id=str(keyset_id))
            collection.save_all(updated_by=str(updated_by))

            return PromoteKeysetResult(
                success=True,
                promoted_keyset=KeysetType.from_entity(promoted) if promoted else None,
                swapped_keyset=KeysetType.from_entity(swapped) if swapped else None,
            )
        except ValueError as e:
            return PromoteKeysetResult(success=False, error=str(e))
        except Exception as e:
            return PromoteKeysetResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def rename_keyset(
        self,
        keyset_id: strawberry.ID,
        new_name: str,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> KeysetMutationResult:
        """Rename an existing keyset."""
        try:
            collection: KeysetCollection = info.context["keyset_collection"]
            keyset = _load_for_keyset_id(keyset_id=keyset_id, info=info)
            if not keyset:
                return KeysetMutationResult(success=False, error=f"Keyset {keyset_id} not found")

            success = collection.rename_keyset(keyset_id=str(keyset_id), new_name=new_name)
            if not success:
                return KeysetMutationResult(success=False, error=f"Keyset {keyset_id} not found")

            collection.save_all(updated_by=str(updated_by))
            updated = collection.get_keyset(keyset_id=str(keyset_id))
            return KeysetMutationResult(
                success=True,
                keyset=KeysetType.from_entity(updated) if updated else None,
            )
        except (ValueError, KeysetValidationError) as e:
            return KeysetMutationResult(success=False, error=str(e))
        except Exception as e:
            return KeysetMutationResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def add_key_to_keyset(
        self,
        keyset_id: strawberry.ID,
        key_char: str,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> KeysetMutationResult:
        """Add a key to a keyset."""
        try:
            collection: KeysetCollection = info.context["keyset_collection"]
            keyset = _load_for_keyset_id(keyset_id=keyset_id, info=info)
            if not keyset:
                return KeysetMutationResult(success=False, error=f"Keyset {keyset_id} not found")

            collection.add_key_to_keyset(keyset_id=str(keyset_id), key_char=key_char)
            collection.save_all(updated_by=str(updated_by))
            updated = collection.get_keyset(keyset_id=str(keyset_id))
            return KeysetMutationResult(
                success=True,
                keyset=KeysetType.from_entity(updated) if updated else None,
            )
        except (ValueError, KeysetValidationError) as e:
            return KeysetMutationResult(success=False, error=str(e))
        except Exception as e:
            return KeysetMutationResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def remove_key_from_keyset(
        self,
        keyset_id: strawberry.ID,
        key_char: str,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> KeysetMutationResult:
        """Remove a key from a keyset."""
        try:
            collection: KeysetCollection = info.context["keyset_collection"]
            keyset = _load_for_keyset_id(keyset_id=keyset_id, info=info)
            if not keyset:
                return KeysetMutationResult(success=False, error=f"Keyset {keyset_id} not found")

            removed = collection.remove_key_from_keyset(keyset_id=str(keyset_id), key_char=key_char)
            if not removed:
                return KeysetMutationResult(
                    success=False,
                    error=f"Key '{key_char}' not found in keyset {keyset_id}",
                )

            collection.save_all(updated_by=str(updated_by))
            updated = collection.get_keyset(keyset_id=str(keyset_id))
            return KeysetMutationResult(
                success=True,
                keyset=KeysetType.from_entity(updated) if updated else None,
            )
        except (ValueError, KeysetValidationError) as e:
            return KeysetMutationResult(success=False, error=str(e))
        except Exception as e:
            return KeysetMutationResult(success=False, error=f"Unexpected error: {e}")

    @strawberry.mutation
    def insert_keyset_before(
        self,
        input: InsertKeysetBeforeInput,
        info: strawberry.Info,
        updated_by: strawberry.ID,
    ) -> KeysetMutationResult:
        """Insert a keyset before another keyset (or append if before keyset absent)."""
        try:
            collection: KeysetCollection = info.context["keyset_collection"]
            collection.load_for_keyboard(keyboard_id=str(input.keyboard_id))

            new_keyset = collection.insert_keyset_before(
                keyset_name=input.keyset_name,
                before_keyset_id=str(input.before_keyset_id) if input.before_keyset_id else None,
                keys=list(input.keys) if input.keys else [],
            )
            collection.save_all(updated_by=str(updated_by))

            return KeysetMutationResult(success=True, keyset=KeysetType.from_entity(new_keyset))
        except (ValueError, KeysetValidationError) as e:
            return KeysetMutationResult(success=False, error=str(e))
        except Exception as e:
            return KeysetMutationResult(success=False, error=f"Unexpected error: {e}")


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
