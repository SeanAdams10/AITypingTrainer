"""Test fixtures for Settings system testing.

Provides shared test data, mock objects, and utilities for comprehensive testing.
"""

import json
import uuid
from typing import Dict, List, Optional
from unittest.mock import Mock

import pytest

from db.database_manager import DatabaseManager
from models.setting import Setting
from models.setting_type import SettingType
from models.settings_manager import SettingsManager


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager for testing without actual database."""
    mock = Mock(spec=DatabaseManager)
    mock.fetchall.return_value = []
    mock.fetchone.return_value = None
    mock.execute_many.return_value = True
    return mock


@pytest.fixture
def sample_setting_types() -> List[SettingType]:
    """Sample setting types for testing."""
    return [
        SettingType(
            setting_type_id="user.theme",
            setting_type_name="User Theme",
            description="User interface theme preference",
            related_entity_type="user",
            data_type="string",
            default_value="dark",
            validation_rules=json.dumps({"enum": ["light", "dark", "auto"]}),
            is_system=False,
            is_active=True,
            created_user_id="system",
            updated_user_id="system"
        ),
        SettingType(
            setting_type_id="user.language",
            setting_type_name="User Language",
            description="User's preferred language",
            related_entity_type="user",
            data_type="string",
            default_value="en",
            validation_rules=json.dumps({"enum": ["en", "es", "fr", "de"]}),
            is_system=False,
            is_active=True,
            created_user_id="system",
            updated_user_id="system"
        ),
        SettingType(
            setting_type_id="system.max_session_duration",
            setting_type_name="Maximum Session Duration",
            description="Maximum time a user session can remain active (minutes)",
            related_entity_type="system",
            data_type="integer",
            default_value="480",
            validation_rules=json.dumps({"minimum": 1, "maximum": 1440}),
            is_system=True,
            is_active=True,
            created_user_id="system",
            updated_user_id="system"
        ),
        SettingType(
            setting_type_id="user.notification_email",
            setting_type_name="Email Notifications",
            description="Enable email notifications for user",
            related_entity_type="user",
            data_type="boolean",
            default_value="true",
            validation_rules=json.dumps({"type": "boolean"}),
            is_system=False,
            is_active=True,
            created_user_id="system",
            updated_user_id="system"
        ),
        SettingType(
            setting_type_id="user.typing_speed_goal",
            setting_type_name="Typing Speed Goal",
            description="User's typing speed goal in WPM",
            related_entity_type="user",
            data_type="number",
            default_value="60.0",
            validation_rules=json.dumps({"minimum": 10.0, "maximum": 200.0}),
            is_system=False,
            is_active=True,
            created_user_id="system",
            updated_user_id="system"
        )
    ]


@pytest.fixture
def sample_settings(sample_setting_types) -> List[Setting]:
    """Sample settings for testing."""
    user_id = str(uuid.uuid4())
    return [
        Setting(
            setting_type_id="user.theme",
            setting_value="dark",
            related_entity_id=user_id,
            created_user_id="system",
            updated_user_id="system"
        ),
        Setting(
            setting_type_id="user.language",
            setting_value="en",
            related_entity_id=user_id,
            created_user_id="system",
            updated_user_id="system"
        ),
        Setting(
            setting_type_id="system.max_session_duration",
            setting_value="480",
            related_entity_id="system",
            created_user_id="system",
            updated_user_id="system"
        ),
        Setting(
            setting_type_id="user.notification_email",
            setting_value="true",
            related_entity_id=user_id,
            created_user_id=user_id,
            updated_user_id=user_id
        )
    ]


@pytest.fixture
def initialized_settings_manager(mock_db_manager, sample_setting_types, sample_settings):
    """Settings manager initialized with test data."""
    # Reset singleton
    SettingsManager.reset_instance()
    
    # Setup mock to return test data
    setting_type_rows = []
    for st in sample_setting_types:
        setting_type_rows.append({
            'setting_type_id': st.setting_type_id,
            'setting_type_name': st.setting_type_name,
            'description': st.description,
            'related_entity_type': st.related_entity_type,
            'data_type': st.data_type,
            'default_value': st.default_value,
            'validation_rules': st.validation_rules,
            'is_system': st.is_system,
            'is_active': st.is_active,
            'created_user_id': st.created_user_id,
            'updated_user_id': st.updated_user_id,
            'created_at': st.created_at.isoformat(),
            'updated_at': st.updated_at.isoformat(),
            'row_checksum': st.row_checksum
        })
    
    setting_rows = []
    for s in sample_settings:
        setting_rows.append({
            'setting_id': s.setting_id,
            'setting_type_id': s.setting_type_id,
            'setting_value': s.setting_value,
            'related_entity_id': s.related_entity_id,
            'created_user_id': s.created_user_id,
            'updated_user_id': s.updated_user_id,
            'created_at': s.created_at.isoformat(),
            'updated_at': s.updated_at.isoformat(),
            'row_checksum': s.row_checksum
        })
    
    def mock_fetchall(query: str, params: Optional[List[str]] = None) -> List[Dict[str, str]]:
        if "setting_types" in query:
            return setting_type_rows
        elif "settings" in query:
            return setting_rows
        return []
    
    mock_db_manager.fetchall.side_effect = mock_fetchall
    
    # Get instance and initialize
    manager = SettingsManager.get_instance()
    manager.initialize(mock_db_manager)
    
    yield manager
    
    # Cleanup
    SettingsManager.reset_instance()


@pytest.fixture
def user_id():
    """Sample user ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def admin_user_id():
    """Sample admin user ID for testing."""
    return "admin-" + str(uuid.uuid4())


