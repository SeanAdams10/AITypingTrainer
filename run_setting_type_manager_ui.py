"""Runner script for the Setting Type Manager UI.

Simple launcher for the setting type management interface.
Uses the Docker PostgreSQL connection by default.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from db.database_manager import ConnectionType
from desktop_ui.setting_type_manager_ui import SettingTypeManagerWindow
from PySide6.QtWidgets import QApplication

def main() -> None:
    """Run the Setting Type Manager UI with Docker PostgreSQL connection."""
    app = QApplication(sys.argv)
    
    # Use POSTGRESS_DOCKER by default - change to ConnectionType.CLOUD for cloud DB
    window = SettingTypeManagerWindow(
        connection_type=ConnectionType.POSTGRESS_DOCKER
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
