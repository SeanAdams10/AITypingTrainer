-- Migration script to add missing columns to existing settings table
-- This script adds created_at, updated_at, created_user_id, updated_user_id, valid_from, valid_to, and row_checksum columns

-- First, check if the settings table exists
-- If it doesn't exist, this migration is not needed as the new DDL will create it correctly

-- Add created_at column if it doesn't exist
ALTER TABLE settings ADD COLUMN created_at TIMESTAMP_NTZ;

-- Add updated_at column if it doesn't exist  
ALTER TABLE settings ADD COLUMN updated_at TIMESTAMP_NTZ;

-- Add created_user_id column if it doesn't exist
ALTER TABLE settings ADD COLUMN created_user_id TEXT DEFAULT 'a287befc-0570-4eb3-a5d7-46653054cf0f';

-- Add updated_user_id column if it doesn't exist
ALTER TABLE settings ADD COLUMN updated_user_id TEXT DEFAULT 'a287befc-0570-4eb3-a5d7-46653054cf0f';

-- Add valid_from column if it doesn't exist
ALTER TABLE settings ADD COLUMN valid_from TIMESTAMP_NTZ;

-- Add valid_to column if it doesn't exist
ALTER TABLE settings ADD COLUMN valid_to TIMESTAMP_NTZ DEFAULT '9999-12-31T23:59:59Z';

-- Add row_checksum column if it doesn't exist
ALTER TABLE settings ADD COLUMN row_checksum BINARY(32) DEFAULT (ZEROBLOB(32));

-- Update existing rows to set timestamps to current time if they are NULL
UPDATE settings 
SET created_at = datetime('now'), 
    updated_at = datetime('now'),
    valid_from = datetime('now')
WHERE created_at IS NULL OR updated_at IS NULL OR valid_from IS NULL;

-- Make the columns NOT NULL after setting values
-- Note: SQLite doesn't support ALTER COLUMN to add NOT NULL constraint directly
-- This would need to be done by recreating the table if strict NOT NULL is required

-- Add foreign key constraints for user references
-- Note: SQLite foreign key constraints can only be added during table creation
-- To add these constraints, the table would need to be recreated

-- For PostgreSQL, you would use:
-- ALTER TABLE settings ADD CONSTRAINT fk_settings_created_user FOREIGN KEY (created_user_id) REFERENCES users(user_id);
-- ALTER TABLE settings ADD CONSTRAINT fk_settings_updated_user FOREIGN KEY (updated_user_id) REFERENCES users(user_id);

-- Drop the old foreign key constraint to setting_types if it exists
-- Note: SQLite doesn't support dropping foreign key constraints directly
-- This would require recreating the table

COMMIT;
