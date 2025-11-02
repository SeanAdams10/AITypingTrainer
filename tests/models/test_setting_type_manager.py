"""Unit tests for the SettingTypeManager class.

Covers CRUD operations, validation, SCD-2 history tracking, and error handling
for setting types using raw SQL with DatabaseManager.
"""

import uuid

import pytest

from db.database_manager import DatabaseManager
from models.setting_type import SettingType, SettingTypeNotFound, SettingTypeValidationError
from models.setting_type_manager import SettingTypeManager


@pytest.fixture(scope="function")
def setting_type_manager(
    db_with_tables: DatabaseManager,
) -> SettingTypeManager:
    """Fixture: Provides a SettingTypeManager with a fresh, initialized database."""
    return SettingTypeManager(db_manager=db_with_tables)


@pytest.fixture(scope="function")
def test_user_id() -> uuid.UUID:
    """Fixture: Provides a consistent test user ID."""
    return uuid.UUID("a287befc-0570-4eb3-a5d7-46653054cf0f")


@pytest.fixture(scope="function")
def sample_setting_type(test_user_id: uuid.UUID) -> SettingType:
    """Fixture: Provides a sample SettingType for testing."""
    return SettingType(
        setting_type_id="USRTHM",
        setting_type_name="User Theme",
        description="User's preferred theme",
        related_entity_type="user",
        data_type="string",
        default_value="light",
        validation_rules='{"enum": ["light", "dark", "auto"]}',
        is_system=False,
        is_active=True,
        created_user_id=str(test_user_id),
        updated_user_id=str(test_user_id),
    )