@pytest.fixture
def system_user_id():
    """System user ID for testing."""
    return "system"


@pytest.fixture
def test_entity_ids():
    """Various entity IDs for testing."""
    return {
        'user1': str(uuid.uuid4()),
        'user2': str(uuid.uuid4()),
        'system': 'system',
        'organization': str(uuid.uuid4())
    }


class SettingsTestHelper:
    """Helper class with utility methods for settings testing."""
    
    @staticmethod
    def create_test_setting_type(setting_type_id: str, data_type: str = "string", 
                               is_system: bool = False, **kwargs: str) -> SettingType:
        """Create a test setting type with default values."""
        defaults = {
            'setting_type_name': f"Test {setting_type_id}",
            'description': f"Test setting type for {setting_type_id}",
            'related_entity_type': 'user',
            'data_type': data_type,
            'default_value': '""' if data_type == 'string' else '0',
            'validation_rules': '{}',
            'is_system': is_system,
            'is_active': True,
            'created_user_id': 'test',
            'updated_user_id': 'test'
        }
        defaults.update(kwargs)
        
        return SettingType(
            setting_type_id=setting_type_id,
            **defaults
        )
    
    @staticmethod
    def create_test_setting(setting_type_id: str, setting_value: str,
                          related_entity_id: str, **kwargs: str) -> Setting:
        """Create a test setting with default values."""
        defaults = {
            'created_user_id': 'test',
            'updated_user_id': 'test'
        }
        defaults.update(kwargs)
        
        return Setting(
            setting_type_id=setting_type_id,
            setting_value=setting_value,
            related_entity_id=related_entity_id,
            **defaults
        )
    
    @staticmethod
    def verify_setting_persistence(mock_db_manager: Mock, expected_inserts: int = 0,
                                 expected_updates: int = 0, expected_deletes: int = 0) -> None:
        """Verify expected database operations were called."""
        execute_many_calls = mock_db_manager.execute_many.call_args_list
        
        insert_calls = [call for call in execute_many_calls 
                       if 'INSERT INTO settings' in call[0][0]]
        update_calls = [call for call in execute_many_calls 
                       if 'UPDATE settings' in call[0][0]]
        delete_calls = [call for call in execute_many_calls 
                       if 'DELETE FROM settings' in call[0][0]]
        
        assert len(insert_calls) == (1 if expected_inserts > 0 else 0)
        assert len(update_calls) == (1 if expected_updates > 0 else 0)
        assert len(delete_calls) == (1 if expected_deletes > 0 else 0)
        
        if expected_inserts > 0:
            insert_data = insert_calls[0][0][1]
            assert len(insert_data) == expected_inserts
        
        if expected_updates > 0:
            update_data = update_calls[0][0][1]
            assert len(update_data) == expected_updates
        
        if expected_deletes > 0:
            delete_data = delete_calls[0][0][1]
            assert len(delete_data) == expected_deletes


@pytest.fixture
def settings_test_helper():
    """Settings test helper instance."""
    return SettingsTestHelper()


# Parametrized fixtures for different data types
@pytest.fixture(params=[
    ("string", "test_value", json.dumps({"minLength": 1, "maxLength": 100})),
    ("integer", "42", json.dumps({"minimum": 0, "maximum": 100})),
    ("number", "3.14", json.dumps({"minimum": 0.0, "maximum": 10.0})),
    ("boolean", "true", json.dumps({"type": "boolean"})),
    ("json", '{"key": "value"}', json.dumps({"type": "object"}))
])
def data_type_test_case(request):
    """Parametrized test data for different setting data types."""
    data_type, valid_value, validation_rules = request.param
    return {
        'data_type': data_type,
        'valid_value': valid_value,
        'validation_rules': validation_rules,
        'invalid_values': {
            'string': ["", "x" * 101] if data_type == 'string' else ["not_string"],
            'integer': ["-1", "101", "not_number"] if data_type == 'integer' else ["42"],
            'number': ["-1.0", "11.0", "not_number"] if data_type == 'number' else ["3.14"],
            'boolean': ["not_boolean", "1", "0"] if data_type == 'boolean' else ["true"],
            'json': ['{"invalid": json}', "not_json"] if data_type == 'json' else ['{"key": "value"}']
        }.get(data_type, ["invalid"])
    }


@pytest.fixture
def validation_test_cases():
    """Test cases for validation scenarios."""
    return {
        'string_enum': {
            'data_type': 'string',
            'validation_rules': json.dumps({"enum": ["option1", "option2", "option3"]}),
            'valid_values': ["option1", "option2", "option3"],
            'invalid_values': ["option4", "", "OPTION1"]
        },
        'integer_range': {
            'data_type': 'integer',
            'validation_rules': json.dumps({"minimum": 10, "maximum": 100}),
            'valid_values': ["10", "50", "100"],
            'invalid_values': ["9", "101", "not_number"]
        },
        'string_pattern': {
            'data_type': 'string',
            'validation_rules': json.dumps({"pattern": "^[A-Za-z0-9]+$"}),
            'valid_values': ["abc123", "ABC", "123"],
            'invalid_values': ["abc-123", "abc 123", "abc@123"]
        }
    }
