"""PostgreSQL implementation of IKeysetRepository using raw SQL with SCD-2 history.

This repository implements Slowly Changing Dimension Type 2 (SCD-2) for full audit history:
- valid_from_dt: Timestamp when this version became active
- valid_to_dt: Timestamp when superseded (default '9999-12-31 23:59:59' for current)
- is_current: Boolean flag for active version (1=current, 0=historical)
- version_no: Monotonically increasing version number
- row_checksum: SHA256 hash for no-op detection (skip if unchanged)
- action: INSERT/UPDATE/DELETE for audit trail

Schema tables:
- keyset: Current keyset data (keyset_id, keyboard_id, keyset_name, progression_order)
- keyset_history: Full SCD-2 audit trail
- keyset_keys: Current keys (key_id, keyset_id, key_char, is_new_key)
- keyset_keys_history: Full SCD-2 audit trail for keys

Note: Uses raw SQL strings with DatabaseManager (not SQLAlchemy query builder).
"""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional

from db.database_manager import DatabaseManager
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_protocols import IKeysetRepository


class PostgresKeysetRepository(IKeysetRepository):
    """PostgreSQL implementation with SCD-2 history tracking using raw SQL."""

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize with DatabaseManager for connection pooling."""
        self._db = db

    def _compute_keyset_checksum(self, keyset: Keyset) -> bytes:
        """Compute SHA256 checksum for no-op detection."""
        content = f"{keyset.keyboard_id}|{keyset.keyset_name}|{keyset.progression_order}"
        return sha256(content.encode("utf-8")).digest()

    def _compute_key_checksum(self, key: KeysetKey) -> bytes:
        """Compute SHA256 checksum for key."""
        content = f"{key.key_char}|{int(key.is_new_key)}"
        return sha256(content.encode("utf-8")).digest()

    def _now_iso(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def list_for_keyboard(self, keyboard_id: str) -> list[Keyset]:
        """List all keysets for a keyboard ordered by progression."""
        query = """
            SELECT keyset_id, keyboard_id, keyset_name, progression_order
            FROM keyset
            WHERE keyboard_id = %s
            ORDER BY progression_order
        """
        rows = self._db.fetchall(query=query, params=(keyboard_id,))
        keysets = []

        for row in rows:
            # Fetch keys for this keyset
            keys_query = """
                SELECT key_id, key_char, is_new_key
                FROM keyset_keys
                WHERE keyset_id = %s
                ORDER BY key_char
            """
            key_rows = self._db.fetchall(query=keys_query, params=(row["keyset_id"],))

            keys = [
                KeysetKey(
                    key_id=str(k["key_id"]),
                    key_char=str(k["key_char"]),
                    is_new_key=bool(k["is_new_key"]),
                )
                for k in key_rows
            ]

            keyset = Keyset(
                keyset_id=str(row["keyset_id"]),
                keyboard_id=str(row["keyboard_id"]),
                keyset_name=str(row["keyset_name"]),
                progression_order=int(str(row["progression_order"])),
                keys=keys,
            )
            keysets.append(keyset)

        return keysets

    def get_by_id(self, keyset_id: str) -> Optional[Keyset]:
        """Get a keyset by ID with all keys."""
        query = """
            SELECT keyset_id, keyboard_id, keyset_name, progression_order
            FROM keyset
            WHERE keyset_id = %s
        """
        row = self._db.fetchone(query=query, params=(keyset_id,))
        if not row:
            return None

        # Fetch keys
        keys_query = """
            SELECT key_id, key_char, is_new_key
            FROM keyset_keys
            WHERE keyset_id = %s
            ORDER BY key_char
        """
        key_rows = self._db.fetchall(query=keys_query, params=(keyset_id,))

        keys = [
            KeysetKey(
                key_id=str(k["key_id"]),
                key_char=str(k["key_char"]),
                is_new_key=bool(k["is_new_key"]),
            )
            for k in key_rows
        ]

        return Keyset(
            keyset_id=str(row["keyset_id"]),
            keyboard_id=str(row["keyboard_id"]),
            keyset_name=str(row["keyset_name"]),
            progression_order=int(str(row["progression_order"])),
            keys=keys,
        )

    def save(self, keyset: Keyset, *, updated_by: Optional[str] = None) -> None:
        """Save keyset with SCD-2 history tracking."""
        # Check if exists
        existing = self.get_by_id(str(keyset.keyset_id))
        now = self._now_iso()
        user_id = str(updated_by) if updated_by else "system"

        if existing is None:
            # INSERT new keyset
            checksum = self._compute_keyset_checksum(keyset)

            # Insert main keyset record
            insert_query = """
                INSERT INTO keyset (keyset_id, keyboard_id, keyset_name, progression_order,
                                   row_checksum, created_dt, updated_dt, created_user_id, updated_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self._db.execute(
                query=insert_query,
                params=(
                    str(keyset.keyset_id),
                    str(keyset.keyboard_id),
                    keyset.keyset_name,
                    keyset.progression_order,
                    checksum,
                    now,
                    now,
                    user_id,
                    user_id,
                ),
            )

            # Insert history record
            history_query = """
                INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order,
                                           row_checksum, created_dt, updated_dt, created_user_id, updated_user_id,
                                           action, valid_from_dt, valid_to_dt, is_current, version_no)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self._db.execute(
                query=history_query,
                params=(
                    str(keyset.keyset_id),
                    str(keyset.keyboard_id),
                    keyset.keyset_name,
                    keyset.progression_order,
                    checksum,
                    now,
                    now,
                    user_id,
                    user_id,
                    "INSERT",
                    now,
                    "9999-12-31 23:59:59",
                    1,
                    1,
                ),
            )

            # Insert keys
            for key in keyset.keys:
                self._insert_key(key, str(keyset.keyset_id), now, user_id)

        else:
            # UPDATE existing keyset
            checksum = self._compute_keyset_checksum(keyset)
            old_checksum_query = """
                SELECT row_checksum FROM keyset WHERE keyset_id = %s
            """
            old_row = self._db.fetchone(query=old_checksum_query, params=(str(keyset.keyset_id),))

            # No-op detection
            old_checksum = old_row["row_checksum"] if old_row else None
            # Handle memoryview from PostgreSQL
            if isinstance(old_checksum, memoryview):
                old_checksum = bytes(old_checksum)
            if old_checksum == checksum:
                # Checksum match, but still need to check keys
                keys_changed = self._keys_changed(keyset, existing)
                if not keys_changed:
                    return  # Complete no-op

            # Close old history version
            close_query = """
                UPDATE keyset_history
                SET valid_to_dt = %s, is_current = 0
                WHERE keyset_id = %s AND is_current = 1
            """
            self._db.execute(query=close_query, params=(now, str(keyset.keyset_id)))

            # Get next version number
            version_query = """
                SELECT version_no FROM keyset_history
                WHERE keyset_id = %s
                ORDER BY version_no DESC
                LIMIT 1
            """
            version_row = self._db.fetchone(query=version_query, params=(str(keyset.keyset_id),))
            next_version = (int(str(version_row["version_no"])) + 1) if version_row else 1

            # Update main keyset record
            update_query = """
                UPDATE keyset
                SET keyset_name = %s, progression_order = %s, row_checksum = %s, 
                    updated_dt = %s, updated_user_id = %s
                WHERE keyset_id = %s
            """
            self._db.execute(
                query=update_query,
                params=(
                    keyset.keyset_name,
                    keyset.progression_order,
                    checksum,
                    now,
                    user_id,
                    str(keyset.keyset_id),
                ),
            )

            # Insert new history record
            history_query = """
                INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order,
                                           row_checksum, created_dt, updated_dt, created_user_id, updated_user_id,
                                           action, valid_from_dt, valid_to_dt, is_current, version_no)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self._db.execute(
                query=history_query,
                params=(
                    str(keyset.keyset_id),
                    str(keyset.keyboard_id),
                    keyset.keyset_name,
                    keyset.progression_order,
                    checksum,
                    now,
                    now,
                    user_id,
                    user_id,
                    "UPDATE",
                    now,
                    "9999-12-31 23:59:59",
                    1,
                    next_version,
                ),
            )

            # Update keys (delete old, insert new)
            self._sync_keys(keyset, now, user_id)

    def _keys_changed(self, new_keyset: Keyset, old_keyset: Keyset) -> bool:
        """Check if keys have changed."""
        if len(new_keyset.keys) != len(old_keyset.keys):
            return True

        new_keys_set = {(k.key_char, k.is_new_key) for k in new_keyset.keys}
        old_keys_set = {(k.key_char, k.is_new_key) for k in old_keyset.keys}

        return new_keys_set != old_keys_set

    def _insert_key(self, key: KeysetKey, keyset_id: str, now: str, user_id: str) -> None:
        """Insert a single key with history."""
        checksum = self._compute_key_checksum(key)

        # Insert main key record
        insert_query = """
            INSERT INTO keyset_keys (key_id, keyset_id, key_char, is_new_key, row_checksum,
                                    created_dt, updated_dt, created_user_id, updated_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self._db.execute(
            query=insert_query,
            params=(
                str(key.key_id),
                keyset_id,
                key.key_char,
                int(key.is_new_key),
                checksum,
                now,
                now,
                user_id,
                user_id,
            ),
        )

        # Insert history record
        history_query = """
            INSERT INTO keyset_keys_history (key_id, keyset_id, key_char, is_new_key, row_checksum,
                                            created_dt, updated_dt, created_user_id, updated_user_id,
                                            action, valid_from_dt, valid_to_dt, is_current, version_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self._db.execute(
            query=history_query,
            params=(
                str(key.key_id),
                keyset_id,
                key.key_char,
                int(key.is_new_key),
                checksum,
                now,
                now,
                user_id,
                user_id,
                "INSERT",
                now,
                "9999-12-31 23:59:59",
                1,
                1,
            ),
        )

    def _sync_keys(self, keyset: Keyset, now: str, user_id: str) -> None:
        """Sync keys: delete old, insert new."""
        # Delete old keys
        delete_query = "DELETE FROM keyset_keys WHERE keyset_id = %s"
        self._db.execute(query=delete_query, params=(str(keyset.keyset_id),))

        # Insert new keys
        for key in keyset.keys:
            self._insert_key(key, str(keyset.keyset_id), now, user_id)

    def delete(self, keyset_id: str, *, deleted_by: Optional[str] = None) -> bool:
        """Soft delete by closing history records."""
        existing = self.get_by_id(keyset_id)
        if not existing:
            return False

        now = self._now_iso()
        user_id = str(deleted_by) if deleted_by else "system"

        # Close keyset history
        close_query = """
            UPDATE keyset_history
            SET valid_to_dt = %s, is_current = 0
            WHERE keyset_id = %s AND is_current = 1
        """
        self._db.execute(query=close_query, params=(now, keyset_id))

        # Get next version
        next_version = self._get_next_version(keyset_id)

        # Insert DELETE history record
        history_query = """
            INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order,
                                       row_checksum, created_dt, updated_dt, created_user_id, updated_user_id,
                                       action, valid_from_dt, valid_to_dt, is_current, version_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self._db.execute(
            query=history_query,
            params=(
                keyset_id,
                str(existing.keyboard_id),
                existing.keyset_name,
                existing.progression_order,
                self._compute_keyset_checksum(existing),
                now,
                now,
                user_id,
                user_id,
                "DELETE",
                now,
                "9999-12-31 23:59:59",
                1,
                next_version,
            ),
        )

        # Hard delete from main tables (CASCADE will handle keys)
        delete_query = "DELETE FROM keyset WHERE keyset_id = %s"
        self._db.execute(query=delete_query, params=(keyset_id,))

        return True

    def _get_next_version(self, keyset_id: str) -> int:
        """Get next version number for history."""
        query = """
            SELECT version_no FROM keyset_history
            WHERE keyset_id = %s
            ORDER BY version_no DESC
            LIMIT 1
        """
        row = self._db.fetchone(query=query, params=(keyset_id,))
        return (int(str(row["version_no"])) + 1) if row else 1

    def validate_key_progression_uniqueness(
        self,
        *,
        keyboard_id: str,
        progression_order: int,
        keys: list[str],
        keyset_id: Optional[str] = None,
    ) -> None:
        """Validate that new keys don't exist in earlier progressions."""
        new_keys = set(keys)

        # Query all earlier progressions
        query = """
            SELECT keyset_id FROM keyset
            WHERE keyboard_id = %s AND progression_order < %s
        """
        rows = self._db.fetchall(query=query, params=(keyboard_id, progression_order))

        # Collect all keys from earlier progressions
        earlier_keys: set[str] = set()
        for row in rows:
            keys_query = "SELECT key_char FROM keyset_keys WHERE keyset_id = %s"
            key_rows = self._db.fetchall(query=keys_query, params=(row["keyset_id"],))
            earlier_keys.update(str(k["key_char"]) for k in key_rows)

        # Find violations
        violations = sorted(new_keys & earlier_keys)
        if violations:
            raise ValueError(
                f"Keys {violations} already exist in earlier progressions for keyboard {keyboard_id}"
            )

    def swap_progression_order(
        self,
        keyset1: Keyset,
        keyset2: Keyset,
        *,
        updated_by: Optional[str] = None,
    ) -> None:
        """Atomically swap the progression_order of two keysets.

        Uses a three-step approach with a temporary negative value to avoid 
        unique constraint violation on (keyboard_id, progression_order):
        1. Set keyset1 to temporary value (-1)
        2. Set keyset2 to keyset1's new value
        3. Set keyset1 from temporary to its new value

        Args:
            keyset1: First keyset (with updated progression_order already set)
            keyset2: Second keyset (with updated progression_order already set)
            updated_by: User ID performing the operation (for audit trail)

        Raises:
            ValueError: If keysets belong to different keyboards
        """
        if keyset1.keyboard_id != keyset2.keyboard_id:
            raise ValueError("Cannot swap progression order between different keyboards")

        now = self._now_iso()
        user_id = updated_by or "system"

        # Compute new checksums
        checksum1 = self._compute_keyset_checksum(keyset1)
        checksum2 = self._compute_keyset_checksum(keyset2)

        # Step 1: Set keyset1 to temporary value (-1) to free up the slot
        temp_query = """
            UPDATE keyset
            SET progression_order = -1, updated_dt = %s, updated_user_id = %s
            WHERE keyset_id = %s
        """
        self._db.execute(
            query=temp_query,
            params=(now, user_id, str(keyset1.keyset_id)),
        )

        # Step 2: Set keyset2 to its new value (keyset1's original slot is now free)
        update2_query = """
            UPDATE keyset
            SET progression_order = %s, updated_dt = %s, updated_user_id = %s, row_checksum = %s
            WHERE keyset_id = %s
        """
        self._db.execute(
            query=update2_query,
            params=(keyset2.progression_order, now, user_id, checksum2, str(keyset2.keyset_id)),
        )

        # Step 3: Set keyset1 to its new value
        update1_query = """
            UPDATE keyset
            SET progression_order = %s, updated_dt = %s, updated_user_id = %s, row_checksum = %s
            WHERE keyset_id = %s
        """
        self._db.execute(
            query=update1_query,
            params=(keyset1.progression_order, now, user_id, checksum1, str(keyset1.keyset_id)),
        )

        # Close old history versions and insert new ones for both keysets
        for keyset, checksum in [(keyset1, checksum1), (keyset2, checksum2)]:
            # Close old history
            close_query = """
                UPDATE keyset_history
                SET valid_to_dt = %s, is_current = 0
                WHERE keyset_id = %s AND is_current = 1
            """
            self._db.execute(query=close_query, params=(now, str(keyset.keyset_id)))

            # Get next version number
            next_version = self._get_next_version(str(keyset.keyset_id))

            # Insert new history record
            history_query = """
                INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order,
                                           row_checksum, created_dt, updated_dt, created_user_id, updated_user_id,
                                           action, valid_from_dt, valid_to_dt, is_current, version_no)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self._db.execute(
                query=history_query,
                params=(
                    str(keyset.keyset_id),
                    str(keyset.keyboard_id),
                    keyset.keyset_name,
                    keyset.progression_order,
                    checksum,
                    now,
                    now,
                    user_id,
                    user_id,
                    "UPDATE",
                    now,
                    "9999-12-31 23:59:59",
                    1,
                    next_version,
                ),
            )

        # Mark both as clean
        keyset1.is_dirty = False
        keyset2.is_dirty = False
