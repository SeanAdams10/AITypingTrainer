"""KeysetManager: application-managed persistence and history for Keysets.

Implements creation, listing, and promotion (order swap) with SCD-2 history
and checksum-based no-op detection as outlined in Prompts/Keysets.md.

This minimal implementation focuses on functionality required by
`tests/models/test_keysets.py` and is designed to be extended.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

from db.database_manager import DatabaseManager
from helpers.debug_util import DebugUtil
from models.keyset import Keyset, KeysetKey


@dataclass
class _Now:
    """Timestamp provider to simplify testing/mocking later."""

    @staticmethod
    def iso() -> str:
        import datetime as _dt

        return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class KeysetManager:
    """Manage Keyset entities, their keys, and SCD-2 history (no triggers)."""

    def __init__(self, db: DatabaseManager, debug_util: Optional[DebugUtil] = None) -> None:
        self.db = db
        self.debug_util = debug_util or DebugUtil("quiet")
        # Ensure schema exists per spec
        self.db.init_tables()
        # Basic single-keyboard cache structures (can be extended later)
        self._cached_keyboard_id: Optional[str] = None
        self._cached_keysets: Dict[str, Keyset] = {}

    # ---- Helpers ----
    def _dbg(self, *args: object, **kwargs: object) -> None:
        if self.debug_util:
            self.debug_util.debugMessage(*args, **kwargs)

    def _checksum_keyset(self, ks: Keyset) -> str:
        payload = f"{ks.keyboard_id}|{ks.keyset_name}|{int(ks.progression_order)}"
        return sha256(payload.encode("utf-8")).hexdigest()

    def _checksum_key(self, k: KeysetKey, keyset_id: str) -> str:
        payload = f"{keyset_id}|{k.key_char}|{1 if k.is_new_key else 0}"
        return sha256(payload.encode("utf-8")).hexdigest()

    def _current_hist_version(self, table: str, id_col: str, entity_id: str) -> int:
        row = self.db.fetchone(
            f"SELECT MAX(version_no) AS v FROM {table} WHERE {id_col} = ?",
            (entity_id,),
        )
        v = int(row["v"]) if row and row.get("v") is not None else 0  # type: ignore[index]
        return v

    def _close_current_history(self, table: str, id_col: str, entity_id: str) -> None:
        now = _Now.iso()
        self.db.execute(
            f"UPDATE {table} SET valid_to = ?, is_current = 0 WHERE {id_col} = ? AND is_current = 1",
            (now, entity_id),
        )

    def _insert_keyset_history(
        self,
        ks: Keyset,
        action: str,
        version_no: int,
        checksum: str,
        *,
        user_id: Optional[str] = None,
    ) -> None:
        now = _Now.iso()
        self.db.execute(
            """
            INSERT INTO keysets_history (
              history_id, keyset_id, keyboard_id, keyset_name, progression_order,
              action, valid_from, valid_to, is_current, version_no, recorded_at,
              created_user_id, updated_user_id, row_checksum
            ) VALUES(?, ?, ?, ?, ?, ?, ?, '9999-12-31 23:59:59', 1, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                ks.keyset_id,
                ks.keyboard_id,
                ks.keyset_name,
                int(ks.progression_order),
                action,
                now,
                version_no,
                now,
                user_id,
                user_id,
                checksum,
            ),
        )

    def _insert_key_history(
        self,
        k: KeysetKey,
        keyset_id: str,
        action: str,
        version_no: int,
        checksum: str,
        *,
        user_id: Optional[str] = None,
    ) -> None:
        now = _Now.iso()
        self.db.execute(
            """
            INSERT INTO keyset_keys_history (
              history_id, key_id, keyset_id, key_char, is_new_key,
              action, valid_from, valid_to, is_current, version_no, recorded_at,
              created_user_id, updated_user_id, row_checksum
            ) VALUES(?, ?, ?, ?, ?, ?, ?, '9999-12-31 23:59:59', 1, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                k.key_id,
                keyset_id,
                k.key_char,
                1 if k.is_new_key else 0,
                action,
                now,
                version_no,
                now,
                user_id,
                user_id,
                checksum,
            ),
        )

    # ---- Public API used in tests/UI ----
    def preload_keysets_for_keyboard(self, keyboard_id: str) -> List[Keyset]:
        """Load all keysets + keys into cache ordered by progression_order."""
        self._cached_keyboard_id = keyboard_id
        rows = self.db.fetchall(
            """
            SELECT keyset_id, keyboard_id, keyset_name, progression_order
            FROM keysets
            WHERE keyboard_id = ?
            ORDER BY progression_order
            """,
            (keyboard_id,),
        )
        self._cached_keysets.clear()
        for r in rows:
            ks = Keyset(
                keyset_id=str(r["keyset_id"]),
                keyboard_id=str(r["keyboard_id"]),
                keyset_name=str(r["keyset_name"]),
                progression_order=int(r["progression_order"]),
                keys=[],
                in_db=True,
            )
            # Load keys
            krows = self.db.fetchall(
                "SELECT key_id, key_char, is_new_key FROM keyset_keys WHERE keyset_id = ? ORDER BY key_char",
                (ks.keyset_id,),
            )
            for kr in krows:
                ks.keys.append(
                    KeysetKey(
                        key_id=str(kr["key_id"]),
                        keyset_id=ks.keyset_id,
                        key_char=str(kr["key_char"]),
                        is_new_key=bool(int(kr["is_new_key"])),
                        in_db=True,
                    )
                )
            self._cached_keysets[ks.keyset_id or ""] = ks
        return list(self._cached_keysets.values())

    def list_keysets_for_keyboard(self, keyboard_id: str) -> List[Keyset]:
        if self._cached_keyboard_id == keyboard_id and self._cached_keysets:
            return list(self._cached_keysets.values())
        return self.preload_keysets_for_keyboard(keyboard_id)

    def get_keyset(self, keyset_id: str) -> Optional[Keyset]:
        ks = self._cached_keysets.get(keyset_id)
        if ks:
            return ks
        # Fallback query
        r = self.db.fetchone(
            "SELECT keyset_id, keyboard_id, keyset_name, progression_order FROM keysets WHERE keyset_id = ?",
            (keyset_id,),
        )
        if not r:
            return None
        ks = Keyset(
            keyset_id=str(r["keyset_id"]),
            keyboard_id=str(r["keyboard_id"]),
            keyset_name=str(r["keyset_name"]),
            progression_order=int(r["progression_order"]),
            keys=[],
            in_db=True,
        )
        self._cached_keysets[ks.keyset_id or ""] = ks
        return ks

    def get_keys_for_keyset(self, keyset_id: str) -> List[Tuple[str, bool]]:
        # Prefer cache
        ks = self._cached_keysets.get(keyset_id)
        if ks:
            return [(k.key_char, bool(k.is_new_key)) for k in sorted(ks.keys, key=lambda x: x.key_char.lower())]
        # Fallback query
        rows = self.db.fetchall(
            "SELECT key_char, is_new_key FROM keyset_keys WHERE keyset_id = ? ORDER BY key_char",
            (keyset_id,),
        )
        return [(str(r["key_char"]), bool(int(r["is_new_key"]))) for r in rows]

    def create_keyset(self, ks: Keyset, *, created_by: Optional[str] = None) -> str:
        """Create a keyset with keys, enforce unique progression per keyboard, write history."""
        # Enforce unique progression per keyboard
        exists = self.db.fetchone(
            "SELECT 1 AS x FROM keysets WHERE keyboard_id = ? AND progression_order = ?",
            (ks.keyboard_id, int(ks.progression_order)),
        )
        if exists:
            raise ValueError("Duplicate progression_order for keyboard")

        now = _Now.iso()
        checksum = self._checksum_keyset(ks)
        # Insert base row
        self.db.execute(
            """
            INSERT INTO keysets (keyset_id, keyboard_id, keyset_name, progression_order, created_at, updated_at, row_checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ks.keyset_id,
                ks.keyboard_id,
                ks.keyset_name,
                int(ks.progression_order),
                now,
                now,
                checksum,
            ),
        )
        # History version 1 (create)
        self._insert_keyset_history(ks, action="I", version_no=1, checksum=checksum, user_id=created_by)

        # Insert keys and their history
        if ks.keys:
            params: List[Tuple[str, str, str, int, str, str]] = []
            for k in ks.keys:
                # Ensure key has parent id
                k.keyset_id = ks.keyset_id
                ksum = self._checksum_key(k, ks.keyset_id or "")
                params.append(
                    (
                        k.key_id or str(uuid4()),
                        ks.keyset_id or "",
                        k.key_char,
                        1 if k.is_new_key else 0,
                        now,
                        now,
                    )
                )
                # Insert history v1
                self._insert_key_history(k, ks.keyset_id or "", action="I", version_no=1, checksum=ksum, user_id=created_by)
            self.db.execute_many(
                """
                INSERT INTO keyset_keys (key_id, keyset_id, key_char, is_new_key, created_at, updated_at, row_checksum)
                VALUES(?, ?, ?, ?, ?, ?, '')
                """,
                params,
            )
            # Update checksums for inserted keys (SQLite lacks computed columns; set individually)
            # This loop is small; optimize later if needed
            for k in ks.keys:
                ksum = self._checksum_key(k, ks.keyset_id or "")
                self.db.execute(
                    "UPDATE keyset_keys SET row_checksum = ? WHERE key_id = ?",
                    (ksum, k.key_id or ""),
                )

        # Cache update
        ks.in_db = True
        for k in ks.keys:
            k.in_db = True
        self._cached_keysets[ks.keyset_id or ""] = ks
        return ks.keyset_id or ""

    def promote_keyset(self, keyboard_id: str, keyset_id: str) -> bool:
        """Promote a keyset by swapping its order with the previous one for the same keyboard."""
        row = self.db.fetchone(
            "SELECT progression_order FROM keysets WHERE keyset_id = ? AND keyboard_id = ?",
            (keyset_id, keyboard_id),
        )
        if not row:
            return False
        current_order = int(row["progression_order"])  # type: ignore[index]
        if current_order <= 1:
            return True  # nothing to do, already at top
        prev = self.db.fetchone(
            "SELECT keyset_id FROM keysets WHERE keyboard_id = ? AND progression_order = ?",
            (keyboard_id, current_order - 1),
        )
        if not prev:
            return False
        prev_id = str(prev["keyset_id"])  # type: ignore[index]

        # Perform swap using a sentinel to avoid transient unique conflicts
        self.db.execute(
            "UPDATE keysets SET progression_order = 0 WHERE keyset_id = ? AND keyboard_id = ?",
            (keyset_id, keyboard_id),
        )
        self.db.execute(
            "UPDATE keysets SET progression_order = ? WHERE keyset_id = ? AND keyboard_id = ?",
            (current_order, prev_id, keyboard_id),
        )
        self.db.execute(
            "UPDATE keysets SET progression_order = ? WHERE keyset_id = ? AND keyboard_id = ?",
            (current_order - 1, keyset_id, keyboard_id),
        )

        # Write history records for both affected keysets
        k1 = self.get_keyset(keyset_id)
        k2 = self.get_keyset(prev_id)
        if k1:
            k1.progression_order = current_order - 1
            csum1 = self._checksum_keyset(k1)
            # close and insert new version
            self._close_current_history("keysets_history", "keyset_id", k1.keyset_id or "")
            ver1 = self._current_hist_version("keysets_history", "keyset_id", k1.keyset_id or "") + 1
            self._insert_keyset_history(k1, action="U", version_no=ver1, checksum=csum1)
        if k2:
            k2.progression_order = current_order
            csum2 = self._checksum_keyset(k2)
            self._close_current_history("keysets_history", "keyset_id", k2.keyset_id or "")
            ver2 = self._current_hist_version("keysets_history", "keyset_id", k2.keyset_id or "") + 1
            self._insert_keyset_history(k2, action="U", version_no=ver2, checksum=csum2)

        # Refresh cache
        self.preload_keysets_for_keyboard(keyboard_id)
        return True

    # Convenience used by UI dialog; not used by current tests but kept minimal
    def save_all_keysets(self, keysets: Sequence[Keyset]) -> bool:
        for ks in keysets:
            if not ks.in_db:
                self.create_keyset(ks)
            else:
                # Minimal update: only name/order; real impl should also sync keys
                # Compare checksum to decide if update/history is required
                existing = self.db.fetchone("SELECT row_checksum FROM keysets WHERE keyset_id = ?", (ks.keyset_id,))
                new_sum = self._checksum_keyset(ks)
                if existing and str(existing.get("row_checksum")) == new_sum:
                    continue  # no-op
                now = _Now.iso()
                self.db.execute(
                    "UPDATE keysets SET keyset_name = ?, progression_order = ?, updated_at = ?, row_checksum = ? WHERE keyset_id = ?",
                    (ks.keyset_name, int(ks.progression_order), now, new_sum, ks.keyset_id or ""),
                )
                # history close-update
                self._close_current_history("keysets_history", "keyset_id", ks.keyset_id or "")
                ver = self._current_hist_version("keysets_history", "keyset_id", ks.keyset_id or "") + 1
                self._insert_keyset_history(ks, action="U", version_no=ver, checksum=new_sum)
        return True

    def delete_keyset(self, keyset_id: str, *, deleted_by: Optional[str] = None) -> bool:
        """Delete a keyset and its keys with SCD-2 history bookkeeping.

        Steps:
        - Select keys; for each, close current history and insert a 'D' record.
        - Delete keys (child table) first.
        - Close current keyset history and insert a 'D' record for the keyset.
        - Delete the keyset row.
        - Update cache.
        """
        # Verify exists
        row = self.db.fetchone(
            "SELECT keyset_id, keyboard_id, keyset_name, progression_order FROM keysets WHERE keyset_id = ?",
            (keyset_id,),
        )
        if not row:
            return False
        ks = Keyset(
            keyset_id=str(row["keyset_id"]),
            keyboard_id=str(row["keyboard_id"]),
            keyset_name=str(row["keyset_name"]),
            progression_order=int(row["progression_order"]),
            keys=[],
            in_db=True,
        )

        # Child keys: write delete history then delete
        krows = self.db.fetchall(
            "SELECT key_id, key_char, is_new_key FROM keyset_keys WHERE keyset_id = ?",
            (keyset_id,),
        )
        now = _Now.iso()
        for kr in krows:
            key = KeysetKey(
                key_id=str(kr["key_id"]),
                keyset_id=keyset_id,
                key_char=str(kr["key_char"]),
                is_new_key=bool(int(kr["is_new_key"])),
                in_db=True,
            )
            # Close current, then add a 'D' record with is_current=0 and valid_to=now
            self._close_current_history("keyset_keys_history", "key_id", key.key_id or "")
            ver = self._current_hist_version("keyset_keys_history", "key_id", key.key_id or "") + 1
            checksum = self._checksum_key(key, keyset_id)
            self.db.execute(
                """
                INSERT INTO keyset_keys_history (
                  history_id, key_id, keyset_id, key_char, is_new_key,
                  action, valid_from, valid_to, is_current, version_no, recorded_at,
                  created_user_id, updated_user_id, row_checksum
                ) VALUES (?, ?, ?, ?, ?, 'D', ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    key.key_id,
                    keyset_id,
                    key.key_char,
                    1 if key.is_new_key else 0,
                    now,
                    now,
                    ver,
                    now,
                    deleted_by,
                    deleted_by,
                    checksum,
                ),
            )

        # Delete child rows
        self.db.execute("DELETE FROM keyset_keys WHERE keyset_id = ?", (keyset_id,))

        # Keyset history: close current, then insert a 'D' record
        self._close_current_history("keysets_history", "keyset_id", keyset_id)
        ver_k = self._current_hist_version("keysets_history", "keyset_id", keyset_id) + 1
        checksum_k = self._checksum_keyset(ks)
        self.db.execute(
            """
            INSERT INTO keysets_history (
              history_id, keyset_id, keyboard_id, keyset_name, progression_order,
              action, valid_from, valid_to, is_current, version_no, recorded_at,
              created_user_id, updated_user_id, row_checksum
            ) VALUES(?, ?, ?, ?, ?, 'D', ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                ks.keyset_id,
                ks.keyboard_id,
                ks.keyset_name,
                int(ks.progression_order),
                now,
                now,
                ver_k,
                now,
                deleted_by,
                deleted_by,
                checksum_k,
            ),
        )

        # Delete keyset row
        self.db.execute("DELETE FROM keysets WHERE keyset_id = ?", (keyset_id,))

        # Cache cleanup
        self._cached_keysets.pop(keyset_id, None)
        return True
