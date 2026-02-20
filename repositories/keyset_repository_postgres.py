"""PostgreSQL implementation of IKeysetRepository using raw SQL with SCD-2 history."""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional
from uuid import UUID

from db.database_manager import DatabaseManager
from db.exceptions import ConstraintError
from entities.keyset import Keyset
from entities.keyset_key import KeysetKey
from repositories.keyset_protocols import IKeysetRepository


class PostgresKeysetRepository(IKeysetRepository):
    """PostgreSQL implementation with SCD-2 history tracking using raw SQL."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _wrap_constraint_error(self, err: ConstraintError, keyset: Keyset) -> ValueError:
        message = str(err)
        if "keyset_keyboard_id_keyset_name_key" in message:
            return ValueError(
                f"Keyset name '{keyset.keyset_name}' already exists for keyboard {keyset.keyboard_id}"
            )
        if "keyset_keyboard_id_progression_order_key" in message:
            return ValueError(
                f"Progression order {keyset.progression_order} is already in use for keyboard {keyset.keyboard_id}"
            )
        return ValueError(f"Keyset save failed due to constraint violation: {message}")

    def _compute_keyset_checksum(self, keyset: Keyset) -> bytes:
        content = f"{keyset.keyboard_id}|{keyset.keyset_name}|{keyset.progression_order}"
        return sha256(content.encode("utf-8")).digest()

    def _compute_key_checksum(self, key: KeysetKey) -> bytes:
        content = f"{key.key_char}|{int(key.is_new_key)}"
        return sha256(content.encode("utf-8")).digest()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _mark_persisted(self, keyset: Keyset) -> None:
        keyset.in_db = True
        keyset.is_dirty = False
        for key in keyset.keys:
            key.in_db = True
            key.keyset_id = str(keyset.keyset_id)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def list_for_keyboard(self, keyboard_id: str) -> list[Keyset]:
        query = (
            "SELECT keyset_id, keyboard_id, keyset_name, progression_order "
            "FROM keyset WHERE keyboard_id = %s ORDER BY progression_order"
        )
        rows = self._db.fetchall(query=query, params=(keyboard_id,))
        keysets: list[Keyset] = []

        for row in rows:
            key_rows = self._db.fetchall(
                query=(
                    "SELECT key_id, key_char, is_new_key FROM keyset_keys "
                    "WHERE keyset_id = %s ORDER BY key_char"
                ),
                params=(row["keyset_id"],),
            )

            keys = [
                KeysetKey(
                    key_id=str(k["key_id"]),
                    key_char=str(k["key_char"]),
                    is_new_key=bool(k["is_new_key"]),
                    in_db=True,
                    keyset_id=str(row["keyset_id"]),
                )
                for k in key_rows
            ]

            keysets.append(
                Keyset(
                    keyset_id=str(row["keyset_id"]),
                    keyboard_id=str(row["keyboard_id"]),
                    keyset_name=str(row["keyset_name"]),
                    progression_order=int(str(row["progression_order"])),
                    keys=keys,
                    in_db=True,
                )
            )

        return keysets

    def get_by_id(self, keyset_id: str) -> Optional[Keyset]:
        row = self._db.fetchone(
            query=(
                "SELECT keyset_id, keyboard_id, keyset_name, progression_order "
                "FROM keyset WHERE keyset_id = %s"
            ),
            params=(keyset_id,),
        )
        if not row:
            return None

        key_rows = self._db.fetchall(
            query=(
                "SELECT key_id, key_char, is_new_key FROM keyset_keys "
                "WHERE keyset_id = %s ORDER BY key_char"
            ),
            params=(keyset_id,),
        )

        keys = [
            KeysetKey(
                key_id=str(k["key_id"]),
                key_char=str(k["key_char"]),
                is_new_key=bool(k["is_new_key"]),
                in_db=True,
                keyset_id=str(row["keyset_id"]),
            )
            for k in key_rows
        ]

        return Keyset(
            keyset_id=str(row["keyset_id"]),
            keyboard_id=str(row["keyboard_id"]),
            keyset_name=str(row["keyset_name"]),
            progression_order=int(str(row["progression_order"])),
            keys=keys,
            in_db=True,
        )

    def save(self, keyset: Keyset, *, updated_by: str) -> None:
        if not updated_by:
            raise ValueError("updated_by user ID is required for audit trail")
        try:
            UUID(updated_by)
        except ValueError as exc:
            raise ValueError(f"updated_by must be a valid UUID, got: {updated_by}") from exc

        new_keys = [k.key_char for k in keyset.keys if k.is_new_key]
        if new_keys:
            self.validate_key_progression_uniqueness(
                keyboard_id=keyset.keyboard_id,
                progression_order=keyset.progression_order,
                keys=new_keys,
                keyset_id=str(keyset.keyset_id),
            )

        existing = self.get_by_id(str(keyset.keyset_id))
        now = self._now_iso()

        try:
            if existing is None:
                self._insert_keyset(keyset, now, updated_by)
            else:
                self._update_keyset(keyset, existing, now, updated_by)
        except ConstraintError as err:
            raise self._wrap_constraint_error(err, keyset) from err

        self._mark_persisted(keyset)

    def delete(self, keyset_id: str, *, deleted_by: str) -> bool:
        if not deleted_by:
            raise ValueError("deleted_by user ID is required for audit trail")
        try:
            UUID(deleted_by)
        except ValueError as exc:
            raise ValueError(f"deleted_by must be a valid UUID, got: {deleted_by}") from exc

        existing = self.get_by_id(keyset_id)
        if not existing:
            return False

        now = self._now_iso()

        self._db.execute(
            query=(
                "UPDATE keyset_history SET valid_to_dt = %s, is_current = 0 "
                "WHERE keyset_id = %s AND is_current = 1"
            ),
            params=(now, keyset_id),
        )

        next_version = self._get_next_version(keyset_id)
        checksum = self._compute_keyset_checksum(existing)

        self._db.execute(
            query=(
                "INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order, "
                "row_checksum, created_dt, updated_dt, created_user_id, updated_user_id, action, "
                "valid_from_dt, valid_to_dt, is_current, version_no) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
            params=(
                str(existing.keyset_id),
                str(existing.keyboard_id),
                existing.keyset_name,
                existing.progression_order,
                checksum,
                now,
                now,
                deleted_by,
                deleted_by,
                "DELETE",
                now,
                "9999-12-31 23:59:59",
                1,
                next_version,
            ),
        )

        keys_rows = self._db.fetchall(
            query=(
                "SELECT key_id, key_char, is_new_key, row_checksum FROM keyset_keys WHERE keyset_id = %s"
            ),
            params=(keyset_id,),
        )

        for row in keys_rows:
            key_id = str(row["key_id"])
            self._db.execute(
                query=(
                    "UPDATE keyset_keys_history SET valid_to_dt = %s, is_current = 0 "
                    "WHERE key_id = %s AND is_current = 1"
                ),
                params=(now, key_id),
            )
            next_key_version = self._get_next_key_version(key_id)
            self._db.execute(
                query=(
                    "INSERT INTO keyset_keys_history (key_id, keyset_id, key_char, is_new_key, row_checksum, "
                    "created_dt, updated_dt, created_user_id, updated_user_id, action, valid_from_dt, valid_to_dt, "
                    "is_current, version_no) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                ),
                params=(
                    key_id,
                    keyset_id,
                    row["key_char"],
                    1 if row["is_new_key"] else 0,
                    row["row_checksum"],
                    now,
                    now,
                    deleted_by,
                    deleted_by,
                    "DELETE",
                    now,
                    "9999-12-31 23:59:59",
                    1,
                    next_key_version,
                ),
            )

        self._db.execute(query="DELETE FROM keyset_keys WHERE keyset_id = %s", params=(keyset_id,))
        self._db.execute(query="DELETE FROM keyset WHERE keyset_id = %s", params=(keyset_id,))
        return True

    def validate_key_progression_uniqueness(
        self,
        *,
        keyboard_id: str,
        progression_order: int,
        keys: list[str],
        keyset_id: Optional[str] = None,
    ) -> None:
        query = (
            "SELECT DISTINCT kk.key_char FROM keyset k "
            "JOIN keyset_keys kk ON kk.keyset_id = k.keyset_id "
            "WHERE k.keyboard_id = %s AND k.progression_order < %s"
        )
        params: list[object] = [keyboard_id, progression_order]
        if keyset_id:
            query += " AND k.keyset_id <> %s"
            params.append(keyset_id)

        rows = self._db.fetchall(query=query, params=tuple(params))
        prior_keys = {str(r["key_char"]) for r in rows}
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
        updated_by: str,
    ) -> None:
        if not updated_by:
            raise ValueError("updated_by user ID is required for audit trail")
        try:
            UUID(updated_by)
        except ValueError as exc:
            raise ValueError(f"updated_by must be a valid UUID, got: {updated_by}") from exc

        if keyset1.keyboard_id != keyset2.keyboard_id:
            raise ValueError("Cannot swap progression order between different keyboards")

        now = self._now_iso()

        self._db.execute(
            query=(
                "UPDATE keyset_history SET valid_to_dt = %s, is_current = 0 "
                "WHERE keyset_id IN (%s, %s) AND is_current = 1"
            ),
            params=(now, str(keyset1.keyset_id), str(keyset2.keyset_id)),
        )

        checksum1 = self._compute_keyset_checksum(keyset1)
        checksum2 = self._compute_keyset_checksum(keyset2)

        # Use three-step approach to avoid unique constraint violation during swap:
        # 1. Set first keyset to temporary negative value
        # 2. Set second keyset to first's target value
        # 3. Set first keyset to its final value
        temp_order = -99999

        self._db.execute(
            query=(
                "UPDATE keyset SET progression_order = %s, updated_dt = %s, updated_user_id = %s "
                "WHERE keyset_id = %s"
            ),
            params=(temp_order, now, updated_by, str(keyset1.keyset_id)),
        )

        self._db.execute(
            query=(
                "UPDATE keyset SET progression_order = %s, row_checksum = %s, "
                "updated_dt = %s, updated_user_id = %s WHERE keyset_id = %s"
            ),
            params=(
                keyset2.progression_order,
                checksum2,
                now,
                updated_by,
                str(keyset2.keyset_id),
            ),
        )

        self._db.execute(
            query=(
                "UPDATE keyset SET progression_order = %s, row_checksum = %s, "
                "updated_dt = %s, updated_user_id = %s WHERE keyset_id = %s"
            ),
            params=(
                keyset1.progression_order,
                checksum1,
                now,
                updated_by,
                str(keyset1.keyset_id),
            ),
        )

        next1 = self._get_next_version(str(keyset1.keyset_id))
        next2 = self._get_next_version(str(keyset2.keyset_id))

        history_query = (
            "INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order, row_checksum, "
            "created_dt, updated_dt, created_user_id, updated_user_id, action, valid_from_dt, valid_to_dt, "
            "is_current, version_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )

        self._db.execute(
            query=history_query,
            params=(
                str(keyset1.keyset_id),
                str(keyset1.keyboard_id),
                keyset1.keyset_name,
                keyset1.progression_order,
                checksum1,
                now,
                now,
                updated_by,
                updated_by,
                "UPDATE",
                now,
                "9999-12-31 23:59:59",
                1,
                next1,
            ),
        )

        self._db.execute(
            query=history_query,
            params=(
                str(keyset2.keyset_id),
                str(keyset2.keyboard_id),
                keyset2.keyset_name,
                keyset2.progression_order,
                checksum2,
                now,
                now,
                updated_by,
                updated_by,
                "UPDATE",
                now,
                "9999-12-31 23:59:59",
                1,
                next2,
            ),
        )

        self._mark_persisted(keyset1)
        self._mark_persisted(keyset2)

    # ------------------------------------------------------------------
    # Internal key helpers
    # ------------------------------------------------------------------
    def _keys_changed(self, new_keyset: Keyset, old_keyset: Keyset) -> bool:
        if len(new_keyset.keys) != len(old_keyset.keys):
            return True
        new_set = {(k.key_char, k.is_new_key) for k in new_keyset.keys}
        old_set = {(k.key_char, k.is_new_key) for k in old_keyset.keys}
        return new_set != old_set

    def _get_next_version(self, keyset_id: str) -> int:
        row = self._db.fetchone(
            query="SELECT COALESCE(MAX(version_no), 0) + 1 AS next_version FROM keyset_history WHERE keyset_id = %s",
            params=(keyset_id,),
        )
        return int(str(row["next_version"])) if row else 1

    def _get_next_key_version(self, key_id: str) -> int:
        row = self._db.fetchone(
            query=(
                "SELECT COALESCE(MAX(version_no), 0) + 1 AS next_version FROM keyset_keys_history WHERE key_id = %s"
            ),
            params=(key_id,),
        )
        return int(str(row["next_version"])) if row else 1

    def _insert_key(
        self,
        key: KeysetKey,
        keyset_id: str,
        now: str,
        user_id: str,
        *,
        action: str,
        version_no: int,
    ) -> None:
        checksum = self._compute_key_checksum(key)
        key.keyset_id = keyset_id
        key.in_db = True

        self._db.execute(
            query=(
                "INSERT INTO keyset_keys (key_id, keyset_id, key_char, is_new_key, row_checksum, created_dt, "
                "updated_dt, created_user_id, updated_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
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

        self._insert_key_history(
            key,
            keyset_id,
            now,
            user_id,
            action=action,
            version_no=version_no,
        )

    def _insert_key_history(
        self,
        key: KeysetKey,
        keyset_id: str,
        now: str,
        user_id: str,
        *,
        action: str,
        version_no: int,
    ) -> None:
        checksum = self._compute_key_checksum(key)
        self._db.execute(
            query=(
                "INSERT INTO keyset_keys_history (key_id, keyset_id, key_char, is_new_key, row_checksum, created_dt, "
                "updated_dt, created_user_id, updated_user_id, action, valid_from_dt, valid_to_dt, is_current, "
                "version_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
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
                action,
                now,
                "9999-12-31 23:59:59",
                1,
                version_no,
            ),
        )

    def _insert_keyset(self, keyset: Keyset, now: str, user_id: str) -> None:
        checksum = self._compute_keyset_checksum(keyset)

        self._db.execute(
            query=(
                "INSERT INTO keyset (keyset_id, keyboard_id, keyset_name, progression_order, row_checksum, "
                "created_dt, updated_dt, created_user_id, updated_user_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
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

        self._db.execute(
            query=(
                "INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order, row_checksum, "
                "created_dt, updated_dt, created_user_id, updated_user_id, action, valid_from_dt, valid_to_dt, "
                "is_current, version_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
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

        for key in keyset.keys:
            self._insert_key(
                key,
                str(keyset.keyset_id),
                now,
                user_id,
                action="INSERT",
                version_no=1,
            )

    def _update_keyset(self, keyset: Keyset, existing: Keyset, now: str, user_id: str) -> None:
        checksum = self._compute_keyset_checksum(keyset)
        row = self._db.fetchone(
            query="SELECT row_checksum FROM keyset WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )
        old_checksum = row["row_checksum"] if row else None
        if isinstance(old_checksum, memoryview):
            old_checksum = bytes(old_checksum)

        if old_checksum == checksum and not self._keys_changed(keyset, existing):
            self._mark_persisted(keyset)
            return

        self._db.execute(
            query=(
                "UPDATE keyset_history SET valid_to_dt = %s, is_current = 0 "
                "WHERE keyset_id = %s AND is_current = 1"
            ),
            params=(now, str(keyset.keyset_id)),
        )

        next_version = self._get_next_version(str(keyset.keyset_id))

        self._db.execute(
            query=(
                "UPDATE keyset SET keyset_name = %s, progression_order = %s, row_checksum = %s, "
                "updated_dt = %s, updated_user_id = %s WHERE keyset_id = %s"
            ),
            params=(
                keyset.keyset_name,
                keyset.progression_order,
                checksum,
                now,
                user_id,
                str(keyset.keyset_id),
            ),
        )

        self._db.execute(
            query=(
                "INSERT INTO keyset_history (keyset_id, keyboard_id, keyset_name, progression_order, row_checksum, "
                "created_dt, updated_dt, created_user_id, updated_user_id, action, valid_from_dt, valid_to_dt, "
                "is_current, version_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
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

        self._sync_keys(keyset, now, user_id)

    def _sync_keys(self, keyset: Keyset, now: str, user_id: str) -> None:
        existing_rows = self._db.fetchall(
            query="SELECT key_id, key_char, is_new_key, row_checksum FROM keyset_keys WHERE keyset_id = %s",
            params=(str(keyset.keyset_id),),
        )
        existing_by_id = {str(row["key_id"]): row for row in existing_rows}
        new_ids: set[str] = set()

        for key in keyset.keys:
            key.keyset_id = str(keyset.keyset_id)
            key_id = str(key.key_id)
            new_ids.add(key_id)

            if key_id in existing_by_id:
                old = existing_by_id[key_id]
                old_checksum = old["row_checksum"]
                if isinstance(old_checksum, memoryview):
                    old_checksum = bytes(old_checksum)
                new_checksum = self._compute_key_checksum(key)

                if (
                    str(old["key_char"]) != key.key_char
                    or bool(old["is_new_key"]) != bool(key.is_new_key)
                    or old_checksum != new_checksum
                ):
                    self._db.execute(
                        query=(
                            "UPDATE keyset_keys SET key_char = %s, is_new_key = %s, row_checksum = %s, "
                            "updated_dt = %s, updated_user_id = %s WHERE key_id = %s"
                        ),
                        params=(
                            key.key_char,
                            int(key.is_new_key),
                            new_checksum,
                            now,
                            user_id,
                            key_id,
                        ),
                    )

                    self._db.execute(
                        query=(
                            "UPDATE keyset_keys_history SET valid_to_dt = %s, is_current = 0 "
                            "WHERE key_id = %s AND is_current = 1"
                        ),
                        params=(now, key_id),
                    )

                    next_version = self._get_next_key_version(key_id)
                    self._insert_key_history(
                        key,
                        str(keyset.keyset_id),
                        now,
                        user_id,
                        action="UPDATE",
                        version_no=next_version,
                    )
            else:
                self._insert_key(
                    key,
                    str(keyset.keyset_id),
                    now,
                    user_id,
                    action="INSERT",
                    version_no=1,
                )

        for key_id, row in existing_by_id.items():
            if key_id not in new_ids:
                self._db.execute(
                    query="DELETE FROM keyset_keys WHERE key_id = %s", params=(key_id,)
                )
                self._db.execute(
                    query=(
                        "UPDATE keyset_keys_history SET valid_to_dt = %s, is_current = 0 "
                        "WHERE key_id = %s AND is_current = 1"
                    ),
                    params=(now, key_id),
                )
                next_version = self._get_next_key_version(key_id)
                self._db.execute(
                    query=(
                        "INSERT INTO keyset_keys_history (key_id, keyset_id, key_char, is_new_key, row_checksum, "
                        "created_dt, updated_dt, created_user_id, updated_user_id, action, valid_from_dt, "
                        "valid_to_dt, is_current, version_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    ),
                    params=(
                        key_id,
                        str(keyset.keyset_id),
                        row["key_char"],
                        1 if row["is_new_key"] else 0,
                        row["row_checksum"],
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
        self._mark_persisted(keyset)
