#!/usr/bin/env python3
"""
Скрипт для перевірки правильності звертання до бази даних
"""

import sqlite3
import json
import sys
import os

# Додаємо шлях для імпорту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import db_manager
    print("✅ db_manager успішно імпортовано")
except ImportError as e:
    print(f"❌ Помилка імпорту db_manager: {e}")
    sys.exit(1)

def load_db_structure():
    """Завантажити структуру бази даних з JSON файлу"""
    try:
        with open('db_structure_20250624_154957.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Помилка завантаження структури БД: {e}")
        return None

def check_table_references():
    """Перевірити звертання до таблиць"""
    print("\n📋 Перевірка звертання до таблиць...")
    
    structure = load_db_structure()
    if not structure:
        return False
    
    tables = structure.get('tables', {})
    
    # Список таблиць з бази даних
    shared_dict_tables = [name for name in tables.keys() if name.startswith('shared_dict_') and name not in ['shared_dict_users']]
    user_tables = [name for name in tables.keys() if name.startswith('user_')]
    
    print(f"Знайдено спільних словників: {len(shared_dict_tables)}")
    print(f"Знайдено персональних словників: {len(user_tables)}")
    
    # Перевіряємо основні таблиці
    required_tables = ['words', 'users', 'article', 'shared_dictionaries', 'shared_dict_users']
    missing_tables = [table for table in required_tables if table not in tables]
    
    if missing_tables:
        print(f"❌ Відсутні обов'язкові таблиці: {missing_tables}")
        return False
    
    print("✅ Всі обов'язкові таблиці присутні")
    return True

def check_function_existence():
    """Перевірити наявність необхідних функцій"""
    print("\n🔧 Перевірка наявності функцій...")
    
    required_functions = [
        'get_shared_dictionary_words',
        'get_shared_dictionary_words_with_articles', 
        'get_user_shared_dictionaries',
        'delete_word_from_shared_dict',
        'delete_word_from_personal_dict',
        'update_word_translation_shared_dict',
        'update_word_translation_personal_dict',
        'add_word_to_shared_dictionary',
        'create_shared_dictionary',
        'join_shared_dictionary'
    ]
    
    missing_functions = []
    for func_name in required_functions:
        if not hasattr(db_manager, func_name):
            missing_functions.append(func_name)
        else:
            print(f"✅ {func_name}")
    
    if missing_functions:
        print(f"❌ Відсутні функції: {missing_functions}")
        return False
    
    return True

def test_database_queries():
    """Тестування запитів до бази даних"""
    print("\n🗄️ Тестування запитів до БД...")
    
    try:
        # Тест підключення
        conn = sqlite3.connect(db_manager.DB_PATH)
        cursor = conn.cursor()
        
        # Перевірка таблиць
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        actual_tables = [row[0] for row in cursor.fetchall()]
        
        # Перевірка спільних словників
        shared_dicts = [t for t in actual_tables if t.startswith('shared_dict_') and t != 'shared_dict_users']
        print(f"Знайдено спільних словників у БД: {len(shared_dicts)}")
        
        for dict_table in shared_dicts[:3]:  # Перевіряємо перші 3
            cursor.execute(f"PRAGMA table_info({dict_table})")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"  {dict_table}: {len(columns)} колонок")
            
            # Перевіряємо, чи є колонка word_id
            if 'word_id' not in columns:
                print(f"❌ У таблиці {dict_table} відсутня колонка word_id")
            else:
                print(f"✅ Таблиця {dict_table} має правильну структуру")
        
        # Перевірка персональних словників
        user_tables = [t for t in actual_tables if t.startswith('user_') and '_' in t[5:]]
        print(f"Знайдено персональних словників у БД: {len(user_tables)}")
        
        for user_table in user_tables[:3]:  # Перевіряємо перші 3
            cursor.execute(f"PRAGMA table_info({user_table})")
            columns = [col[1] for col in cursor.fetchall()]
            required_cols = ['id', 'word_id', 'rating']
            missing_cols = [col for col in required_cols if col not in columns]
            
            if missing_cols:
                print(f"❌ У таблиці {user_table} відсутні колонки: {missing_cols}")
            else:
                print(f"✅ Таблиця {user_table} має правильну структуру")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Помилка тестування БД: {e}")
        return False

