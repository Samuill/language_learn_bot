# -*- coding: utf-8 -*-
import os
import re
import random
import string
import datetime
import sqlite3
import pandas as pd
from config import ADMIN_ID
from db_init import create_user_table, create_database, migrate_from_csv

# Шлях до бази даних
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "german_words.db")

def get_connection():
    """Get a connection to the database, creating it if needed"""
    if not os.path.exists(DB_PATH):
        
        create_database()
        
        # Також виконаємо міграцію даних з CSV, якщо база щойно створена
        
        migrate_from_csv()
    
    return sqlite3.connect(DB_PATH)

def user_exists(chat_id):
    """Check if user exists in database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT 1 FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone() is not None
    
    conn.close()
    
    return result

def initialize_user(chat_id, language):
    """Initialize a new user in the database with specified language"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Add user to users table if not exists
    cursor.execute('INSERT OR IGNORE INTO users (chat_id, language) VALUES (?, ?)', 
                 (chat_id, language))
    
    # Create user dictionary table if not exists
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS user_{chat_id} (
        id INTEGER PRIMARY KEY,
        word_id INTEGER,
        rating REAL DEFAULT 0.0,
        FOREIGN KEY (word_id) REFERENCES words(id),
        UNIQUE(word_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    return True

def get_user_language(chat_id):
    """Get user language from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT language FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    else:
        return None

def set_user_language(chat_id, language):
    """Set or update user language"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT 1 FROM users WHERE chat_id = ?', (chat_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE users SET language = ? WHERE chat_id = ?', (language, chat_id))
    else:
        cursor.execute('INSERT INTO users (chat_id, language) VALUES (?, ?)', (chat_id, language))
        
        # Create user table
        create_user_table(chat_id)
    
    conn.commit()
    conn.close()
    
    return language

def get_user_words(chat_id, dict_type="personal"):
    """Get words for a user as a DataFrame"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Визначаємо, який словник використовувати
    if dict_type == "common":
        # Загальний словник - вибираємо всі слова
        language = get_user_language(chat_id) or "uk"
        print(f"Getting common dictionary words for user {chat_id} in language {language}")
        
        query = f'''
        SELECT w.id, w.word, w.{language}_tran as translation, a.article, 0.0 as priority
        FROM words w
        LEFT JOIN article a ON w.article_id = a.id
        WHERE w.{language}_tran IS NOT NULL
        '''
        cursor.execute(query)
    else:
        # Персональний словник - вибираємо слова користувача
        language = get_user_language(chat_id)
        if not language:
            print(f"Cannot determine language for user {chat_id}")
            conn.close()
            return pd.DataFrame()
        
        print(f"Getting personal dictionary for user {chat_id} in language {language}")
        
        # Перевіряємо, чи існує таблиця для користувача
        cursor.execute(f"""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='user_{chat_id}'
        """)
        if not cursor.fetchone():
            print(f"No table found for user {chat_id}")
            conn.close()
            return pd.DataFrame()
        
        query = f'''
        SELECT w.id, w.word, w.{language}_tran as translation, a.article, u.rating
        FROM user_{chat_id} u
        JOIN words w ON u.word_id = w.id
        LEFT JOIN article a ON w.article_id = a.id
        WHERE w.{language}_tran IS NOT NULL
        ORDER BY u.rating ASC
        '''
        cursor.execute(query)
    
    # Отримуємо результати
    results = cursor.fetchall()
    
    # Convert results to DataFrame
    columns = ['id', 'word', 'translation', 'article', 'priority']
    df = pd.DataFrame(results, columns=columns)
    
    print(f"Found {len(df)} words for user {chat_id} with dict_type={dict_type}")
    
    conn.close()
    
    return df

def add_word(chat_id, word, translation, dict_type="personal", article=None):
    """Add a word to user's dictionary with duplicate handling and article update"""
    # Check if user can add to common dictionary
    if dict_type == "common" and chat_id != ADMIN_ID:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get user language
    language = get_user_language(chat_id)
    if not language:
        conn.close()
        return False
    
    # Перевіряємо, чи є в слові артикль

    article_match = re.match(r'^(der|die|das)\s+(.+)$', word, re.IGNORECASE)
    extracted_article = None
    if article_match:
        # Якщо знайшли артикль в слові
        extracted_article = article_match.group(1).lower()
        word = article_match.group(2).strip()
    
    # Визначаємо ID артикля (якщо він є)
    article_id = None
    if extracted_article or article:
        article_to_use = extracted_article or article
        cursor.execute('SELECT id FROM article WHERE LOWER(article) = LOWER(?)', (article_to_use,))
        result = cursor.fetchone()
        if result:
            article_id = result[0]
    
    # Якщо артикль не знайдено, використовуємо порожній артикль (ID = 4)
    if not article_id:
        article_id = 4  # Empty article by default
    
    # Перевірка на дублікати - шукаємо слово не залежно від регістру
    cursor.execute('SELECT id, article_id FROM words WHERE LOWER(word) = LOWER(?)', (word,))
    existing_words = cursor.fetchall()
    
    if existing_words:
        # Слово(а) існує, перевіряємо чи є дублікати і які артиклі вже задані
        duplicate_ids = []
        best_word_id = None
        best_has_article = False
        
        for word_id, existing_article_id in existing_words:
            # Якщо у нас є артикль і існуюче слово немає артикля, зберігаємо це слово для оновлення
            has_article = existing_article_id != 4 and existing_article_id is not None
            
            if not best_word_id or (article_id != 4 and not best_has_article and has_article):
                best_word_id = word_id
                best_has_article = has_article
            else:
                # Додаємо інші слова в список дублікатів
                duplicate_ids.append(word_id)
        
        # Оновлюємо переклад для обраного слова і можливо артикль
        if article_id != 4 and not best_has_article:
            # Оновлюємо артикль для слова, якщо в нього не було артикля
            cursor.execute(f'UPDATE words SET {language}_tran = ?, article_id = ? WHERE id = ?', 
                         (translation, article_id, best_word_id))
        else:
            # Просто оновлюємо переклад, якщо артикль вже був або ми не надаємо нового
            cursor.execute(f'UPDATE words SET {language}_tran = ? WHERE id = ?', 
                         (translation, best_word_id))
        
        word_id = best_word_id
        
        # Обробка дублікатів
        if duplicate_ids:
            print(f"Found {len(duplicate_ids)} duplicates for word '{word}', merging to word_id={word_id}")
            for dup_id in duplicate_ids:
                # Знаходимо користувачів, у яких є це слово
                cursor.execute(f"SELECT 'user_' || chat_id FROM users")
                user_tables = [row[0] for row in cursor.fetchall()]
                
                for user_table in user_tables:
                    try:
                        # Перевіряємо чи користувач має дублікат
                        cursor.execute(f"SELECT 1 FROM {user_table} WHERE word_id = ?", (dup_id,))
                        if cursor.fetchone():
                            # Перевіряємо чи користувач вже має основне слово
                            cursor.execute(f"SELECT 1 FROM {user_table} WHERE word_id = ?", (word_id,))
                            has_main_word = cursor.fetchone() is not None
                            
                            if has_main_word:
                                # Видаляємо дублікат, основне слово вже є
                                cursor.execute(f"DELETE FROM {user_table} WHERE word_id = ?", (dup_id,))
                                print(f"Deleted duplicate word_id={dup_id} from {user_table}, already has main word")
                            else:
                                # Оновлюємо word_id з дубліката на основне слово
                                cursor.execute(f"UPDATE {user_table} SET word_id = ? WHERE word_id = ?", 
                                             (word_id, dup_id))
                                print(f"Updated in {user_table}: word_id {dup_id} -> {word_id}")
                    except Exception as e:
                        print(f"Error processing duplicate for {user_table}: {e}")
                        continue
    else:
        # Слово не існує, додаємо нове
        # Переконаймося, що слово починається з великої літери, якщо це іменник
        if all(c.islower() or not c.isalpha() for c in word):
            is_noun = article_id != 4 and article_id is not None  # Якщо є артикль, це іменник
            if is_noun:
                word = word.capitalize()
        
        cursor.execute('''
        INSERT INTO words (article_id, word, ru_tran, uk_tran)
        VALUES (?, ?, ?, ?)
        ''', (
            4,  # Empty article by default
            word,
            translation if language == 'ru' else None,
            translation if language == 'uk' else None
        ))
        word_id = cursor.lastrowid
    
    # If it's a personal dictionary, add reference to user's table
    if dict_type == "personal":
        # Ensure user table exists
        
        create_user_table(chat_id)
        
        # Add word to user's table if not exists
        cursor.execute(f'''
        INSERT OR IGNORE INTO user_{chat_id} (word_id, rating)
        VALUES (?, ?)
        ''', (word_id, 0.0))
    
    conn.commit()
    conn.close()
    
    return True

def update_word_rating(chat_id, word_id, change, dict_type="personal"):
    """Update word rating for a user with step 0.1, constrained between 0 and 5"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if dict_type == "personal":
        # Спочатку отримуємо поточний рейтинг
        cursor.execute(f'''
        SELECT rating FROM user_{chat_id} WHERE word_id = ?
        ''', (word_id,))
        result = cursor.fetchone()
        
        if result:
            current_rating = result[0]
            # Застосовуємо зміну з кроком 0.1
            new_rating = max(min(current_rating + change, 5.0), 0.0)
            # Округлюємо до однієї цифри після коми для стабільного збереження
            new_rating = round(new_rating, 1)
            
            # Оновлюємо рейтинг
            cursor.execute(f'''
            UPDATE user_{chat_id} 
            SET rating = ?
            WHERE word_id = ?
            ''', (new_rating, word_id))
            
            print(f"Updated rating for user {chat_id}, word_id {word_id}: {current_rating} -> {new_rating}")
        else:
            print(f"Warning: Word {word_id} not found in user_{chat_id} table")
    else:
        # Common dictionary - can't update ratings
        pass
    
    conn.commit()
    conn.close()
    
    return True

def get_user_streak(chat_id):
    """Get user's streak"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT streak, last_active FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0], result[1]
    else:
        return 0, None

def update_user_streak(chat_id):
    """Update user's streak"""

    
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.datetime.now().date()
    today_str = today.isoformat()
    
    # Get current streak and last active day
    cursor.execute('SELECT streak, last_active FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    
    if result:
        streak, last_active_str = result
        
        if last_active_str:
            last_active = datetime.date.fromisoformat(last_active_str)
            delta = (today - last_active).days
            
            if delta == 1:
                # Consecutive day
                streak += 1
            elif delta > 1:
                # Streak broken
                streak = 1
            # If delta == 0, same day, keep streak
        else:
            # First activity
            streak = 1
    else:
        # User doesn't exist, create entry
        cursor.execute('INSERT INTO users (chat_id, streak, last_active) VALUES (?, 1, ?)', 
                     (chat_id, today_str))
        streak = 1
    
    # Update streak and last_active
    cursor.execute('UPDATE users SET streak = ?, last_active = ? WHERE chat_id = ?',
                 (streak, today_str, chat_id))
    
    conn.commit()
    conn.close()
    
    return streak

def create_shared_dictionary_tables():
    """Create tables for shared dictionaries if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблиця для зберігання інформації про спільні словники
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shared_dictionaries (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        created_by INTEGER,
        created_at TEXT,
        FOREIGN KEY (created_by) REFERENCES users(chat_id)
    )
    ''')
    
    # Додати колонку shared_dict_admin до таблиці users, якщо вона не існує
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "shared_dict_admin" not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN shared_dict_admin INTEGER DEFAULT 0')
    
    # Додати колонку shared_dict_id до таблиці users, якщо вона не існує
    if "shared_dict_id" not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN shared_dict_id INTEGER DEFAULT NULL')
    
    conn.commit()
    conn.close()

def create_shared_dictionary(chat_id, name):
    """Create a new shared dictionary with a random code"""

    # Генеруємо випадковий код з 6 символів (літери верхнього регістру та цифри)
    code_chars = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(code_chars) for _ in range(6))
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Створюємо запис про словник
    cursor.execute('''
    INSERT INTO shared_dictionaries (name, code, created_by, created_at)
    VALUES (?, ?, ?, datetime('now'))
    ''', (name, code, chat_id))
    
    # Отримуємо ID створеного словника
    shared_dict_id = cursor.lastrowid
    
    # Оновлюємо інформацію про користувача
    cursor.execute('''
    UPDATE users SET shared_dict_admin = 1, shared_dict_id = ? WHERE chat_id = ?
    ''', (shared_dict_id, chat_id))
    
    # Створюємо таблицю для слів цього словника
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS shared_dict_{shared_dict_id} (
        id INTEGER PRIMARY KEY,
        word_id INTEGER,
        FOREIGN KEY (word_id) REFERENCES words(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    return code, shared_dict_id

def join_shared_dictionary(chat_id, code):
    """Join a shared dictionary using its code"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Перевіряємо існування словника з таким кодом
    cursor.execute('SELECT id, name FROM shared_dictionaries WHERE code = ?', (code,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return False, "Словник з таким кодом не знайдено."
    
    shared_dict_id, dict_name = result
    
    # Перевіряємо, чи користувач вже приєднаний до цього словника
    cursor.execute('SELECT 1 FROM users WHERE chat_id = ? AND shared_dict_id = ?', 
                 (chat_id, shared_dict_id))
    if cursor.fetchone():
        conn.close()
        return False, f"Ви вже приєднані до словника '{dict_name}'."
    
    # Додаємо користувача до словника
    cursor.execute('UPDATE users SET shared_dict_id = ? WHERE chat_id = ?', 
                 (shared_dict_id, chat_id))
    
    # Створюємо колонку для користувача в таблиці словника, якщо її ще немає
    cursor.execute(f"PRAGMA table_info(shared_dict_{shared_dict_id})")
    columns = [col[1] for col in cursor.fetchall()]
    user_col = f"user_{chat_id}"
    
    if user_col not in columns:
        cursor.execute(f'''
        ALTER TABLE shared_dict_{shared_dict_id} ADD COLUMN {user_col} REAL DEFAULT 0.0
        ''')
    
    conn.commit()
    conn.close()
    
    return True, dict_name

def get_user_shared_dictionaries(chat_id):
    """Get list of shared dictionaries a user is part of"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Спершу перевіряємо словники, де користувач є учасником або адміністратором
    # Для цього використовуємо три підходи:
    # 1. Словник є активним для користувача (shared_dict_id)
    # 2. Користувач є адміністратором цього словника (shared_dict_admin = 1)
    # 3. Користувач має колонку в таблиці спільного словника
    
    # Збираємо всі можливі словники з трьох підходів
    shared_dicts = []
    
    # Підхід 1: активний словник
    cursor.execute('''
    SELECT sd.id, sd.name, sd.code, u.shared_dict_admin 
    FROM shared_dictionaries sd
    JOIN users u ON sd.id = u.shared_dict_id
    WHERE u.chat_id = ?
    ''', (chat_id,))
    result = cursor.fetchone()
    
    if result:
        dict_id, name, code, is_admin = result
        shared_dicts.append({
            'id': dict_id,
            'name': name,
            'code': code,
            'is_admin': bool(is_admin)
        })
    
    # Підхід 2: користувач є адміністратором
    cursor.execute('''
    SELECT sd.id, sd.name, sd.code
    FROM shared_dictionaries sd
    JOIN users u ON sd.created_by = u.chat_id
    WHERE u.chat_id = ? AND (u.shared_dict_admin = 1 OR sd.created_by = ?)
    ''', (chat_id, chat_id))
    
    for dict_id, name, code in cursor.fetchall():
        # Перевіряємо, чи не додали вже цей словник
        if not any(d['id'] == dict_id for d in shared_dicts):
            shared_dicts.append({
                'id': dict_id,
                'name': name,
                'code': code,
                'is_admin': True  # Якщо користувач творець, він адміністратор
            })
    
    # Підхід 3: ми повинні перевірити всі таблиці shared_dict_*, чи містять вони колонки для користувача
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'shared_dict_%'")
    tables = [row[0] for row in cursor.fetchall()]
    
    for table in tables:
        try:
            # Витягуємо ID зі назви таблиці
            dict_id = int(table.replace('shared_dict_', ''))
            
            # Перевіряємо, чи словник вже доданий
            if any(d['id'] == dict_id for d in shared_dicts):
                continue
                
            # Отримуємо інформацію про цей словник
            cursor.execute('SELECT name, code FROM shared_dictionaries WHERE id = ?', (dict_id,))
            dict_info = cursor.fetchone()
            
            if not dict_info:
                continue
                
            name, code = dict_info
            
            # Перевіряємо, чи є колонка user_{chat_id} в цій таблиці
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            user_col = f"user_{chat_id}"
            
            # Або перевіряємо, чи є слова додані цим користувачем
            has_words = False
            if user_col in columns:
                has_words = True
            
            # Також перевіряємо, чи є записи в таблиці для цього користувача
            cursor.execute(f"SELECT EXISTS (SELECT 1 FROM {table} LIMIT 1)")
            table_has_data = cursor.fetchone()[0]
            
            # Якщо є дані і користувач має доступ
            if table_has_data and has_words:
                # Перевіряємо статус адміністратора
                cursor.execute('SELECT shared_dict_admin FROM users WHERE chat_id = ?', (chat_id,))
                is_admin_result = cursor.fetchone()
                is_admin = bool(is_admin_result and is_admin_result[0])
                
                shared_dicts.append({
                    'id': dict_id,
                    'name': name,
                    'code': code,
                    'is_admin': is_admin
                })
        except Exception as e:
            print(f"Error checking shared dict table {table}: {e}")
            continue
    
    conn.close()
    
    return shared_dicts

def get_shared_dictionary_words(chat_id, shared_dict_id=None):
    """Get words from a shared dictionary for a specific user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Якщо shared_dict_id не вказано, отримуємо його з профілю користувача
    if not shared_dict_id:
        cursor.execute('SELECT shared_dict_id FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            conn.close()
            return pd.DataFrame()
        shared_dict_id = result[0]
    
    # Отримуємо мову користувача
    language = get_user_language(chat_id) or "uk"
    
    # Перевіряємо, чи існує таблиця для цього словника
    cursor.execute(f"""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='shared_dict_{shared_dict_id}'
    """)
    if not cursor.fetchone():
        conn.close()
        return pd.DataFrame()
    
    # Перевіряємо, чи є колонка для цього користувача
    cursor.execute(f"PRAGMA table_info(shared_dict_{shared_dict_id})")
    columns = [col[1] for col in cursor.fetchall()]
    user_col = f"user_{chat_id}"
    
    if user_col not in columns:
        # Якщо колонки немає, додаємо її
        cursor.execute(f'''
        ALTER TABLE shared_dict_{shared_dict_id} ADD COLUMN {user_col} REAL DEFAULT 0.0
        ''')
        conn.commit()
    
    # Отримуємо слова зі спільного словника з рейтингами для цього користувача
    query = f'''
    SELECT w.id, w.word, w.{language}_tran as translation, a.article, sd.{user_col} as priority
    FROM shared_dict_{shared_dict_id} sd
    JOIN words w ON sd.word_id = w.id
    LEFT JOIN article a ON w.article_id = a.id
    WHERE w.{language}_tran IS NOT NULL
    ORDER BY sd.{user_col} ASC
    '''
    cursor.execute(query)
    
    # Отримуємо результати
    results = cursor.fetchall()
    
    # Convert results to DataFrame
    columns = ['id', 'word', 'translation', 'article', 'priority']
    df = pd.DataFrame(results, columns=columns)
    
    conn.close()
    
    return df

def add_word_to_shared_dictionary(chat_id, word_id, shared_dict_id=None):
    """Add a word to a shared dictionary"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Якщо shared_dict_id не вказано, отримуємо його з профілю користувача
    if not shared_dict_id:
        cursor.execute('SELECT shared_dict_id, shared_dict_admin FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            conn.close()
            return False, "Ви не є учасником жодного спільного словника."
        
        shared_dict_id, is_admin = result
        
        # Перевіряємо, чи користувач є адміністратором словника
        if not is_admin:
            conn.close()
            return False, "Тільки адміністратор може додавати слова до спільного словника."
    
    # Перевіряємо, чи слово вже є у спільному словнику
    cursor.execute(f'''
    SELECT 1 FROM shared_dict_{shared_dict_id} 
    WHERE word_id = ?
    ''', (word_id,))
    
    if cursor.fetchone():
        conn.close()
        return True, "Слово вже є у спільному словнику."
    
    # Додаємо слово до спільного словника
    cursor.execute(f'''
    INSERT INTO shared_dict_{shared_dict_id} (word_id)
    VALUES (?)
    ''', (word_id,))
    
    conn.commit()
    conn.close()
    
    return True, "Слово успішно додано до спільного словника."

def update_word_rating_shared_dict(chat_id, word_id, change, shared_dict_id=None):
    """Update word rating for a user in shared dictionary"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Якщо shared_dict_id не вказано, отримуємо його з профілю користувача
    if not shared_dict_id:
        cursor.execute('SELECT shared_dict_id FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            conn.close()
            return False
        shared_dict_id = result[0]
    
    user_col = f"user_{chat_id}"
    
    # Перевіряємо, чи є колонка для цього користувача
    cursor.execute(f"PRAGMA table_info(shared_dict_{shared_dict_id})")
    columns = [col[1] for col in cursor.fetchall()]
    
    if user_col not in columns:
        # Якщо колонки немає, додаємо її
        cursor.execute(f'''
        ALTER TABLE shared_dict_{shared_dict_id} ADD COLUMN {user_col} REAL DEFAULT 0.0
        ''')
        conn.commit()
    
    # Отримуємо поточний рейтинг слова для користувача
    cursor.execute(f'''
    SELECT {user_col} FROM shared_dict_{shared_dict_id} 
    WHERE word_id = ?
    ''', (word_id,))
    
    result = cursor.fetchone()
    if result:
        current_rating = result[0] or 0.0
        # Застосовуємо зміну з обмеженнями
        new_rating = max(min(current_rating + change, 5.0), 0.0)
        # Округлюємо до однієї цифри після коми
        new_rating = round(new_rating, 1)
        
        # Оновлюємо рейтинг
        cursor.execute(f'''
        UPDATE shared_dict_{shared_dict_id}
        SET {user_col} = ?
        WHERE word_id = ?
        ''', (new_rating, word_id))
        
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False
