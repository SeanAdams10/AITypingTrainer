import sqlite3
import re

def copy_snippet_parts(clear_existing=True):
    """
    Copy the snippet_parts table from typing_data_backup.db to typing_data.db
    
    Args:
        clear_existing: If True, will clear existing data before copying
    """
    print("Starting to copy snippet_parts from backup database...")
    
    # Connect to both databases
    backup_conn = sqlite3.connect('typing_data_backup.db')
    backup_cursor = backup_conn.cursor()
    
    main_conn = sqlite3.connect('typing_data.db')
    main_cursor = main_conn.cursor()
    
    try:
        # Check the schema of both databases
        backup_cursor.execute("PRAGMA table_info(snippet_parts)")
        backup_columns = [col[1] for col in backup_cursor.fetchall()]
        print(f"Backup database columns: {backup_columns}")
        
        main_cursor.execute("PRAGMA table_info(snippet_parts)")
        main_columns = [col[1] for col in main_cursor.fetchall()]
        print(f"Main database columns: {main_columns}")
        
        if not backup_columns:
            print("Error: snippet_parts table not found in backup database!")
            return
            
        if not main_columns:
            print("Error: snippet_parts table not found in main database!")
            return
        
        # Define a specific mapping for columns with different naming patterns
        specific_mapping = {
            'PartID': 'part_id',
            'SnippetID': 'snippet_id',
            'PartNumber': 'part_number',
            'Content': 'content'
        }
        
        # Get the data from the backup database
        column_list = ", ".join(backup_columns)
        backup_cursor.execute(f"SELECT {column_list} FROM snippet_parts")
        rows = backup_cursor.fetchall()
        
        if not rows:
            print("No data found in backup snippet_parts table!")
            return
        
        print(f"Found {len(rows)} rows in backup snippet_parts table")
        
        # First, check if there's any data in the current snippet_parts table
        main_cursor.execute("SELECT COUNT(*) FROM snippet_parts")
        count = main_cursor.fetchone()[0]
        
        if count > 0:
            print(f"Current snippet_parts table has {count} rows")
            if clear_existing:
                main_cursor.execute("DELETE FROM snippet_parts")
                main_conn.commit()
                print("Existing data deleted")
            else:
                print("Keeping existing data, will attempt to copy non-conflicting records")
        
        # Create a mapping between backup and main columns using specific_mapping
        column_mapping = {}
        for backup_col in backup_columns:
            if backup_col in specific_mapping and specific_mapping[backup_col] in main_columns:
                column_mapping[backup_col] = specific_mapping[backup_col]
        
        print(f"Column mapping: {column_mapping}")
        
        if not column_mapping:
            print("Error: No matching columns found between the databases!")
            return
        
        # Insert data from backup into the current database
        success_count = 0
        error_count = 0
        
        # Create the INSERT query based on the column mapping
        main_cols = list(column_mapping.values())
        placeholders = ", ".join(["?" for _ in main_cols])
        insert_query = f"INSERT INTO snippet_parts ({', '.join(main_cols)}) VALUES ({placeholders})"
        
        print(f"Insert query: {insert_query}")
        
        # Process each row
        for row in rows:
            try:
                # Map values based on the column mapping
                values = []
                for i, backup_col in enumerate(backup_columns):
                    if backup_col in column_mapping:
                        values.append(row[i])
                
                # Print the first row being inserted for debugging
                if success_count == 0:
                    print(f"Inserting values: {values}")
                
                main_cursor.execute(insert_query, values)
                success_count += 1
                
                if success_count % 5 == 0 or success_count == len(rows):
                    print(f"Progress: {success_count}/{len(rows)} records copied")
                
            except sqlite3.IntegrityError as e:
                # Skip duplicates or handle differently if needed
                error_count += 1
                print(f"SQLite Integrity Error: {e}")
                if success_count == 0:
                    # Show the problematic row for the first error
                    print(f"Row data: {row}")
                    print(f"Column mapping: {column_mapping}")
                    print(f"Mapped values: {values}")
            except Exception as e:
                error_count += 1
                print(f"Error copying record: {e}")
        
        main_conn.commit()
        print(f"Copy completed: {success_count} records successfully copied, {error_count} errors/duplicates skipped")
        
    except Exception as e:
        print(f"Error during copy operation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        backup_conn.close()
        main_conn.close()

if __name__ == "__main__":
    # Automatically clear existing data
    copy_snippet_parts(clear_existing=True)
