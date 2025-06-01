# -*- coding: utf-8 -*-
import sqlite3
import os
import glob
import re

def check_db_users():
    """Check users in database and CSV files"""
    from db_manager import DB_PATH, get_connection
    from storage import USER_DICT_DIR
    
    print("=== Checking Database Users ===")
    
    # Get users from database
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT chat_id, language FROM users")
    db_users = {chat_id: lang for chat_id, lang in cursor.fetchall()}
    
    print(f"Found {len(db_users)} users in database")
    
    # Get user tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'user_%'")
    user_tables = [table_name for table_name, in cursor.fetchall()]
    
    print(f"Found {len(user_tables)} user tables in database")
    
    # Check CSV files
    csv_pattern = os.path.join(USER_DICT_DIR, "*_words_*.csv")
    csv_files = glob.glob(csv_pattern)
    csv_users = set()
    
    for file_path in csv_files:
        match = re.search(r'_words_(\d+)\.csv$', os.path.basename(file_path))
        if match:
            csv_users.add(int(match.group(1)))
    
    print(f"Found {len(csv_users)} user CSV files")
    
    # Compare
    users_in_db_not_csv = set(db_users.keys()) - csv_users
    users_in_csv_not_db = csv_users - set(db_users.keys())
    
    print(f"\nUsers in database but not in CSV: {len(users_in_db_not_csv)}")
    print(f"Users in CSV but not in database: {len(users_in_csv_not_db)}")
    
    if users_in_csv_not_db:
        print("\nMissing users in database:")
        for user_id in users_in_csv_not_db:
            print(f"  - {user_id}")
        
        fix = input("\nDo you want to add missing users to database? (y/n): ")
        if fix.lower() == 'y':
            import db_manager
            print("\nAdding missing users to database...")
            for user_id in users_in_csv_not_db:
                # Determine language from file name
                ru_file = os.path.join(USER_DICT_DIR, f"ru_words_{user_id}.csv")
                uk_file = os.path.join(USER_DICT_DIR, f"uk_words_{user_id}.csv")
                
                lang = 'uk'  # Default
                if os.path.exists(ru_file):
                    lang = 'ru'
                elif os.path.exists(uk_file):
                    lang = 'uk'
                
                # Add user to database
                print(f"  - Adding user {user_id} with language {lang}")
                db_manager.initialize_user(user_id, lang)
    
    print("\nCheck completed.")

if __name__ == "__main__":
    check_db_users()
