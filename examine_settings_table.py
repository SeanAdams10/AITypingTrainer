#!/usr/bin/env python3
"""
Script to examine the current settings table structure and data.
"""

import sqlite3
import sys
from typing import List, Tuple, Any

def examine_settings_table() -> None:
    """Examine the current settings table structure and data."""
    try:
        # Connect to the main database
        conn = sqlite3.connect('typing_data.db')
        cursor = conn.cursor()

        print('=== CURRENT SETTINGS TABLE STRUCTURE ===')
        cursor.execute('PRAGMA table_info(settings)')
        columns = cursor.fetchall()
        
        if not columns:
            print('Settings table does not exist or has no columns')
            return
            
        for col in columns:
            nullable = "NULL" if not col[3] else "NOT NULL"
            default = f"DEFAULT {col[4]}" if col[4] is not None else "NO DEFAULT"
            print(f'{col[1]:<20} {col[2]:<15} {nullable:<10} {default}')

        print('\n=== SAMPLE SETTINGS DATA ===')
        cursor.execute('SELECT * FROM settings LIMIT 5')
        rows = cursor.fetchall()
        
        if rows:
            # Print column headers
            col_names = [desc[1] for desc in columns]
            print(' | '.join(f'{name:<15}' for name in col_names))
            print('-' * (len(col_names) * 17))
            
            for row in rows:
                print(' | '.join(f'{str(val):<15}' for val in row))
        else:
            print('No data in settings table')

        print('\n=== SETTINGS COUNT ===')
        cursor.execute('SELECT COUNT(*) FROM settings')
        count = cursor.fetchone()[0]
        print(f'Total settings: {count}')

        print('\n=== UNIQUE SETTING TYPES ===')
        cursor.execute('SELECT DISTINCT setting_type_id FROM settings ORDER BY setting_type_id')
        types = cursor.fetchall()
        for setting_type in types:
            print(f'  {setting_type[0]}')

        conn.close()

    except sqlite3.Error as e:
        print(f'Database error: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

def examine_users_table() -> None:
    """Examine the users table to get valid user IDs."""
    try:
        conn = sqlite3.connect('typing_data.db')
        cursor = conn.cursor()

        print('\n=== USERS TABLE STRUCTURE ===')
        cursor.execute('PRAGMA table_info(users)')
        columns = cursor.fetchall()
        
        if not columns:
            print('Users table does not exist')
            return
            
        for col in columns:
            nullable = "NULL" if not col[3] else "NOT NULL"
            default = f"DEFAULT {col[4]}" if col[4] is not None else "NO DEFAULT"
            print(f'{col[1]:<20} {col[2]:<15} {nullable:<10} {default}')

        print('\n=== SAMPLE USERS DATA ===')
        cursor.execute('SELECT user_id, first_name, last_name, email FROM users LIMIT 10')
        rows = cursor.fetchall()
        
        if rows:
            print(f'{"user_id":<40} {"first_name":<15} {"last_name":<15} {"email":<30}')
            print('-' * 100)
            for row in rows:
                print(f'{str(row[0]):<40} {str(row[1]):<15} {str(row[2]):<15} {str(row[3]):<30}')
        else:
            print('No users found')

        print('\n=== USERS COUNT ===')
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        print(f'Total users: {count}')

        conn.close()

    except sqlite3.Error as e:
        print(f'Database error: {e}')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    examine_settings_table()
    examine_users_table()
