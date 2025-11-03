"""Unit tests for models.setting_manager.SettingManager.

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


@pytest.fixture(scope="function")
def setting_type_mgr(db_with_tables: DatabaseManager) -> Generator[SettingTypeManager, None, None]:
    """Fixture: Provides a SettingTypeManager for creating setting types."""
    assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER
    manager = SettingTypeManager(db_manager=db_with_tables)
    yield manager


@pytest.fixture(scope="function")
def setting_mgr(
    db_with_tables: DatabaseManager,
    setting_type_mgr: SettingTypeManager
) -> Generator[SettingManager, None, None]:
    """Fixture: Provides a SettingManager with a fresh, initialized database.
    
    Test objective: Ensure database connection is Docker PostgreSQL for safety.
    Creates common setting types for testing.
    """
    assert db_with_tables.connection_type == ConnectionType.POSTGRESS_DOCKER
    
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
    
    manager = SettingManager(db_manager=db_with_tables)
    yield manager


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
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Create a new setting and verify persistence."""
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        
        result = setting_mgr.save_setting(setting=setting)
        assert result is True
        assert setting.setting_id is not None
        
        # Verify it's in the DB
        retrieved = setting_mgr.get_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        assert retrieved.setting_value == "dark"
        assert retrieved.setting_type_id == "USRTHM"

    def test_save_setting_update_existing(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Update an existing setting and verify the change."""
        # Create initial setting
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        original_id = setting.setting_id
        
        # Update the value
        setting2 = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="light",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting2)
        
        # Verify update
        retrieved = setting_mgr.get_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        assert retrieved.setting_value == "light"
        # Should have same ID (update, not insert)
        assert retrieved.setting_id == original_id

    def test_get_setting_existing(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Retrieve an existing setting by type and entity."""
        setting = create_test_setting(
            setting_type_id="USRLNG",
            setting_value="en",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        
        retrieved = setting_mgr.get_setting(
            setting_type_id="USRLNG",
            related_entity_id=test_entity_id
        )
        assert retrieved.setting_value == "en"
        assert retrieved.setting_type_id == "USRLNG"
        assert retrieved.related_entity_id == test_entity_id

    def test_get_setting_not_found(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Attempt to retrieve a non-existent setting."""
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(
                setting_type_id="NOTFND",
                related_entity_id=test_entity_id
            )

    def test_get_setting_with_default(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Retrieve setting with default value when not found."""
        setting = setting_mgr.get_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id,
            default_value="auto"
        )
        
        # Should return a new setting with default value (not saved to DB)
        assert setting.setting_value == "auto"
        assert setting.setting_type_id == "USRTHM"
        assert setting.related_entity_id == test_entity_id
        
        # Verify it's NOT in the database yet
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(
                setting_type_id="USRTHM",
                related_entity_id=test_entity_id
            )

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
            setting_mgr.save_setting(setting=setting)
        
        # List all settings
        settings = setting_mgr.list_settings(related_entity_id=test_entity_id)
        assert len(settings) == 3
        
        # Verify all are for the same entity
        assert all(s.related_entity_id == test_entity_id for s in settings)
        
        # Verify type IDs
        retrieved_types = sorted([s.setting_type_id for s in settings])
        assert retrieved_types == sorted(setting_types)

    def test_delete_setting_existing(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Delete an existing setting."""
        # Create a setting
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        
        # Delete it
        result = setting_mgr.delete_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        assert result is True
        
        # Verify it's gone
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(
                setting_type_id="USRTHM",
                related_entity_id=test_entity_id
            )

    def test_delete_setting_not_found(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Attempt to delete a non-existent setting."""
        result = setting_mgr.delete_setting(
            setting_type_id="NOTFND",
            related_entity_id=test_entity_id
        )
        assert result is False

    def test_delete_all_settings_for_entity(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Delete all settings for a specific entity."""
        # Create multiple settings
        setting_types = ["TYPE01", "TYPE02", "TYPE03"]
        for type_id in setting_types:
            setting = create_test_setting(
                setting_type_id=type_id,
                setting_value=f"value_{type_id}",
                related_entity_id=test_entity_id,
                user_id=test_user_id,
            )
            setting_mgr.save_setting(setting=setting)
        
        # Verify they exist
        settings = setting_mgr.list_settings(related_entity_id=test_entity_id)
        assert len(settings) == 3
        
        # Delete all
        result = setting_mgr.delete_all_settings_for_entity(
            related_entity_id=test_entity_id
        )
        assert result is True
        
        # Verify all are gone
        settings = setting_mgr.list_settings(related_entity_id=test_entity_id)
        assert len(settings) == 0

    def test_delete_all_settings_for_entity_empty(
        self, setting_mgr: SettingManager, test_entity_id: str
    ) -> None:
        """Test objective: Delete all settings when none exist."""
        result = setting_mgr.delete_all_settings_for_entity(
            related_entity_id=test_entity_id
        )
        assert result is False


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
        setting_mgr.save_setting(setting=setting)
        
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
        setting_mgr.save_setting(setting=setting)
        setting_id = setting.setting_id
        
        # Update the setting
        setting2 = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="light",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting2)
        
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
        # Create a setting
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value="dark",
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        setting_id = setting.setting_id
        
        # Delete it
        setting_mgr.delete_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        
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


class TestSettingEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_large_setting_value(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Handle large setting values."""
        large_value = "x" * 1000
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value=large_value,
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        
        retrieved = setting_mgr.get_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        assert retrieved.setting_value == large_value

    def test_special_characters_in_value(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Handle special characters in setting values."""
        special_value = "Test with 'quotes', \"double quotes\", and symbols: @#$%^&*()"
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value=special_value,
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        
        retrieved = setting_mgr.get_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        assert retrieved.setting_value == special_value

    def test_unicode_in_value(
        self, setting_mgr: SettingManager, test_entity_id: str, test_user_id: str
    ) -> None:
        """Test objective: Handle Unicode characters in setting values."""
        unicode_value = "日本語 Español Français 中文 🎉"
        setting = create_test_setting(
            setting_type_id="USRTHM",
            setting_value=unicode_value,
            related_entity_id=test_entity_id,
            user_id=test_user_id,
        )
        setting_mgr.save_setting(setting=setting)
        
        retrieved = setting_mgr.get_setting(
            setting_type_id="USRTHM",
            related_entity_id=test_entity_id
        )
        assert retrieved.setting_value == unicode_value


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
