# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd
from config import ADMIN_ID

# Шлях до бази даних
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "german_words.db")

def get_connection():
    """Get a connection to the database, creating it if needed"""
    if not os.path.exists(DB_PATH):
        from db_init import create_database
        create_database()
        
        # Також виконаємо міграцію даних з CSV, якщо база щойно створена
        from db_init import migrate_from_csv
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
        from db_init import create_user_table
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
        ORDER BY priority ASC
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
    import re
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
            article_id,
            word,
            translation if language == 'ru' else None,
            translation if language == 'uk' else None
        ))
        word_id = cursor.lastrowid
    
    # If it's a personal dictionary, add reference to user's table
    if dict_type == "personal":
        # Ensure user table exists
        from db_init import create_user_table
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
    import datetime
    
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
