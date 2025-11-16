# Spikes Directory

This directory contains utility scripts and experimental code for the AI Typing Trainer project.

## Scripts

### insert_setting_types.py

**Purpose**: Inserts all setting type definitions from Requirements/Settings_req.md into the database.

**What it does**:
1. Connects to the cloud database
2. Reads the setting type definitions from the script (based on Requirements/Settings_req.md)
3. For each setting type:
   - Checks if it already exists (skips if found)
   - Creates a SettingType object with all required fields
   - Inserts into both `setting_types` and `setting_types_history` tables using SettingTypeManager
4. Provides summary of inserted/skipped setting types

**Setting Types Inserted**:
- **LSTKBD** - Last Used Keyboard (user)
- **DRICAT** - Last Selected Drill Category (keyboard)
- **DRISNP** - Last Selected Drill Snippet (keyboard)
- **DRILEN** - Drill Length (keyboard)
- **NGRSZE** - N-gram Size (keyboard)
- **NGRCNT** - N-gram Count (keyboard)
- **NGRMOC** - N-gram Minimum Occurrences (keyboard)
- **NGRLEN** - N-gram Practice Length (keyboard)
- **NGRKEY** - N-gram Included Keys (keyboard)
- **NGRTYP** - N-gram Practice Type (keyboard)
- **NGRFST** - Focus on Speed Target (keyboard)

**Usage**:
```bash
# From the feature_settings directory
uv run python Spikes/insert_setting_types.py
```

**Prerequisites**:
- Database connection configured (uses ConnectionType.CLOUD)
- `setting_types` and `setting_types_history` tables must exist

**Output**:
The script will print:
- Progress for each setting type (inserted/skipped/error)
- Summary with counts of inserted, skipped, and total setting types

**Safety**:
- Checks for existing setting types before inserting (idempotent)
- Uses SettingTypeManager for proper SCD-2 history tracking
- All setting types marked as non-system (is_system=False)

---

### update_settings_checksums.py

**Purpose**: Updates all settings in the database with calculated row checksums and proper user IDs.

**What it does**:
1. Connects to the cloud database
2. Finds Sean's user_id from the users table
3. Reads all settings from the settings table
4. Calculates the correct row_checksum for each setting (SHA-256 hash of business columns)
5. Updates each setting with:
   - Calculated `row_checksum`
   - `created_user_id` set to Sean's user_id
   - `updated_user_id` set to Sean's user_id

**Usage**:
```bash
# From the feature_settings directory
uv run python Spikes/update_settings_checksums.py
```

**Prerequisites**:
- Database connection configured (uses ConnectionType.CLOUD)
- User "Sean" must exist in the users table
- Settings table must exist with proper schema

**Output**:
The script will print:
- Sean's user_id
- Progress for each setting updated
- Total count of settings updated

**Safety**:
- Only updates `row_checksum`, `created_user_id`, and `updated_user_id` columns
- Does not modify business data (setting_type_id, setting_value, related_entity_id)
- Uses proper Pydantic model for checksum calculation
