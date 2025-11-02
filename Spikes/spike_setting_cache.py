import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from db.database_manager import ConnectionType, DatabaseManager
from models.settings_manager import SettingsManager

# Create a new DatabaseManager object, which connects to the cloud DB
db_manager = DatabaseManager(connection_type=ConnectionType.CLOUD)

# Get the singleton instance (pass db_manager on first call)
settings_mgr = SettingsManager.get_instance(db_manager)

# Access the cache directly
settings_cache = settings_mgr.cache

print(f"Number of settings: {len(settings_cache.entries)}")
