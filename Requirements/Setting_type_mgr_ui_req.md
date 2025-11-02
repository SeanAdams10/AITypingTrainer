# Setting Type Manager UI

## Overview

The Setting Type Manager is a modern PySide6-based desktop UI for managing setting type definitions in the AI Typing Trainer application. It provides full CRUD (Create, Read, Update, Delete) operations for setting types with validation and filtering capabilities.

## Features

### Core Functionality
- **Add Setting Types**: Create new setting type definitions with full validation
- **Edit Setting Types**: Modify existing setting types (except system types)
- **Delete Setting Types**: Soft-delete setting types (mark as inactive)
- **Search/Filter**: Real-time search and entity type filtering
- **Validation**: Comprehensive validation for all fields and data types

### UI Components

#### Main Window (`setting_type_manager.py`)
- **Modern Windows 11-style design** with rounded corners and subtle shadows
- **Maximized window** with minimum size of 900x600
- **Search bar** for real-time filtering by setting type name
- **Entity type filter** dropdown (All, user, keyboard, global)
- **List view** showing all setting types with visual indicators for system types
- **Action buttons**: Add, Edit, Delete
- **Status bar** showing operation results and error messages

#### Dialog (`setting_type_dialogs.py`)
- **Form-based input** for all setting type attributes
- **Field validation** with helpful error messages
- **Dynamic placeholders** that update based on data type selection
- **Visual feedback** for required fields
- **Modern styling** consistent with main window

### Setting Type Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Type ID | String (6 chars) | Yes | Unique uppercase alphanumeric identifier |
| Name | String (100 max) | Yes | Human-readable name |
| Description | Text (500 max) | Yes | Detailed description |
| Entity Type | Enum | Yes | user, keyboard, or global |
| Data Type | Enum | Yes | string, integer, boolean, or decimal |
| Default Value | String | No | Optional default value |
| Validation Rules | JSON | No | Optional validation constraints |
| Is System | Boolean | No | System types cannot be deleted |
| Is Active | Boolean | No | Inactive types are hidden |

### Validation Rules Examples

**Integer validation:**
```json
{"min": 8, "max": 32}
```

**String validation:**
```json
{"min_length": 1, "max_length": 50, "pattern": "^[A-Z]+$"}
```

**Decimal validation:**
```json
{"min": 0.0, "max": 100.0}
```

## Usage

### Running the UI

```bash
# From the feature_settings directory
python run_setting_type_manager.py
```

### Programmatic Usage

```python
from PySide6.QtWidgets import QApplication
from desktop_ui.setting_type_manager import SettingTypeManagerWindow
from models.library import DatabaseManager

# Create application
app = QApplication(sys.argv)

# Set up database
db_manager = DatabaseManager("path/to/database.db")

# Create and show window
window = SettingTypeManagerWindow(db_manager=db_manager)
window.showMaximized()

# Run
app.exec()
```

### Testing Mode

For automated testing, use `testing_mode=True` to suppress modal dialogs:

```python
window = SettingTypeManagerWindow(
    db_manager=db_manager,
    testing_mode=True
)
```

## Architecture

### Design Patterns
- **Dependency Injection**: DatabaseManager passed to constructor
- **Singleton Pattern**: Uses SettingsManager singleton for data access
- **MVC Pattern**: Separates UI (View) from data (Model) via SettingsManager
- **Testing Mode**: Allows headless testing without modal dialogs

### Database Integration
- Uses `SettingsManager` singleton for all database operations
- Supports bulk persistence with `flush()` method
- Implements caching for performance
- Handles transaction management internally

### UI Standards Compliance
Follows all standards from `MemoriesAndRules/ui_standards.md`:
- ✅ **Clarity**: Clear labels and helpful tooltips
- ✅ **Consistency**: Shared design patterns with library UI
- ✅ **Efficiency**: Keyboard shortcuts and double-click editing
- ✅ **Accessibility**: WCAG 2.1 AA compliant (keyboard navigation, focus states)
- ✅ **Simplicity**: Clean, focused interface without clutter

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/desktop_ui/test_setting_type_manager_ui.py -v

# Run specific test
uv run pytest tests/desktop_ui/test_setting_type_manager_ui.py::TestSettingTypeManagerWindow::test_window_initialization -v
```

### Test Coverage
- Window initialization and configuration
- Data loading and display
- Button state management
- Selection handling
- Search and filtering
- System setting type protection
- Validation error handling
- Entity type filtering

## Files

### Implementation
- `desktop_ui/setting_type_manager.py` - Main window implementation
- `desktop_ui/setting_type_dialogs.py` - Dialog components
- `run_setting_type_manager.py` - Standalone runner script

### Tests
- `tests/desktop_ui/test_setting_type_manager_ui.py` - Comprehensive test suite

### Dependencies
- `models/setting_type.py` - Setting type data model
- `models/settings_manager.py` - Settings manager singleton
- `models/library.py` - Database manager

## Future Enhancements

Potential improvements for future versions:
- **Export/Import**: Export setting types to JSON/CSV
- **Bulk Operations**: Select and delete multiple setting types
- **History View**: Show audit trail for setting type changes
- **Advanced Validation**: Visual JSON editor for validation rules
- **Templates**: Pre-defined setting type templates
- **Search Improvements**: Advanced search with multiple criteria
- **Sorting**: Sort by name, type, entity type, etc.

## Troubleshooting

### Common Issues

**Issue**: Setting type list is empty
- **Solution**: Check database connection and ensure `setting_types` table exists

**Issue**: Cannot edit setting type
- **Solution**: Verify it's not a system setting type (check `is_system` flag)

**Issue**: Validation errors on save
- **Solution**: Ensure all required fields are filled and Type ID is exactly 6 uppercase alphanumeric characters

**Issue**: Dialog doesn't open
- **Solution**: Check for exceptions in console, verify PySide6 is installed

## Support

For issues or questions:
1. Check the test suite for usage examples
2. Review the SettingsManager documentation
3. Consult the UI standards in MemoriesAndRules/ui_standards.md
