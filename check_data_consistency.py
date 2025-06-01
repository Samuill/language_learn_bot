# -*- coding: utf-8 -*-
import os
import pandas as pd
import sqlite3
import re
from db_manager import DB_PATH
from storage import USER_DICT_DIR

def check_data_consistency():
    """Compare data between CSV files and SQLite database"""
    print("=== CHECKING DATA CONSISTENCY ===")
    
    # Перевіряємо, чи існує база даних
    if not os.path.exists(DB_PATH):
        print(f"SQLite database not found at {DB_PATH}")
        return
    
    # Підключаємося до бази даних
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Перевіряємо кількість слів у базі даних
    cursor.execute("SELECT COUNT(*) FROM words")
    word_count_db = cursor.fetchone()[0]
    print(f"Words in SQLite database: {word_count_db}")
    
    # Знаходимо всі CSV файли користувачів
    user_dict_pattern = os.path.join(USER_DICT_DIR, "*_words_*.csv")
    import glob
    user_dict_files = glob.glob(user_dict_pattern)
    
    total_words_csv = 0
    total_users_csv = len(user_dict_files)
    
    # Словник для підрахунку слів по користувачах
    user_words_counts = {}
    
    for file_path in user_dict_files:
        try:
            # Отримуємо ID користувача з імені файлу
            file_name = os.path.basename(file_path)
            match = re.search(r'_words_(\d+)\.csv$', file_name)
            if not match:
                continue
                
            chat_id = int(match.group(1))
            
            # Читаємо CSV файл
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            word_count_csv = len(df)
            total_words_csv += word_count_csv
            
            # Додаємо користувача та кількість слів у словник
            user_words_counts[chat_id] = word_count_csv
            
            # Перевіряємо наявність користувача в базі даних
            cursor.execute("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,))
            user_exists = cursor.fetchone() is not None
            
            # Перевіряємо наявність таблиці користувача
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='user_{chat_id}'")
            table_exists = cursor.fetchone() is not None
            
            # Якщо таблиця існує, підрахуємо кількість слів у ній
            word_count_user_db = 0
            if table_exists:
                cursor.execute(f"SELECT COUNT(*) FROM user_{chat_id}")
                word_count_user_db = cursor.fetchone()[0]
            
            print(f"User {chat_id}: CSV={word_count_csv}, SQLite={word_count_user_db}, "
                  f"{'✅' if word_count_csv == word_count_user_db else '❌'}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Отримуємо кількість користувачів із бази даних
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count_db = cursor.fetchone()[0]
    
    print("\n=== SUMMARY ===")
    print(f"Users in CSV files: {total_users_csv}")
    print(f"Users in SQLite database: {user_count_db}")
    print(f"Total words in SQLite database: {word_count_db}")
    
    conn.close()
    
    print("===========================")

if __name__ == "__main__":
    check_data_consistency()
