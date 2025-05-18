import sqlite3
import os
from pathlib import Path

def inspect_database(db_path):
    """Inspect the database schema and print detailed information."""
    print(f"\nInspecting database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("Database file does not exist!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nTables in database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Get schema for session_keystrokes
        cursor.execute("PRAGMA table_info(session_keystrokes);")
        schema = cursor.fetchall()
        
        print("\nSession_keystrokes table schema:")
        print("cid | name                 | type    | notnull | dflt_value | pk")
        print("----+----------------------+---------+---------+------------+----")
        for col in schema:
            print(f"{col[0]:<3} | {col[1]:<20} | {col[2]:<7} | {col[3]:<7} | {str(col[4]):<10} | {col[5]}")
        
        # Check if wpm and accuracy columns exist
        column_names = [col[1].lower() for col in schema]
        print("\nChecking for wpm and accuracy columns:")
        print(f"'wpm' in columns: {'wpm' in column_names}")
        print(f"'accuracy' in columns: {'accuracy' in column_names}")
        
        # Get sample data
        cursor.execute("SELECT * FROM session_keystrokes LIMIT 1;")
        sample = cursor.fetchone()
        
        if sample:
            print("\nSample data (first row):")
            for i, col in enumerate(schema):
                print(f"{col[1]}: {sample[i] if i < len(sample) else 'N/A'}")
    
    except Exception as e:
        print(f"Error inspecting database: {e}")
    finally:
        conn.close()

def main():
    """Main function to inspect the database."""
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = temp_db.name
    temp_db.close()
    
    print(f"Creating temporary database at: {db_path}")
    
    try:
        # Initialize the database with our schema
        db = DatabaseManager(db_path)
        db.init_tables()
        
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Get list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if not tables:
                print("No tables found in the database.")
                return  # This is inside the main() function, so it's valid
                
            print("\nTables in the database:")
            for table in tables:
                print(f"- {table[0]}")
                
            # For each table, show its schema and sample data
            for table in tables:
                table_name = table[0]
                print(f"\n{'='*50}")
                print(f"Table: {table_name}")
                print(f"{'='*50}")
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                schema = cursor.fetchall()
                
                if not schema:
                    print("  No schema information available")
                    continue
                    
                print("\nSchema:")
                for col in schema:
                    col_id, name, col_type, not_null, default_val, pk = col
                    print(f"  {name:20} {col_type:15} {'NOT NULL' if not_null else 'NULL':10} DEFAULT: {default_val or 'None':10} {'PRIMARY KEY' if pk else ''}")
                
                # Show sample data (first 3 rows)
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                    rows = cursor.fetchall()
                    
                    if not rows:
                        print("\nNo data in table")
                        continue
                        
                    print("\nSample data:")
                    
                    # Get column names
                    col_names = [desc[0] for desc in cursor.description]
                    print("  " + " | ".join(f"{name:15}" for name in col_names))
                    print("  " + "-" * (len(col_names) * 18))
                    
                    for row in rows:
                        print("  " + " | ".join(f"{str(val)[:15]:15}" for val in row))
                        
                    # Count total rows
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    if count > 3:
                        print(f"  ... and {count - 3} more rows")
                        
                except sqlite3.Error as e:
                    print(f"\nError reading data from {table_name}: {e}")
                    
        finally:
            cursor.close()
            conn.close()
            db.close()
            
    except Exception as e:
        print(f"\nError during database inspection: {e}")
    finally:
        # Clean up the temporary database
        try:
            os.unlink(db_path)
        except PermissionError:
            print(f"\nWarning: Could not delete temporary database file {db_path}")
        except Exception as e:
            print(f"\nWarning: Could not delete temporary database file: {e}")

if __name__ == "__main__":
    import tempfile
    from db.database_manager import DatabaseManager
    main()
