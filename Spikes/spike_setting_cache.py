import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database_manager import ConnectionType, DatabaseManager
from models.setting_manager import SettingManager
from models.setting_cache import global_setting_cache

# Create a new DatabaseManager object, which connects to the cloud DB
db_manager = DatabaseManager(connection_type=ConnectionType.CLOUD)

# Get the singleton instance (pass db_manager on first call)
settings_mgr = SettingManager.get_instance(db_manager)

# Access the global cache directly
print(f"Number of settings: {len(global_setting_cache.entries)}")
