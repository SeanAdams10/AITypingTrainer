"""Unit tests for models.settings_manager.SettingManager.

Covers CRUD operations, validation, SCD-2 history tracking, and error handling.
Uses real PostgreSQL database integration for reliable testing.
"""

import sys
import uuid
from datetime import datetime, timezone
from typing import Generator

import pytest

from db.database_manager import ConnectionType, DatabaseManager
from models.setting import Setting, SettingNotFound, SettingValidationError
from models.setting_manager import SettingManager
from models.setting_type_manager import SettingTypeManager
from models.setting_type import SettingType
from models.setting_cache import SettingCacheEntry, global_setting_cache

# Backwards-compatibility alias for legacy type hints in this test module
SettingManager = SettingManager


@pytest.fixture(scope="function")
def setting_type_mgr(db_with_tables: DatabaseManager) -> Generator[SettingTypeManager, None, None]:
    """Fixture: Provides a SettingTypeManager for creating setting types."""
    assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER
    manager = SettingTypeManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture(scope="function")
def setting_mgr(
    db_with_tables: DatabaseManager,
    setting_type_mgr: SettingTypeManager,
) -> Generator[SettingManager, None, None]:
    """Fixture: Provides a SettingManager singleton with initialized cache.

    Test objective: Ensure database connection is Docker PostgreSQL for safety,
    create common setting types, and initialize the SettingManager singleton
    backed by the shared global_setting_cache.
    """
    assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER

    # Ensure a clean singleton and cache for each test
    SettingManager.reset_instance()
    global_setting_cache.clear()

    # Create common setting types for testing
    common_types = [
        ("USRTHM", "User Theme", "user", "string"),
        ("USRLNG", "User Language", "user", "string"),
        ("TYPE01", "Test Type 1", "user", "string"),
        ("TYPE02", "Test Type 2", "user", "string"),
        ("TYPE03", "Test Type 3", "user", "string"),
        ("OTHER1", "Other Type 1", "user", "string"),
        ("STYPE1", "System Type 1", "global", "string"),
        ("STYPE2", "System Type 2", "global", "string"),
    ]

    admin_user_id = uuid.uuid4()
    for type_id, name, entity_type, data_type in common_types:
        st = SettingType(
            setting_type_id=type_id,
            setting_type_name=name,
            description=f"Test setting type {type_id}",
            related_entity_type=entity_type,
            data_type=data_type,
            default_value="default",
            validation_rules=None,
            is_system=False,
            is_active=True,
            created_user_id=str(admin_user_id),
            updated_user_id=str(admin_user_id),
            created_dt=datetime.now(timezone.utc),
            updated_dt=datetime.now(timezone.utc),
            row_checksum="",
        )
        st.row_checksum = st.calculate_checksum()
        setting_type_mgr.create_setting_type(setting_type=st, user_id=admin_user_id)

    manager = SettingManager.get_instance(db_manager=db_with_tables)
    yield manager

    # Reset after test to avoid cross-test contamination
    SettingManager.reset_instance()
    global_setting_cache.clear()


@pytest.fixture(scope="function")
def test_user_id() -> str:
    """Fixture: Provides a consistent test user ID."""
    return str(uuid.uuid4())


@pytest.fixture(scope="function")
def test_entity_id() -> str:
    """Fixture: Provides a consistent test entity ID."""
    return str(uuid.uuid4())


def create_test_setting(
    setting_type_id: str = "USRTHM",
    setting_value: str = "dark",
    related_entity_id: str | None = None,
    user_id: str | None = None,
) -> Setting:
    """Helper: Create a valid Setting for testing with all required fields."""
    now = datetime.now(timezone.utc)
    uid = user_id or str(uuid.uuid4())
    entity_id = related_entity_id or str(uuid.uuid4())
    
    setting = Setting(
        setting_type_id=setting_type_id,
        setting_value=setting_value,
        related_entity_id=entity_id,
        row_checksum=b"",  # Will be calculated
        created_dt=now,
        updated_dt=now,
        created_user_id=uid,
        updated_user_id=uid,
    )
    # Calculate proper checksum
    setting.row_checksum = setting.calculate_checksum()
    return setting


