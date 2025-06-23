#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для діагностики бази даних
Можна запускати окремо для перевірки стану бази даних
"""

import os
import sys
import sqlite3

def diagnose_database():
    """Comprehensive database diagnosis"""
    
    # Add current directory to path to import local modules
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    try:
        import db_manager
        
        print("=== DATABASE DIAGNOSIS ===")
        print(f"Script directory: {current_dir}")
        
        # Check database path
        db_path = db_manager.DB_PATH
        print(f"Database path: {os.path.abspath(db_path)}")
        print(f"Database exists: {os.path.exists(db_path)}")
        
        if os.path.exists(db_path):
            print(f"Database size: {os.path.getsize(db_path)} bytes")
            
            # Check database integrity
            print("\n=== DATABASE INTEGRITY CHECK ===")
            result = db_manager.check_database_integrity()
            
            # Additional detailed checks
            try:
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                
                print("\n=== TABLE INFORMATION ===")
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"Total tables: {len(tables)}")
                
                for table in tables:
                    table_name = table[0]
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count = cursor.fetchone()[0]
                        print(f"  {table_name}: {count} records")
                    except Exception as e:
                        print(f"  {table_name}: ERROR - {e}")
                
                print("\n=== USER STATISTICS ===")
                try:
                    cursor.execute("SELECT language, COUNT(*) FROM users GROUP BY language")
                    lang_stats = cursor.fetchall()
                    for lang, count in lang_stats:
                        print(f"  {lang}: {count} users")
                except Exception as e:
                    print(f"  ERROR getting user stats: {e}")
                
                print("\n=== SHARED DICTIONARIES ===")
                try:
                    cursor.execute("SELECT COUNT(*) FROM shared_dictionaries")
                    shared_dict_count = cursor.fetchone()[0]
                    print(f"  Total shared dictionaries: {shared_dict_count}")
                    
                    if shared_dict_count > 0:
                        cursor.execute("SELECT name, code, created_by FROM shared_dictionaries")
                        shared_dicts = cursor.fetchall()
                        for name, code, creator in shared_dicts:
                            print(f"    '{name}' (code: {code}, creator: {creator})")
                except Exception as e:
                    print(f"  ERROR getting shared dict stats: {e}")
                
                conn.close()
                
            except Exception as e:
                print(f"ERROR during detailed checks: {e}")
                
        else:
            print("❌ Database file does not exist!")
            print("This might be the cause of the database reset issue.")
            
            # Check if database directory exists
            db_dir = os.path.dirname(db_path)
            print(f"Database directory: {os.path.abspath(db_dir)}")
            print(f"Database directory exists: {os.path.exists(db_dir)}")
            
            if os.path.exists(db_dir):
                files_in_dir = os.listdir(db_dir)
                print(f"Files in database directory: {files_in_dir}")
            
        print("\n=== RECOMMENDATIONS ===")
        if not os.path.exists(db_path):
            print("1. Ensure the database file is properly transferred to the server")
            print("2. Check file permissions on the server")
            print("3. Verify the working directory is correct")
            print("4. Consider using absolute paths in production")
        else:
            print("✅ Database file exists and appears to be functional")
            
    except ImportError as e:
        print(f"ERROR: Cannot import db_manager: {e}")
        print("Make sure you're running this from the correct directory")
    except Exception as e:
        print(f"ERROR during diagnosis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_database()
