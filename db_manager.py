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

def add_word(chat_id, word, translation, dict_type="personal"):
    """Add a word to user's dictionary"""
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
    
    # Check if word already exists
    cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
    result = cursor.fetchone()
    
    if result:
        # Word exists, get its ID
        word_id = result[0]
        
        # Update translation for the language
        cursor.execute(f'UPDATE words SET {language}_tran = ? WHERE id = ?', (translation, word_id))
    else:
        # Word doesn't exist, add it
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
        from db_init import create_user_table
        create_user_table(chat_id)
        
        # Add word to user's table
        cursor.execute(f'''
        INSERT OR IGNORE INTO user_{chat_id} (word_id, rating)
        VALUES (?, ?)
        ''', (word_id, 0.0))
    
    conn.commit()
    conn.close()
    
    return True

def update_word_rating(chat_id, word_id, change, dict_type="personal"):
    """Update word rating for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if dict_type == "personal":
        # Update in user's table
        cursor.execute(f'''
        UPDATE user_{chat_id} 
        SET rating = max(min(rating + ?, 5.0), 0.0)
        WHERE word_id = ?
        ''', (change, word_id))
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
