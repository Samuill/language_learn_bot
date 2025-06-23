#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для перевірки готовності до розгортання на сервері
"""

import os
import sys
import importlib.util

def check_deployment_readiness():
    """Check if the bot is ready for server deployment"""
    
    print("=== DEPLOYMENT READINESS CHECK ===")
    
    # Check current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Current directory: {current_dir}")
    
    # Check required files
    required_files = [
        'main.py',
        'config.py', 
        'db_manager.py',
        'db_init.py',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    # Check required directories
    required_dirs = [
        'handlers',
        'utils', 
        'locales',
        'database'
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        dir_path = os.path.join(current_dir, dir_name)
        if os.path.exists(dir_path):
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ - MISSING")
            missing_dirs.append(dir_name)
    
    # Check database
    print("\n=== DATABASE CHECK ===")
    try:
        sys.path.insert(0, current_dir)
        import db_manager
        
        db_path = db_manager.DB_PATH
        print(f"Database path: {os.path.abspath(db_path)}")
        
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"✅ Database exists ({size} bytes)")
            
            # Quick integrity check
            try:
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM words")  
                word_count = cursor.fetchone()[0]
                conn.close()
                print(f"✅ Database accessible ({user_count} users, {word_count} words)")
            except Exception as e:
                print(f"⚠️  Database access issue: {e}")
                
        else:
            print(f"❌ Database missing: {db_path}")
            
    except ImportError as e:
        print(f"❌ Cannot import db_manager: {e}")
    
    # Check Python dependencies
    print("\n=== DEPENDENCY CHECK ===")
    required_packages = [
        'telebot',
        'pandas', 
        'sqlite3',
        'googletrans'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'sqlite3':
                import sqlite3
            elif package == 'telebot':
                import telebot
            elif package == 'pandas':
                import pandas
            elif package == 'googletrans':
                import googletrans
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing_packages.append(package)
    
    # Check config
    print("\n=== CONFIG CHECK ===")
    try:
        import config
        if hasattr(config, 'BOT_TOKEN'):
            if config.BOT_TOKEN and config.BOT_TOKEN != 'YOUR_BOT_TOKEN':
                print("✅ BOT_TOKEN configured")
            else:
                print("❌ BOT_TOKEN not set")
        else:
            print("❌ BOT_TOKEN not found in config")
            
        if hasattr(config, 'ADMIN_ID'):
            if config.ADMIN_ID and isinstance(config.ADMIN_ID, int):
                print("✅ ADMIN_ID configured")
            else:
                print("❌ ADMIN_ID not properly set")
        else:
            print("❌ ADMIN_ID not found in config")
            
    except ImportError as e:
        print(f"❌ Cannot import config: {e}")
    
    # Summary
    print("\n=== SUMMARY ===")
    issues = len(missing_files) + len(missing_dirs) + len(missing_packages)
    
    if issues == 0:
        print("🎉 Ready for deployment!")
        print("\nRecommendations for server deployment:")
        print("1. Create backup of database before transfer")
        print("2. Check file permissions on server")
        print("3. Use process manager (PM2, systemd) for production")
        print("4. Set up log rotation")
        print("5. Monitor disk space for database growth")
    else:
        print(f"⚠️  {issues} issues found that need to be resolved")
        if missing_files:
            print(f"Missing files: {', '.join(missing_files)}")
        if missing_dirs:
            print(f"Missing directories: {', '.join(missing_dirs)}")
        if missing_packages:
            print(f"Missing packages: {', '.join(missing_packages)}")

if __name__ == "__main__":
    check_deployment_readiness()
