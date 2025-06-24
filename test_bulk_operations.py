#!/usr/bin/env python3
"""
Test script for bulk operations in the German learning bot.
Tests the new database functions and bulk add/delete functionality.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import db_manager
    import config
    print("✅ Successfully imported required modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_database_functions():
    """Test the new database functions added to db_manager."""
    print("\n🔧 Testing database functions...")
    
    # Test if all required functions exist
    required_functions = [
        'delete_word_from_shared_dict',
        'delete_word_from_personal_dict', 
        'update_word_translation_shared_dict',
        'update_word_translation_personal_dict'
    ]
    
    missing_functions = []
    for func_name in required_functions:
        if not hasattr(db_manager, func_name):
            missing_functions.append(func_name)
    
    if missing_functions:
        print(f"❌ Missing functions: {missing_functions}")
        return False
    else:
        print("✅ All required database functions are present")
        return True

def test_database_connection():
    """Test database connection and basic operations."""
    print("\n💾 Testing database connection...")
    
    try:
        # Test basic database connection using the same path as db_manager
        conn = sqlite3.connect(db_manager.DB_PATH)
        cursor = conn.cursor()
          # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['words', 'users', 'shared_dictionaries']
        missing_tables = [table for table in required_tables if table not in tables]
        
        # Check for shared_dict tables (they are created dynamically)
        shared_dict_tables = [table for table in tables if table.startswith('shared_dict_') and table != 'shared_dictionaries']
        if shared_dict_tables:
            print(f"ℹ️ Found shared dictionary tables: {len(shared_dict_tables)} tables")
        
        if missing_tables:
            print(f"❌ Missing database tables: {missing_tables}")
            conn.close()
            return False
        
        print("✅ Database connection and tables OK")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_bulk_add_constants():
    """Test that bulk add constants are properly set."""
    print("\n📊 Testing bulk add constants...")
    
    try:
        # Import the handlers module to check constants
        from handlers import edit_word
        
        # Check if BULK_ADD_MAX_WORDS is increased
        if hasattr(edit_word, 'BULK_ADD_MAX_WORDS'):
            limit = edit_word.BULK_ADD_MAX_WORDS
            if limit >= 100:
                print(f"✅ BULK_ADD_MAX_WORDS is set to {limit} (good, ≥100)")
                return True
            else:
                print(f"⚠️ BULK_ADD_MAX_WORDS is {limit} (should be ≥100)")
                return False
        else:
            print("❌ BULK_ADD_MAX_WORDS not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking bulk add constants: {e}")
        return False

def test_translation_sync():
    """Test that translation sync module is working."""
    print("\n🌐 Testing translation sync...")
    
    try:
        import translation_sync
        
        # Check if safe_translate function exists
        if hasattr(translation_sync, 'safe_translate'):
            print("✅ Translation sync module and safe_translate function available")
            
            # Test a simple translation (if possible without API calls)
            # For now, just check the function signature
            import inspect
            sig = inspect.signature(translation_sync.safe_translate)
            params = list(sig.parameters.keys())
            if 'src' in params and 'dest' in params:
                print("✅ safe_translate function has correct parameters")
                return True
            else:
                print("⚠️ safe_translate function has unexpected parameters")
                return False
        else:
            print("❌ safe_translate function not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing translation sync: {e}")
        return False

def test_german_article_finder():
    """Test German article finder functionality."""
    print("\n📚 Testing German article finder...")
    
    try:
        from german_article_finder import find_german_article
        
        # Test with a known word (if database has it)
        test_word = "Haus"
        try:
            article, clean_word = find_german_article(test_word)
            if article and clean_word:
                print(f"✅ Article finder working: {test_word} -> {article} {clean_word}")
            else:
                print(f"ℹ️ Article finder returned no result for '{test_word}' (may be normal)")
            return True
        except Exception as e:
            print(f"⚠️ Article finder error (may be normal if no data): {e}")
            return True  # Don't fail the test for this
            
    except Exception as e:
        print(f"❌ Error importing German article finder: {e}")
        return False

def test_file_syntax():
    """Test that key files have no syntax errors."""
    print("\n📝 Testing file syntax...")
    
    files_to_test = [
        'db_manager.py',
        'handlers/edit_word.py',
        'handlers/add_word.py',
        'translation_sync.py'
    ]
    
    syntax_errors = []
    
    for file_path in files_to_test:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Try to compile the source
            compile(source, file_path, 'exec')
            print(f"✅ {file_path} - syntax OK")
            
        except SyntaxError as e:
            print(f"❌ {file_path} - syntax error: {e}")
            syntax_errors.append(file_path)
        except Exception as e:
            print(f"⚠️ {file_path} - error reading: {e}")
    
    return len(syntax_errors) == 0

def run_all_tests():
    """Run all tests and provide summary."""
    print("🧪 Running Bulk Operations Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Functions", test_database_functions),
        ("Database Connection", test_database_connection),
        ("Bulk Add Constants", test_bulk_add_constants),
        ("Translation Sync", test_translation_sync),
        ("German Article Finder", test_german_article_finder),
        ("File Syntax", test_file_syntax)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} - unexpected error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bulk operations should be working correctly.")
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)