class TestSettingManagerCRUD:
    """Test suite for SettingManager CRUD operations."""

    def test_save_setting_new(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Create a new setting via cache and verify persistence.

        Verifies that a new setting added to the global_setting_cache is
        persisted to the settings table and that an SCD-2 history row with
        action='I' and version_no=1 is created.
        """
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )

        # Write to cache and flush
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        assert setting.setting_id is not None

        # Verify base table row
        rows = db_with_tables.fetchall(
            query=(
                "SELECT setting_type_id, setting_value, related_entity_id "
                "FROM settings WHERE setting_id = %s"
            ),
            params=(setting.setting_id,),
        )
        assert len(rows) == 1
        assert rows[0]["setting_type_id"] == "USRTHM"
        assert rows[0]["setting_value"] == "dark"
        assert rows[0]["related_entity_id"] == test_entity_id

        # Verify history row
        history_rows = db_with_tables.fetchall(
            query=(
                "SELECT action, version_no, is_current "
                "FROM settings_history WHERE setting_id = %s"
                " ORDER BY version_no"
            ),
            params=(setting.setting_id,),
        )
        assert len(history_rows) == 1
        assert history_rows[0]["action"] == "I"
        assert history_rows[0]["version_no"] == 1
        assert history_rows[0]["is_current"] is True

    def test_save_setting_update_existing(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Update an existing setting and verify SCD-2 history.

        Creates an initial setting and persists it, then changes the value and
        flushes again. Verifies that the settings table reflects the new value
        and that settings_history contains both an 'I' and a 'U' row with
        correct versioning and current flags.
        """
        # Create initial setting
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        original_id = setting.setting_id

        # Update the value via cache (same setting_id)
        setting.setting_value = "light"
        setting.row_checksum = setting.calculate_checksum()
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True

        # Verify base table row
        rows = db_with_tables.fetchall(
            query=(
                "SELECT setting_value FROM settings WHERE setting_id = %s"
            ),
            params=(original_id,),
        )
        assert len(rows) == 1
        assert rows[0]["setting_value"] == "light"

        # Verify history table rows
        history_rows = db_with_tables.fetchall(
            query=(
                "SELECT action, version_no, is_current, setting_value "
                "FROM settings_history WHERE setting_id = %s "
                "ORDER BY version_no"
            ),
            params=(original_id,),
        )
        assert len(history_rows) == 2
        # First version (insert)
        assert history_rows[0]["action"] == "I"
        assert history_rows[0]["version_no"] == 1
        assert history_rows[0]["is_current"] is False
        assert history_rows[0]["setting_value"] == "dark"
        # Second version (update)
        assert history_rows[1]["action"] == "U"
        assert history_rows[1]["version_no"] == 2
        assert history_rows[1]["is_current"] is True
        assert history_rows[1]["setting_value"] == "light"

    def test_deprecated_get_setting_raises_runtimeerror(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Ensure deprecated get_setting raises RuntimeError.

        Per Settings requirements, per-setting getters must be provided by the
        cache layer, not SettingManager. The legacy get_setting method is kept
        only for compatibility and must raise a RuntimeError with a clear
        deprecation message.
        """
        with pytest.raises(RuntimeError) as exc:
            setting_mgr.get_setting(
                setting_type_id="USRTHM",
                related_entity_id=test_entity_id,
                default_value="auto",
            )
        assert "deprecated" in str(exc.value).lower()

    def test_deprecated_set_setting_raises_runtimeerror(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Ensure deprecated set_setting raises RuntimeError.

        Verifies that direct per-setting writes on SettingManager are blocked
        and callers are expected to use global_setting_cache instead.
        """
        with pytest.raises(RuntimeError) as exc:
            setting_mgr.set_setting(
                setting_type_id="USRTHM",
                related_entity_id=test_entity_id,
                value="dark",
                user_id=test_user_id,
            )
        assert "deprecated" in str(exc.value).lower()

    def test_list_settings_empty(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: List settings for an entity when none exist."""
        settings = setting_mgr.list_settings(related_entity_id=test_entity_id)
        assert settings == []

    def test_list_settings_populated(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: List multiple settings for an entity."""
        # Create three settings for the same entity
        setting_types = ["TYPE01", "TYPE02", "TYPE03"]
        for type_id in setting_types:
            setting = create_test_setting(
                setting_type_id=type_id,
                setting_value=f"value_{type_id}",
                related_entity_id=test_entity_id,
                user_id=test_user_id,
            )
            global_setting_cache.set(
                type_id,
                test_entity_id,
                SettingCacheEntry(setting),
            )
        
        # List all settings
        settings = setting_mgr.list_settings(related_entity_id=test_entity_id)
        assert len(settings) == 3
        
        # Verify all are for the same entity
        assert all(s.related_entity_id == test_entity_id for s in settings)
        
        # Verify type IDs
        retrieved_types = sorted([s.setting_type_id for s in settings])
        assert retrieved_types == sorted(setting_types)

    def test_delete_setting_existing(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Delete an existing setting via cache/manager.

        Creates and persists a setting, then uses SettingManager.delete_setting
        to mark it deleted and flushes the cache. Verifies that the base row is
        removed and that a 'D' history version is written as the current row.
        """
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        setting_id = setting.setting_id

        # Mark for deletion in cache via manager and flush
        setting_mgr.delete_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        assert setting_mgr.flush() is True

        # Verify base row is gone
        rows = db_with_tables.fetchall(
            query="SELECT 1 FROM settings WHERE setting_id = %s", params=(setting_id,)
        )
        assert rows == []

        # Verify history rows include delete
        history_rows = db_with_tables.fetchall(
            query=(
                "SELECT action, version_no, is_current "
                "FROM settings_history WHERE setting_id = %s "
                "ORDER BY version_no"
            ),
            params=(setting_id,),
        )
        assert len(history_rows) == 2
        assert history_rows[0]["action"] == "I"
        assert history_rows[0]["is_current"] is False
        assert history_rows[1]["action"] == "D"
        assert history_rows[1]["is_current"] is True

    def test_delete_setting_not_found(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Attempt to delete a non-existent setting.

        Verifies that attempting to delete a missing setting raises
        SettingNotFound rather than silently succeeding.
        """
        with pytest.raises(SettingNotFound):
            setting_mgr.delete_setting(
                setting_type_id="NOTFND",
                related_entity_id=test_entity_id,
                user_id=str(uuid.uuid4()),
            )

    # Note: bulk delete-all behavior is implemented at higher service/UI
    # layers using cache semantics; SettingManager does not expose a
    # dedicated delete_all_settings_for_entity API in the current design.


class TestSettingValidation:
    """Test suite for Setting validation rules."""

    @pytest.mark.parametrize(
        "setting_type_id,err_msg_part",
        [
            ("", "must be exactly 6 characters"),
            ("ABC", "must be exactly 6 characters"),
            ("ABCDEFGH", "must be exactly 6 characters"),
            ("ABC€ΩΨ", "must be ASCII-only"),
        ],
    )
    def test_invalid_setting_type_id_format(
        self, setting_mgr: SettingManager, setting_type_id: str, err_msg_part: str
    ) -> None:
        """Test objective: Validate setting_type_id format requirements."""
        with pytest.raises((ValueError, SettingValidationError)) as e:
            setting = create_test_setting(setting_type_id=setting_type_id)
            setting_mgr.save_setting(setting=setting)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_invalid_related_entity_id(
        self, setting_mgr: SettingManager, test_user_id: str
    ) -> None:
        """Test objective: Validate related_entity_id must be a valid UUID."""
        with pytest.raises((ValueError, SettingValidationError)):
            create_test_setting(
                related_entity_id="not-a-uuid",
                user_id=test_user_id
            )

    def test_invalid_user_id(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Validate user IDs must be valid UUIDs."""
        with pytest.raises((ValueError, SettingValidationError)):
            create_test_setting(
                related_entity_id=test_entity_id,
                user_id="not-a-uuid"
            )


class TestSettingHistoryTracking:
    """Test suite for SCD-2 history tracking."""

    def test_history_entry_on_insert(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Verify history entry is created on insert with action='I'."""
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        
        # Check history table
        history_rows = db_with_tables.fetchall(
            query="""
                SELECT setting_id, action, version_no, is_current
                FROM settings_history
                WHERE setting_id = %s
                ORDER BY version_no
            """,
            params=(setting.setting_id,),
        )
        
        assert len(history_rows) == 1
        assert history_rows[0]["action"] == "I"
        assert history_rows[0]["version_no"] == 1
        assert history_rows[0]["is_current"] is True

    def test_history_entry_on_update(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Verify history entries on update with proper versioning."""
        # Create initial setting
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        setting_id = setting.setting_id

        # Update the setting using the same object/ID
        setting.setting_value = "light"
        setting.row_checksum = setting.calculate_checksum()
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        
        # Check history table
        history_rows = db_with_tables.fetchall(
            query="""
                SELECT action, version_no, is_current, setting_value
                FROM settings_history
                WHERE setting_id = %s
                ORDER BY version_no
            """,
            params=(setting_id,),
        )
        
        assert len(history_rows) == 2
        # First version (insert)
        assert history_rows[0]["action"] == "I"
        assert history_rows[0]["version_no"] == 1
        assert history_rows[0]["is_current"] is False  # Closed
        assert history_rows[0]["setting_value"] == "dark"
        # Second version (update)
        assert history_rows[1]["action"] == "U"
        assert history_rows[1]["version_no"] == 2
        assert history_rows[1]["is_current"] is True  # Current
        assert history_rows[1]["setting_value"] == "light"

    def test_history_entry_on_delete(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Verify history entry on delete with action='D'."""
        # Create a setting and persist it
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        setting_id = setting.setting_id

        # Mark for deletion via manager and flush
        setting_mgr.delete_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        assert setting_mgr.flush() is True
        
        # Check history table
        history_rows = db_with_tables.fetchall(
            query="""
                SELECT action, version_no, is_current
                FROM settings_history
                WHERE setting_id = %s
                ORDER BY version_no
            """,
            params=(setting_id,),
        )
        
        assert len(history_rows) == 2
        # Insert version
        assert history_rows[0]["action"] == "I"
        assert history_rows[0]["version_no"] == 1
        assert history_rows[0]["is_current"] is False
        # Delete version
        assert history_rows[1]["action"] == "D"
        assert history_rows[1]["version_no"] == 2
        assert history_rows[1]["is_current"] is True

    def test_noop_update_does_not_create_new_history(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Ensure no-op updates do not touch settings/history.

        Creates and flushes an initial setting, then performs a second flush
        where the setting value (and therefore row_checksum) is unchanged.
        Verifies that the settings row is unchanged and that no additional
        history rows are created beyond the initial insert.
        """
        # Initial insert via cache + flush
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True
        setting_id = setting.setting_id

        # Capture baseline settings row and history count
        base_rows_before = db_with_tables.fetchall(
            query=(
                "SELECT setting_value, row_checksum FROM settings "
                "WHERE setting_id = %s"
            ),
            params=(setting_id,),
        )
        assert len(base_rows_before) == 1
        history_rows_before = db_with_tables.fetchall(
            query=(
                "SELECT action, version_no, is_current FROM settings_history "
                "WHERE setting_id = %s ORDER BY version_no"
            ),
            params=(setting_id,),
        )
        assert len(history_rows_before) == 1
        assert history_rows_before[0]["action"] == "I"
        assert history_rows_before[0]["is_current"] is True

        # Perform a no-op "update" by writing the same value/checksum
        # back into the cache and flushing again.
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True

        # Verify base row unchanged
        base_rows_after = db_with_tables.fetchall(
            query=(
                "SELECT setting_value, row_checksum FROM settings "
                "WHERE setting_id = %s"
            ),
            params=(setting_id,),
        )
        assert base_rows_after == base_rows_before

        # Verify no additional history rows were created
        history_rows_after = db_with_tables.fetchall(
            query=(
                "SELECT action, version_no, is_current FROM settings_history "
                "WHERE setting_id = %s ORDER BY version_no"
            ),
            params=(setting_id,),
        )
        assert history_rows_after == history_rows_before


class TestSettingEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_large_setting_value(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Handle large setting values."""
        large_value = "x" * 1000
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value=large_value,
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True

        rows = db_with_tables.fetchall(
            query=(
                "SELECT setting_value FROM settings WHERE setting_id = %s"
            ),
            params=(setting.setting_id,),
        )
        assert len(rows) == 1
        assert rows[0]["setting_value"] == large_value

    def test_special_characters_in_value(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Handle special characters in setting values."""
        special_value = "Test with 'quotes', \"double quotes\", and symbols: @#$%^&*()"
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value=special_value,
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True

        rows = db_with_tables.fetchall(
            query=(
                "SELECT setting_value FROM settings WHERE setting_id = %s"
            ),
            params=(setting.setting_id,),
        )
        assert len(rows) == 1
        assert rows[0]["setting_value"] == special_value

    def test_unicode_in_value(
        self,
        setting_mgr: SettingManager,
        db_with_tables: DatabaseManager,
        test_entity_id: str,
        test_user_id: str,
    ) -> None:
        """Test objective: Handle Unicode characters in setting values."""
        unicode_value = "日本語 Español Français 中文 🎉"
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value=unicode_value,
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        global_setting_cache.set(
            "USRTHM",
            test_entity_id,
            SettingCacheEntry(setting),
        )
        assert setting_mgr.flush() is True

        rows = db_with_tables.fetchall(
            query=(
                "SELECT setting_value FROM settings WHERE setting_id = %s"
            ),
            params=(setting.setting_id,),
        )
        assert len(rows) == 1
        assert rows[0]["setting_value"] == unicode_value


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
