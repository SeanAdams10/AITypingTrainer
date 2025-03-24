"""
Script to remove the practice_session_keystrokes table from the database
"""
import sqlite3
import os

def main():
    """Drop the practice_session_keystrokes table from the database"""
    print("Dropping practice_session_keystrokes table...")
    
    try:
        # Create database connection
        conn = sqlite3.connect('typing_data.db')
        c = conn.cursor()
        
        # Drop the table if it exists
        c.execute("DROP TABLE IF EXISTS practice_session_keystrokes")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        print("Table practice_session_keystrokes has been removed successfully!")
        return True
    except Exception as e:
        print(f"Error dropping table: {e}")
        return False

if __name__ == "__main__":
    main()
