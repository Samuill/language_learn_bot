#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для резервного копіювання бази даних
"""

import os
import shutil
import datetime
import sys

def backup_database():
    """Create a backup of the database"""
    
    # Add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    try:
        import db_manager
        
        db_path = db_manager.DB_PATH
        
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return False
        
        # Create backup filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"german_words_backup_{timestamp}.db"
        backup_path = os.path.join(os.path.dirname(db_path), backup_filename)
        
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Get file sizes for verification
        original_size = os.path.getsize(db_path)
        backup_size = os.path.getsize(backup_path)
        
        if original_size == backup_size:
            print(f"✅ Database backup created successfully:")
            print(f"   Original: {db_path} ({original_size} bytes)")
            print(f"   Backup: {backup_path} ({backup_size} bytes)")
            return True
        else:
            print(f"❌ Backup size mismatch:")
            print(f"   Original: {original_size} bytes")
            print(f"   Backup: {backup_size} bytes")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import db_manager: {e}")
        return False
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    backup_database()
