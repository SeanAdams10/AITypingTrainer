"""
Script to rename database columns from CamelCase to snake_case
"""
import sqlite3
import os
import sys

def backup_database():
    """Create a backup of the database before making changes"""
    try:
        if os.path.exists('typing_data.db'):
            os.system('copy typing_data.db typing_data_backup.db')
            print("Database backup created as typing_data_backup.db")
            return True
        else:
            print("Database file not found!")
            return False
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

def rename_columns():
    """Rename all columns from CamelCase to snake_case"""
    conn = sqlite3.connect('typing_data.db')
    c = conn.cursor()

    try:
        # Start a transaction
        c.execute("BEGIN TRANSACTION")

        # 1. Rename columns in text_category table
        print("Renaming columns in text_category table...")
        c.execute("ALTER TABLE text_category RENAME COLUMN CategoryID TO category_id")
        c.execute("ALTER TABLE text_category RENAME COLUMN CategoryName TO category_name")

        # 2. Rename columns in text_snippets table
        print("Renaming columns in text_snippets table...")
        c.execute("ALTER TABLE text_snippets RENAME COLUMN SnippetID TO snippet_id")
        c.execute("ALTER TABLE text_snippets RENAME COLUMN CategoryID TO category_id")
        c.execute("ALTER TABLE text_snippets RENAME COLUMN SnippetName TO snippet_name")
        c.execute("ALTER TABLE text_snippets RENAME COLUMN CreatedAt TO created_at")

        # 3. Rename columns in snippet_parts table
        print("Renaming columns in snippet_parts table...")
        c.execute("ALTER TABLE snippet_parts RENAME COLUMN PartID TO part_id")
        c.execute("ALTER TABLE snippet_parts RENAME COLUMN SnippetID TO snippet_id")
        c.execute("ALTER TABLE snippet_parts RENAME COLUMN PartNumber TO part_number")
        c.execute("ALTER TABLE snippet_parts RENAME COLUMN Content TO content")

        # 4. Update foreign key references
        # SQLite doesn't allow altering foreign key constraints directly, but they'll be updated when we recreate tables

        # Commit the transaction
        c.execute("COMMIT")
        print("All columns renamed successfully!")

    except Exception as e:
        c.execute("ROLLBACK")
        print(f"Error renaming columns: {e}")
        return False

    finally:
        conn.close()

    return True

def main():
    print("Starting database column renaming...")
    if not backup_database():
        print("Aborting due to backup failure")
        sys.exit(1)

    if rename_columns():
        print("Column renaming completed successfully!")
    else:
        print("Column renaming failed. Restore from backup if needed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
