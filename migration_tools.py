# -*- coding: utf-8 -*-

"""
Утиліти для міграції даних зі старих версій бази даних.
"""

import sqlite3
import os

def migrate_shared_dictionary_users():
    """
    Міграція даних про користувачів спільних словників
    зі старої схеми в нову таблицю shared_dict_users.
    """
    DB_DIR = "database"
    DB_PATH = os.path.join(DB_DIR, "german_words.db")
    
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Перевіряємо, чи існує таблиця shared_dict_users
    cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='shared_dict_users'
    """)
    if not cursor.fetchone():
        print("Creating shared_dict_users table...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_dict_users (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            dict_id INTEGER NOT NULL,
            is_admin INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(chat_id),
            FOREIGN KEY (dict_id) REFERENCES shared_dictionaries(id),
            UNIQUE(user_id, dict_id)
        )
        ''')
    
    # Отримуємо всіх користувачів зі значеннями shared_dict_id
    cursor.execute("""
    SELECT chat_id, shared_dict_id, shared_dict_admin 
    FROM users 
    WHERE shared_dict_id IS NOT NULL
    """)
    users_with_shared_dicts = cursor.fetchall()
    
    if not users_with_shared_dicts:
        print("No users with shared dictionaries found")
        conn.close()
        return False
    
    # Додаємо записи в нову таблицю
    migrated_count = 0
    for chat_id, shared_dict_id, is_admin in users_with_shared_dicts:
        try:
            # Додаємо запис тільки якщо такого зв'язку ще немає
            cursor.execute("""
            INSERT OR IGNORE INTO shared_dict_users 
            (user_id, dict_id, is_admin, joined_at) 
            VALUES (?, ?, ?, datetime('now'))
            """, (chat_id, shared_dict_id, 1 if is_admin else 0))
            
            # Знаходимо словники, створені цим користувачем
            cursor.execute("""
            SELECT id FROM shared_dictionaries 
            WHERE created_by = ?
            """, (chat_id,))
            
            for (dict_id,) in cursor.fetchall():
                cursor.execute("""
                INSERT OR IGNORE INTO shared_dict_users 
                (user_id, dict_id, is_admin, joined_at) 
                VALUES (?, ?, 1, datetime('now'))
                """, (chat_id, dict_id))
            
            migrated_count += 1
        except Exception as e:
            print(f"Error migrating user {chat_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"Migration complete: {migrated_count} users migrated to shared_dict_users table")
    return True

def fix_dictionary_admin_status():
    """
    Виправлення статусу адміністраторів словників:
    Встановлює is_admin=1 для користувачів, які створили словник, але не мають статусу адмін
    """
    DB_DIR = "database"
    DB_PATH = os.path.join(DB_DIR, "german_words.db")
    
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Спочатку переконаємося, що існують потрібні таблиці
    cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='shared_dictionaries'
    """)
    if not cursor.fetchone():
        print("Table 'shared_dictionaries' not found")
        conn.close()
        return False
    
    # Отримуємо всі словники та їх творців
    cursor.execute("""
    SELECT id, created_by, name FROM shared_dictionaries
    """)
    dictionaries = cursor.fetchall()
    
    fixed_count = 0
    for dict_id, created_by, dict_name in dictionaries:
        if not created_by:
            continue
            
        # Переконаємося, що творець має відмітку адміна в users
        cursor.execute("""
        UPDATE users 
        SET shared_dict_admin = 1 
        WHERE chat_id = ? AND (shared_dict_admin IS NULL OR shared_dict_admin = 0)
        """, (created_by,))
        
        # Переконаємося, що є запис в shared_dict_users і творець має статус адміна
        cursor.execute("""
        INSERT OR REPLACE INTO shared_dict_users (user_id, dict_id, is_admin, joined_at)
        VALUES (?, ?, 1, datetime('now'))
        """, (created_by, dict_id))
        
        fixed_count += 1
        print(f"Fixed admin status for dictionary '{dict_name}' (ID: {dict_id}) - creator: {created_by}")
    
    conn.commit()
    conn.close()
    
    print(f"Fixed admin status for {fixed_count} dictionaries")
    return True

if __name__ == "__main__":
    migrate_shared_dictionary_users()
    fix_dictionary_admin_status()