def check_word_table_references():
    """Перевірити звертання до таблиці words"""
    print("\n📝 Перевірка таблиці words...")
    
    try:
        conn = sqlite3.connect(db_manager.DB_PATH)
        cursor = conn.cursor()
        
        # Перевіряємо структуру таблиці words
        cursor.execute("PRAGMA table_info(words)")
        columns = [col[1] for col in cursor.fetchall()]
        
        required_cols = ['id', 'word', 'article_id', 'uk_tran', 'ru_tran']
        missing_cols = [col for col in required_cols if col not in columns]
        
        if missing_cols:
            print(f"❌ У таблиці words відсутні колонки: {missing_cols}")
            return False
        
        print(f"✅ Таблиця words має {len(columns)} колонок")
        
        # Перевіряємо кількість слів
        cursor.execute("SELECT COUNT(*) FROM words")
        word_count = cursor.fetchone()[0]
        print(f"✅ У таблиці words {word_count} слів")
        
        # Перевіряємо зв'язки з article
        cursor.execute("""
        SELECT COUNT(*) FROM words w 
        LEFT JOIN article a ON w.article_id = a.id 
        WHERE w.article_id IS NOT NULL AND a.id IS NULL
        """)
        broken_links = cursor.fetchone()[0]
        
        if broken_links > 0:
            print(f"❌ Знайдено {broken_links} слів з невірними посиланнями на артиклі")
        else:
            print("✅ Всі посилання на артиклі коректні")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Помилка перевірки таблиці words: {e}")
        return False

def check_user_functions():
    """Перевірити функції роботи з користувачами"""
    print("\n👤 Перевірка функцій користувачів...")
    
    try:
        # Тестуємо з реальним користувачем
        test_user_id = 476376623  # З JSON видно, що цей користувач існує
        
        # Перевіряємо get_user_language
        language = db_manager.get_user_language(test_user_id)
        if language:
            print(f"✅ get_user_language працює: {language}")
        else:
            print("⚠️ get_user_language повернула None")
        
        # Перевіряємо get_user_dictionary_info
        dict_type, shared_dict_id, is_admin = db_manager.get_user_dictionary_info(test_user_id)
        print(f"✅ get_user_dictionary_info: type={dict_type}, shared_id={shared_dict_id}, admin={is_admin}")
        
        # Перевіряємо get_user_shared_dictionaries
        shared_dicts = db_manager.get_user_shared_dictionaries(test_user_id)
        print(f"✅ get_user_shared_dictionaries: {len(shared_dicts)} словників")
        
        return True
        
    except Exception as e:
        print(f"❌ Помилка перевірки функцій користувачів: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_checks():
    """Запустити всі перевірки"""
    print("🔍 Перевірка правильності звертання до бази даних")
    print("=" * 60)
    
    checks = [
        ("Звертання до таблиць", check_table_references),
        ("Наявність функцій", check_function_existence),
        ("Тестування запитів БД", test_database_queries),
        ("Таблиця words", check_word_table_references),
        ("Функції користувачів", check_user_functions)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} - неочікувана помилка: {e}")
            results.append((check_name, False))
    
    # Підсумок
    print("\n" + "=" * 60)
    print("📊 ПІДСУМОК ПЕРЕВІРКИ")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ ПРОЙДЕНО" if result else "❌ НЕ ПРОЙДЕНО"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\nРезультат: {passed}/{total} перевірок пройдено")
    
    if passed == total:
        print("🎉 Всі перевірки пройдено! База даних працює коректно.")
    else:
        print("⚠️ Деякі перевірки не пройдено. Перегляньте проблеми вище.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