class TestSettingTypeManagerCreate:
    """Tests for creating setting types."""

    def test_create_setting_type_success(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test successfully creating a new setting type."""
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        assert created.setting_type_id == "USRTHM"
        assert created.setting_type_name == "User Theme"
        assert created.data_type == "string"
        assert created.is_active is True
        assert created.created_dt is not None
        assert created.updated_dt is not None
        assert created.row_checksum is not None

    def test_create_setting_type_with_history(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that creating a setting type creates initial history entry."""
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )
        assert created.setting_type_id == "USRTHM"

        # Get history
        history = setting_type_manager.get_setting_type_history(
            setting_type_id="USRTHM"
        )

        assert len(history) == 1
        assert history[0]["action"] == "I"
        assert history[0]["version_no"] == 1
        assert history[0]["is_current"] is True
        assert history[0]["setting_type_id"] == "USRTHM"

    def test_create_duplicate_setting_type_fails(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that creating a duplicate setting type raises error."""
        # Create first time
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )
        assert created is not None

        # Try to create again
        with pytest.raises(SettingTypeValidationError, match="already exists"):
            setting_type_manager.create_setting_type(
                setting_type=sample_setting_type,
                user_id=test_user_id,
            )

    def test_create_setting_type_all_data_types(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test creating setting types with all valid data types."""
        data_types = ["string", "integer", "boolean", "decimal"]

        for idx, data_type in enumerate(data_types):
            setting_type = SettingType(
                setting_type_id=f"TEST0{idx+1}",
                setting_type_name=f"Test {data_type}",
                description=f"Test {data_type} type",
                related_entity_type="user",
                data_type=data_type,
                created_user_id=str(test_user_id),
                updated_user_id=str(test_user_id),
            )

            created = setting_type_manager.create_setting_type(
                setting_type=setting_type,
                user_id=test_user_id,
            )

            assert created.data_type == data_type

    def test_create_setting_type_all_entity_types(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test creating setting types with all valid entity types."""
        entity_types = ["user", "keyboard", "global"]

        for idx, entity_type in enumerate(entity_types):
            setting_type = SettingType(
                setting_type_id=f"ENT00{idx+1}",
                setting_type_name=f"Test {entity_type}",
                description=f"Test {entity_type} entity",
                related_entity_type=entity_type,
                data_type="string",
                created_user_id=str(test_user_id),
                updated_user_id=str(test_user_id),
            )

            created = setting_type_manager.create_setting_type(
                setting_type=setting_type,
                user_id=test_user_id,
            )

            assert created.related_entity_type == entity_type


class TestSettingTypeManagerRead:
    """Tests for reading setting types."""

    def test_get_setting_type_success(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test successfully retrieving a setting type."""
        # Create first
        setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Retrieve
        retrieved = setting_type_manager.get_setting_type(setting_type_id="USRTHM")

        assert retrieved is not None
        assert retrieved.setting_type_id == "USRTHM"
        assert retrieved.setting_type_name == "User Theme"
        assert retrieved.data_type == "string"

    def test_get_setting_type_not_found(
        self,
        setting_type_manager: SettingTypeManager,
    ) -> None:
        """Test retrieving a non-existent setting type returns None."""
        retrieved = setting_type_manager.get_setting_type(setting_type_id="NOTFND")
        assert retrieved is None

    def test_list_setting_types_empty(
        self,
        setting_type_manager: SettingTypeManager,
    ) -> None:
        """Test listing setting types when none exist."""
        types = setting_type_manager.list_setting_types()
        assert types == []

    def test_list_setting_types_all(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test listing all setting types."""
        # Create multiple types
        for i in range(3):
            setting_type = SettingType(
                setting_type_id=f"TYPE0{i+1}",
                setting_type_name=f"Type {i+1}",
                description=f"Description {i+1}",
                related_entity_type="user",
                data_type="string",
                created_user_id=str(test_user_id),
                updated_user_id=str(test_user_id),
            )
            setting_type_manager.create_setting_type(
                setting_type=setting_type,
                user_id=test_user_id,
            )

        types = setting_type_manager.list_setting_types()
        assert len(types) == 3

    def test_list_setting_types_filtered_by_entity_type(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test listing setting types filtered by entity type."""
        # Create types for different entities
        entities = ["user", "keyboard", "global"]
        for idx, entity in enumerate(entities):
            setting_type = SettingType(
                setting_type_id=f"ENT00{idx+1}",
                setting_type_name=f"{entity} Type",
                description=f"{entity} setting",
                related_entity_type=entity,
                data_type="string",
                created_user_id=str(test_user_id),
                updated_user_id=str(test_user_id),
            )
            setting_type_manager.create_setting_type(
                setting_type=setting_type,
                user_id=test_user_id,
            )

        # Filter by user
        user_types = setting_type_manager.list_setting_types(entity_type="user")
        assert len(user_types) == 1
        assert user_types[0].related_entity_type == "user"

        # Filter by keyboard
        keyboard_types = setting_type_manager.list_setting_types(entity_type="keyboard")
        assert len(keyboard_types) == 1
        assert keyboard_types[0].related_entity_type == "keyboard"

    def test_list_setting_types_active_only(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test listing only active setting types."""
        # Create active type
        active_type = SettingType(
            setting_type_id="ACTIVE",
            setting_type_name="Active Type",
            description="Active setting",
            related_entity_type="user",
            data_type="string",
            is_active=True,
            created_user_id=str(test_user_id),
            updated_user_id=str(test_user_id),
        )
        setting_type_manager.create_setting_type(
            setting_type=active_type,
            user_id=test_user_id,
        )

        # Create inactive type
        inactive_type = SettingType(
            setting_type_id="INACTV",
            setting_type_name="Inactive Type",
            description="Inactive setting",
            related_entity_type="user",
            data_type="string",
            is_active=False,
            created_user_id=str(test_user_id),
            updated_user_id=str(test_user_id),
        )
        setting_type_manager.create_setting_type(
            setting_type=inactive_type,
            user_id=test_user_id,
        )

        # List active only
        active_types = setting_type_manager.list_setting_types(active_only=True)
        assert len(active_types) == 1
        assert active_types[0].setting_type_id == "ACTIVE"

        # List all
        all_types = setting_type_manager.list_setting_types(active_only=False)
        assert len(all_types) == 2


class TestSettingTypeManagerUpdate:
    """Tests for updating setting types."""

    def test_update_setting_type_success(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test successfully updating a setting type."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Capture original timestamp before update
        original_updated_dt = created.updated_dt
        
        # Update
        created.description = "Updated description"
        updated = setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        assert updated.description == "Updated description"
        assert updated.updated_dt != original_updated_dt

    def test_update_setting_type_creates_history(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that updating creates new history entry."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Update
        created.description = "Updated description"
        setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        # Check history
        history = setting_type_manager.get_setting_type_history(setting_type_id="USRTHM")
        assert len(history) == 2
        assert history[0]["action"] == "I"
        assert history[0]["version_no"] == 1
        assert history[0]["is_current"] is False  # Closed
        assert history[1]["action"] == "U"
        assert history[1]["version_no"] == 2
        assert history[1]["is_current"] is True  # Current

    def test_update_setting_type_no_op_detection(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that no-op updates don't create history."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Update with same values (no-op)
        updated = setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )
        assert updated.setting_type_id == created.setting_type_id

        # History should still be 1 entry
        history = setting_type_manager.get_setting_type_history(
            setting_type_id="USRTHM"
        )
        assert len(history) == 1

    def test_update_setting_type_not_found(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test updating non-existent setting type raises error."""
        with pytest.raises(SettingTypeNotFound, match="not found"):
            setting_type_manager.update_setting_type(
                setting_type=sample_setting_type,
                user_id=test_user_id,
            )

    def test_update_system_setting_type_fails(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that system setting types cannot be updated."""
        # Create system type
        system_type = SettingType(
            setting_type_id="SYSTEM",
            setting_type_name="System Type",
            description="System setting",
            related_entity_type="global",
            data_type="string",
            is_system=True,
            created_user_id=str(test_user_id),
            updated_user_id=str(test_user_id),
        )
        created = setting_type_manager.create_setting_type(
            setting_type=system_type,
            user_id=test_user_id,
        )

        # Try to update
        created.description = "Updated"
        with pytest.raises(SettingTypeValidationError, match="Cannot modify system"):
            setting_type_manager.update_setting_type(
                setting_type=created,
                user_id=test_user_id,
            )

    def test_update_multiple_fields(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test updating multiple fields at once."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Update multiple fields
        created.setting_type_name = "Updated Theme"
        created.description = "Updated description"
        created.default_value = "dark"
        created.validation_rules = '{"enum": ["light", "dark"]}'

        updated = setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        assert updated.setting_type_name == "Updated Theme"
        assert updated.description == "Updated description"
        assert updated.default_value == "dark"
        assert '"enum"' in updated.validation_rules


class TestSettingTypeManagerDelete:
    """Tests for deleting setting types."""

    def test_delete_setting_type_success(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test successfully deleting (soft delete) a setting type."""
        # Create
        setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Delete
        result = setting_type_manager.delete_setting_type(
            setting_type_id="USRTHM",
            user_id=test_user_id,
        )

        assert result is True

        # Verify soft delete (is_active = False)
        deleted = setting_type_manager.get_setting_type(setting_type_id="USRTHM")
        assert deleted is not None
        assert deleted.is_active is False

    def test_delete_setting_type_creates_history(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that deleting creates delete history entry."""
        # Create
        setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Delete
        setting_type_manager.delete_setting_type(
            setting_type_id="USRTHM",
            user_id=test_user_id,
        )

        # Check history
        history = setting_type_manager.get_setting_type_history(setting_type_id="USRTHM")
        assert len(history) == 2
        assert history[0]["action"] == "I"
        assert history[1]["action"] == "D"
        assert history[1]["is_current"] is True

    def test_delete_setting_type_not_found(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test deleting non-existent setting type raises error."""
        with pytest.raises(SettingTypeNotFound, match="not found"):
            setting_type_manager.delete_setting_type(
                setting_type_id="NOTFND",
                user_id=test_user_id,
            )

    def test_delete_system_setting_type_fails(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that system setting types cannot be deleted."""
        # Create system type
        system_type = SettingType(
            setting_type_id="SYSTEM",
            setting_type_name="System Type",
            description="System setting",
            related_entity_type="global",
            data_type="string",
            is_system=True,
            created_user_id=str(test_user_id),
            updated_user_id=str(test_user_id),
        )
        setting_type_manager.create_setting_type(
            setting_type=system_type,
            user_id=test_user_id,
        )

        # Try to delete
        with pytest.raises(SettingTypeValidationError, match="Cannot delete system"):
            setting_type_manager.delete_setting_type(
                setting_type_id="SYSTEM",
                user_id=test_user_id,
            )


class TestSettingTypeManagerHistory:
    """Tests for history tracking."""

    def test_get_history_empty(
        self,
        setting_type_manager: SettingTypeManager,
    ) -> None:
        """Test getting history for non-existent setting type."""
        history = setting_type_manager.get_setting_type_history(setting_type_id="NOTFND")
        assert history == []

    def test_get_history_complete_lifecycle(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test complete lifecycle: create, update, update, delete."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Update 1
        created.description = "First update"
        setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        # Update 2
        created.description = "Second update"
        setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        # Delete
        setting_type_manager.delete_setting_type(
            setting_type_id="USRTHM",
            user_id=test_user_id,
        )

        # Check history
        history = setting_type_manager.get_setting_type_history(setting_type_id="USRTHM")
        assert len(history) == 4

        # Verify sequence
        assert history[0]["action"] == "I"
        assert history[0]["version_no"] == 1
        assert history[0]["is_current"] is False

        assert history[1]["action"] == "U"
        assert history[1]["version_no"] == 2
        assert history[1]["is_current"] is False

        assert history[2]["action"] == "U"
        assert history[2]["version_no"] == 3
        assert history[2]["is_current"] is False

        assert history[3]["action"] == "D"
        assert history[3]["version_no"] == 4
        assert history[3]["is_current"] is True

    def test_history_version_incrementing(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that version numbers increment correctly."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Multiple updates
        for i in range(5):
            created.description = f"Update {i+1}"
            setting_type_manager.update_setting_type(
                setting_type=created,
                user_id=test_user_id,
            )

        # Check versions
        history = setting_type_manager.get_setting_type_history(setting_type_id="USRTHM")
        assert len(history) == 6  # 1 create + 5 updates

        for idx, entry in enumerate(history):
            assert entry["version_no"] == idx + 1

    def test_history_current_flag_management(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that only the latest version is marked as current."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Update
        created.description = "Updated"
        setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        # Check that only latest is current
        history = setting_type_manager.get_setting_type_history(setting_type_id="USRTHM")
        current_count = sum(1 for h in history if h["is_current"])
        assert current_count == 1
        assert history[-1]["is_current"] is True


class TestSettingTypeManagerEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_create_with_minimal_fields(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test creating with only required fields."""
        minimal_type = SettingType(
            setting_type_id="MINMAL",
            setting_type_name="Minimal",
            description="Minimal setting",
            related_entity_type="user",
            data_type="string",
            created_user_id=str(test_user_id),
            updated_user_id=str(test_user_id),
        )

        created = setting_type_manager.create_setting_type(
            setting_type=minimal_type,
            user_id=test_user_id,
        )

        assert created.setting_type_id == "MINMAL"
        assert created.default_value is None
        assert created.validation_rules is None

    def test_create_with_all_fields(
        self,
        setting_type_manager: SettingTypeManager,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test creating with all optional fields populated."""
        full_type = SettingType(
            setting_type_id="FULLTY",
            setting_type_name="Full Type",
            description="Full setting with all fields",
            related_entity_type="keyboard",
            data_type="integer",
            default_value="100",
            validation_rules='{"minimum": 0, "maximum": 200}',
            is_system=True,
            is_active=True,
            created_user_id=str(test_user_id),
            updated_user_id=str(test_user_id),
        )

        created = setting_type_manager.create_setting_type(
            setting_type=full_type,
            user_id=test_user_id,
        )

        assert created.setting_type_id == "FULLTY"
        assert created.default_value == "100"
        assert created.validation_rules is not None
        assert created.is_system is True

    def test_concurrent_updates_version_tracking(
        self,
        setting_type_manager: SettingTypeManager,
        sample_setting_type: SettingType,
        test_user_id: uuid.UUID,
    ) -> None:
        """Test that concurrent-style updates maintain proper versioning."""
        # Create
        created = setting_type_manager.create_setting_type(
            setting_type=sample_setting_type,
            user_id=test_user_id,
        )

        # Simulate concurrent updates (sequential in test)
        created.description = "Update A"
        setting_type_manager.update_setting_type(
            setting_type=created,
            user_id=test_user_id,
        )

        # Get fresh copy
        fresh = setting_type_manager.get_setting_type(setting_type_id="USRTHM")
        assert fresh is not None
        fresh.description = "Update B"
        setting_type_manager.update_setting_type(
            setting_type=fresh,
            user_id=test_user_id,
        )

        # Verify versions
        history = setting_type_manager.get_setting_type_history(setting_type_id="USRTHM")
        assert len(history) == 3
        assert history[0]["version_no"] == 1
        assert history[1]["version_no"] == 2
        assert history[2]["version_no"] == 3
