"""GraphQL resolvers for Keyset domain using dependency injection.

Resolvers delegate to use cases (business logic layer) and never access
repositories directly. This maintains Clean Architecture boundaries.
"""

from typing import Optional

import strawberry

from api.graphql.types import (
    CreateKeysetInput,
    DeleteKeysetResult,
    KeyProgressionInfo,
    KeysetMutationResult,
    KeysetType,
    PromoteKeysetResult,
    UpdateKeysetInput,
)
from entities.keyset import Keyset
from use_cases.keyset_collection import KeysetCollection, KeysetValidationError


@strawberry.type
class Query:
    """GraphQL queries for Keyset domain."""

    @strawberry.field
    def list_keysets_for_keyboard(
        self, keyboard_id: strawberry.ID, info: strawberry.Info
    ) -> list[KeysetType]:
        """List all keysets for a keyboard ordered by progression."""
        collection: KeysetCollection = info.context["keyset_collection"]
        keysets = collection.list_for_keyboard(keyboard_id=str(keyboard_id))
        return [KeysetType.from_entity(k) for k in keysets]

    @strawberry.field
    def get_keyset(self, keyset_id: strawberry.ID, info: strawberry.Info) -> Optional[KeysetType]:
        """Get a single keyset by ID."""
        collection: KeysetCollection = info.context["keyset_collection"]
        keyset = collection.get_by_id(keyset_id=str(keyset_id))
        return KeysetType.from_entity(keyset) if keyset else None

    @strawberry.field
    def get_key_progression_info(
        self, keyboard_id: strawberry.ID, progression_order: int, info: strawberry.Info
    ) -> KeyProgressionInfo:
        """Get mastered and current keys for a progression level."""
        collection: KeysetCollection = info.context["keyset_collection"]
        # Find keyset by keyboard_id and progression_order
        keysets = collection.list_for_keyboard(keyboard_id=str(keyboard_id))
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
            keyboard_id=str(keyboard_id), keyset_id=str(target_keyset.keyset_id)
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

            # Convert input to entity
            keys = [k.to_entity() for k in input.keys]
            keyset = Keyset(
                keyboard_id=str(input.keyboard_id),
                keyset_name=input.keyset_name,
                progression_order=input.progression_order,
                keys=keys,
            )

            # Add to collection
            collection.add_keyset(keyset=keyset, updated_by=str(updated_by))

            return KeysetMutationResult(success=True, keyset=KeysetType.from_entity(keyset))
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

            # Get existing keyset
            keyset = collection.get_by_id(keyset_id=str(input.keyset_id))
            if not keyset:
                return KeysetMutationResult(
                    success=False, error=f"Keyset {input.keyset_id} not found"
                )

            # Apply updates
            if input.keyset_name is not None:
                keyset.keyset_name = input.keyset_name
            if input.progression_order is not None:
                keyset.progression_order = input.progression_order
            if input.keys is not None:
                keyset.keys = [k.to_entity() for k in input.keys]

            # Update in collection
            collection.update_keyset(keyset=keyset, updated_by=str(updated_by))

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
            success = collection.delete_keyset(keyset_id=str(keyset_id), deleted_by=str(deleted_by))

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

            # Get keyset to find keyboard_id
            keyset = collection.get_by_id(keyset_id=str(keyset_id))
            if not keyset:
                return PromoteKeysetResult(success=False, error=f"Keyset {keyset_id} not found")

            success, swapped = collection.promote_keyset(
                keyboard_id=str(keyset.keyboard_id),
                keyset_id=str(keyset_id),
                updated_by=str(updated_by),
            )

            if not success:
                return PromoteKeysetResult(
                    success=False, error=f"Cannot promote keyset {keyset_id}"
                )

            # Get updated promoted keyset
            promoted = collection.get_by_id(keyset_id=str(keyset_id))

            return PromoteKeysetResult(
                success=True,
                promoted_keyset=KeysetType.from_entity(promoted) if promoted else None,
                swapped_keyset=KeysetType.from_entity(swapped) if swapped else None,
            )
        except ValueError as e:
            return PromoteKeysetResult(success=False, error=str(e))
        except Exception as e:
            return PromoteKeysetResult(success=False, error=f"Unexpected error: {e}")


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
