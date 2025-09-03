"""Unit tests for models.setting_manager.SettingManager.

Covers CRUD, validation (including DB uniqueness), history tracking, and error handling.
"""

import uuid
from datetime import datetime, timezone

import pytest

from db.database_manager import DatabaseManager
from models.setting import Setting, SettingNotFound, SettingValidationError
from models.setting_manager import SettingManager


@pytest.fixture(scope="function")
def setting_mgr(db_with_tables: DatabaseManager) -> SettingManager:
    """Fixture: Provides a SettingManager with a fresh, initialized database."""
    return SettingManager(db_with_tables)


class TestSettingManager:
    """Test suite for SettingManager covering all CRUD, validation logic and history tracking."""

    def test_create_setting_valid(self, setting_mgr: SettingManager) -> None:
        """Test objective: Create a setting with valid data and verify persistence."""
        setting_type_id = "SETTYP"
        related_entity_id = str(uuid.uuid4())
        setting_value = "test value"

        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        assert setting_mgr.save_setting(setting)
        assert setting.setting_type_id == setting_type_id
        assert setting.setting_value == setting_value
        assert isinstance(setting.setting_id, str)

        # Verify it's in the DB
        retrieved_setting = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert retrieved_setting.setting_type_id == setting_type_id
        assert retrieved_setting.setting_value == setting_value
        assert retrieved_setting.related_entity_id == related_entity_id

    @pytest.mark.parametrize(
        "setting_type_id, err_msg_part",
        [
            ("", "must be exactly 6 characters"),
            ("ABC", "must be exactly 6 characters"),
            ("ABCDEFG", "must be exactly 6 characters"),
            ("ABCD€Ω", "must be ASCII-only"),
        ],
    )
    def test_create_setting_invalid_format(
        self, setting_mgr: SettingManager, setting_type_id: str, err_msg_part: str
    ) -> None:
        """Test objective: Attempt to create a setting with an invalid type_id format."""
        with pytest.raises((ValueError, SettingValidationError)) as e:
            setting = Setting(
                setting_type_id=setting_type_id,
                setting_value="test value",
                related_entity_id=str(uuid.uuid4()),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)
        assert err_msg_part.lower() in str(e.value).lower()

    def test_update_existing_setting_with_new_value(self, setting_mgr: SettingManager) -> None:
        """Test objective: Verify that saving a setting with an existing type_id and entity_id updates

        the setting value and creates a new history entry.
        """
        setting_type_id = "UPDSET"
        related_entity_id = str(uuid.uuid4())
        initial_value = "initial value"
        updated_value = "updated value"

        # Create initial setting
        setting1 = Setting(
            setting_type_id=setting_type_id,
            setting_value=initial_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting1)
        original_setting_id = setting1.setting_id

        # Save a new setting with the same type_id and entity_id but different value
        setting2 = Setting(
            setting_type_id=setting_type_id,
            setting_value=updated_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting2)

        # Verify the setting was updated, not duplicated
        updated_setting = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert updated_setting.setting_value == updated_value
        assert updated_setting.setting_id == original_setting_id

        # Check history table for both entries
        history_rows = setting_mgr.db_manager.execute(
            """SELECT setting_id, setting_value FROM settings_history
            WHERE setting_type_id = ? ORDER BY updated_at
            """,
            (setting_type_id,),
        ).fetchall()

        # Should have two history entries with the same setting_id but different values
        assert len(history_rows) == 2
        assert history_rows[0][0] == original_setting_id
        assert history_rows[0][1] == initial_value
        assert history_rows[1][0] == original_setting_id
        assert history_rows[1][1] == updated_value

    def test_get_setting_by_type_and_entity(self, setting_mgr: SettingManager) -> None:
        """Test objective: Retrieve a setting by its type_id and related_entity_id."""
        setting_type_id = "GETSET"
        related_entity_id = str(uuid.uuid4())
        setting_value = "test retrieve"

        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        retrieved = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert retrieved is not None
        assert retrieved.setting_id == setting.setting_id
        assert retrieved.setting_type_id == setting_type_id
        assert retrieved.setting_value == setting_value
        assert retrieved.related_entity_id == related_entity_id

    def test_get_setting_with_default(self, setting_mgr: SettingManager) -> None:
        """Test objective: Test get_setting with a default value when setting doesn't exist."""
        setting_type_id = "DEFVAL"
        related_entity_id = str(uuid.uuid4())
        default_value = "default value"

        # Get with default - should return a new setting with the default value
        setting = setting_mgr.get_setting(setting_type_id, related_entity_id, default_value)
        assert setting.setting_type_id == setting_type_id
        assert setting.setting_value == default_value
        assert setting.related_entity_id == related_entity_id

        # Setting should not be saved to DB yet
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(setting_type_id, related_entity_id)

        # Now save the setting
        setting_mgr.save_setting(setting)

        # Should be able to retrieve it now
        retrieved = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert retrieved.setting_value == default_value

    def test_get_setting_not_found(self, setting_mgr: SettingManager) -> None:
        """Test objective: Attempt to retrieve a non-existent setting."""
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting("NOTEXS", str(uuid.uuid4()))

    def test_list_settings_empty(self, setting_mgr: SettingManager) -> None:
        """Test objective: List settings for an entity when none exist."""
        settings = setting_mgr.list_settings(str(uuid.uuid4()))
        assert len(settings) == 0

    def test_list_settings_populated(self, setting_mgr: SettingManager) -> None:
        """Test objective: List settings for an entity with multiple settings."""
        related_entity_id = str(uuid.uuid4())

        # Create three settings for the same entity
        setting_types = ["TYPE01", "TYPE02", "TYPE03"]
        for type_id in setting_types:
            setting = Setting(
                setting_type_id=type_id,
                setting_value=f"value for {type_id}",
                related_entity_id=related_entity_id,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)

        # List settings for the entity
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 3

        # Verify type_ids
        type_ids = [s.setting_type_id for s in settings]
        assert sorted(type_ids) == sorted(setting_types)

    def test_update_setting_value(self, setting_mgr: SettingManager) -> None:
        """Test objective: Update a setting's value using save_setting."""
        setting_type_id = "UPDATE"
        related_entity_id = str(uuid.uuid4())
        original_value = "original"
        new_value = "updated"

        # Create initial setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=original_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Change the value and save
        setting.setting_value = new_value
        assert setting_mgr.save_setting(setting)

        # Verify the update
        updated = setting_mgr.get_setting(setting_type_id, related_entity_id)
        assert updated.setting_value == new_value

    def test_history_tracking_on_create(self, setting_mgr: SettingManager) -> None:
        """Test objective: Verify history record is created when a setting is created."""
        setting_type_id = "HISCRE"
        related_entity_id = str(uuid.uuid4())
        setting_value = "history test create"

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Check history table
        history_rows = setting_mgr.db_manager.execute(
            """SELECT setting_id, setting_type_id, setting_value
            FROM settings_history
            WHERE setting_type_id = ?""",
            (setting_type_id,),
        ).fetchall()

        assert len(history_rows) == 1
        assert history_rows[0][0] == setting.setting_id
        assert history_rows[0][1] == setting_type_id
        assert history_rows[0][2] == setting_value

    def test_history_tracking_on_update(self, setting_mgr: SettingManager) -> None:
        """Test objective: Verify history records are created when a setting is updated."""
        setting_type_id = "HISUPD"
        related_entity_id = str(uuid.uuid4())
        values = ["original", "update 1", "update 2"]

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=values[0],
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Update the setting twice
        for value in values[1:]:
            setting.setting_value = value
            setting_mgr.save_setting(setting)

        # Check history table
        history_rows = setting_mgr.db_manager.execute(
            """
            SELECT setting_value FROM settings_history
            WHERE setting_type_id = ?
            ORDER BY updated_at
            """,
            (setting_type_id,),
        ).fetchall()

        assert len(history_rows) == 3
        for i, row in enumerate(history_rows):
            assert row[0] == values[i]

    def test_history_tracking_on_delete(self, setting_mgr: SettingManager) -> None:
        """Test objective: Verify history record is created when a setting is deleted."""
        setting_type_id = "HISDEL"
        related_entity_id = str(uuid.uuid4())
        setting_value = "delete me"

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Delete the setting
        setting_mgr.delete_setting(setting_type_id, related_entity_id)

        # Check history table - should have two entries
        history_rows = setting_mgr.db_manager.execute(
            "SELECT setting_value FROM settings_history WHERE setting_type_id = ?",
            (setting_type_id,),
        ).fetchall()

        assert len(history_rows) == 2
        assert history_rows[0][0] == setting_value  # Creation record
        assert history_rows[1][0] == setting_value  # Deletion record

    def test_delete_setting(self, setting_mgr: SettingManager) -> None:
        """Test objective: Delete an existing setting."""
        setting_type_id = "DELETE"
        related_entity_id = str(uuid.uuid4())

        # Create a setting
        setting = Setting(
            setting_type_id=setting_type_id,
            setting_value="to delete",
            related_entity_id=related_entity_id,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        setting_mgr.save_setting(setting)

        # Delete the setting
        assert setting_mgr.delete_setting(setting_type_id, related_entity_id) is True

        # Verify it's gone
        with pytest.raises(SettingNotFound):
            setting_mgr.get_setting(setting_type_id, related_entity_id)

    def test_delete_nonexistent_setting(self, setting_mgr: SettingManager) -> None:
        """Test objective: Attempt to delete a non-existent setting."""
        assert setting_mgr.delete_setting("NOEXST", str(uuid.uuid4())) is False

    def test_delete_all_settings(self, setting_mgr: SettingManager) -> None:
        """Test objective: Delete all settings for an entity and verify the action."""
        related_entity_id = str(uuid.uuid4())

        # Create multiple settings for the entity
        for i, type_id in enumerate(["TYPE01", "TYPE02", "TYPE03"]):
            setting = Setting(
                setting_type_id=type_id,
                setting_value=f"value {i}",
                related_entity_id=related_entity_id,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)

        # Check that all settings exist
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 3

        # Delete all settings for the entity
        assert setting_mgr.delete_all_settings(related_entity_id) is True

        # Verify all are gone
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 0

        # Verify history entries were created for each deletion
        history_rows = setting_mgr.db_manager.execute(
            "SELECT setting_type_id FROM settings_history WHERE related_entity_id = ?",
            (related_entity_id,),
        ).fetchall()

        # Should have 6 entries: 3 for creation and 3 for deletion
        assert len(history_rows) == 6

    def test_history_for_bulk_delete(self, setting_mgr: SettingManager) -> None:
        """Test objective: Verify history tracking for bulk deletion of settings."""
        related_entity_id = str(uuid.uuid4())
        setting_types = ["BULK01", "BULK02", "BULK03"]

        # Create multiple settings
        for type_id in setting_types:
            setting = Setting(
                setting_type_id=type_id,
                setting_value=f"bulk value for {type_id}",
                related_entity_id=related_entity_id,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            setting_mgr.save_setting(setting)

        # Delete all settings for the entity
        setting_mgr.delete_all_settings(related_entity_id)

        # Check that settings are gone
        settings = setting_mgr.list_settings(related_entity_id)
        assert len(settings) == 0

        # Check for history entries
        for type_id in setting_types:
            history_rows = setting_mgr.db_manager.execute(
                """
                SELECT updated_at FROM settings_history
                WHERE setting_type_id = ? AND related_entity_id = ?
                ORDER BY updated_at
                """,
                (type_id, related_entity_id),
            ).fetchall()

            # Should have 2 entries per setting: creation and deletion
            assert len(history_rows) == 2

            # The timestamps should be different (creation vs deletion)
            assert history_rows[0][0] != history_rows[1][0]


if __name__ == "__main__":
    pytest.main([__file__])
