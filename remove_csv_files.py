# -*- coding: utf-8 -*-
import os
import glob
import shutil
import re

def backup_and_remove_csv():
    """Backup and remove CSV files after migration to SQLite is complete"""
    from storage import USER_DICT_DIR
    
    print("=== CSV Cleanup Utility ===")
    
    # Create backup directory
    backup_dir = "csv_backup"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"Created backup directory: {backup_dir}")
    
    # Find all CSV files
    user_dict_pattern = os.path.join(USER_DICT_DIR, "*.csv")
    root_dict_pattern = "*.csv"
    
    csv_files_in_dir = glob.glob(user_dict_pattern)
    csv_files_in_root = glob.glob(root_dict_pattern)
    
    all_csv = csv_files_in_dir + csv_files_in_root
    print(f"Found {len(all_csv)} CSV files")
    
    # Move files to backup
    for csv_file in all_csv:
        filename = os.path.basename(csv_file)
        backup_path = os.path.join(backup_dir, filename)
        
        print(f"Moving {csv_file} to {backup_path}")
        try:
            shutil.copy2(csv_file, backup_path)
            os.remove(csv_file)
            print(f"  ✅ Backed up and removed")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\nCSV cleanup complete!")
    print(f"All files were backed up to {os.path.abspath(backup_dir)}")
    print(f"You can safely delete the backup directory if database is working correctly.")

if __name__ == "__main__":
    confirm = input("This will remove all CSV files after backing them up. Continue? (y/n): ")
    if confirm.lower() == 'y':
        backup_and_remove_csv()
    else:
        print("Operation cancelled.")
