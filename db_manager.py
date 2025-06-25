# -*- coding: utf-8 -*-
import os
import re
import random
import string
import datetime
import sqlite3
import pandas as pd
import traceback # Added for more detailed error logging
from config import ADMIN_ID
from db_init import create_user_table, create_database, migrate_from_csv
from utils.logging_utils import log_language, log_error, log_language_event
from concurrent.futures import ThreadPoolExecutor

# Шлях до бази даних - використовуємо абсолютний шлях відносно поточного файлу
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(SCRIPT_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "german_words.db")

# глобальний пул потоків для I/O-завдань
executor = ThreadPoolExecutor()

def get_connection():
    """Get a connection to the database, creating it if needed"""
    # Убедимся, что директория для базы данных существует
    if not os.path.exists(DB_DIR):
        print(f"Database directory {DB_DIR} does not exist. Creating...")
        os.makedirs(DB_DIR)
        
    # Логируем полный путь к базе данных
    full_db_path = os.path.abspath(DB_PATH)
    print(f"Database path: {full_db_path}")
    
    # Проверяем существование базы данных
    if not os.path.exists(DB_PATH):
        print(f"Database file {DB_PATH} does not exist. Creating new database...")
        create_database()
        migrate_from_csv()
    else:
        print(f"Database file {DB_PATH} found. Size: {os.path.getsize(DB_PATH)} bytes")
    
    # відкриваємо з таймаутом та вмикаємо WAL
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def execute_query(query, params=None, fetch_mode=None, commit=True):
    """
    Безопасно выполняет SQL-запрос и возвращает результат.
    
    Args:
        query: SQL-запрос
        params: Параметры запроса (список или кортеж)
        fetch_mode: Режим получения результата ('one', 'all', None)
        commit: Нужно ли выполнить commit
    
    Returns:
        Результат запроса или None
    """
    conn = get_connection()
    cursor = conn.cursor()
    result = None
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        if fetch_mode == 'one':
            result = cursor.fetchone()
        elif fetch_mode == 'all':
            result = cursor.fetchall()
            
        if commit:
            conn.commit()
            
    except sqlite3.Error as e: # More specific exception
        print(f"SQL Error: {e}")
        print(f"Query: {query}")
        if params:
            print(f"Params: {params}")
        traceback.print_exc()
    except Exception as e: # Catch other potential errors
        print(f"Unexpected Error in execute_query: {e}")
        print(f"Query: {query}")
        if params:
            print(f"Params: {params}")
        traceback.print_exc()
        
    finally:
        conn.close()
        
    return result

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
    try:
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
    except sqlite3.Error as e:
        print(f"Error initializing user {chat_id}: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Unexpected error initializing user {chat_id}: {e}")
        traceback.print_exc()
        return False

def set_user_language(chat_id, language):
    """Set language for a user"""
    try:
        # Ensure chat_id is an integer
        chat_id = int(chat_id)
        
        # Print a debug message
        print(f"DB: Setting language for user {chat_id} to {language}")
        
        # Get a connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if the user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE chat_id = ?", (chat_id,))
        user_exists = cursor.fetchone()[0] > 0
        
        # Debug output - show table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print(f"DB DEBUG: Users table columns: {columns}")
        
        # Update or insert language
        if user_exists:
            print(f"DB: User {chat_id} exists, updating language to {language}")
            cursor.execute("UPDATE users SET language = ? WHERE chat_id = ?", (language, chat_id))
        else:
            print(f"DB: User {chat_id} does not exist, inserting with language {language}")
            cursor.execute("INSERT INTO users (chat_id, language) VALUES (?, ?)", (chat_id, language))
        
        # Commit and close
        conn.commit()
        rows_affected = conn.total_changes
        print(f"DB: Updated {rows_affected} rows")
        
        # Verify language was set correctly
        cursor.execute("SELECT language FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        print(f"DB: Verified language for user {chat_id}: {result[0] if result else 'None'}")
        
        conn.close()
        
        # Also clear the language cache in language_utils if it exists
        try:
            from utils.language_utils import clear_language_cache # Ensure this import is correct
            clear_language_cache(chat_id)
        except ImportError:
            print("Warning: clear_language_cache not found or language_utils not available.")
        except Exception as e:
            print(f"Error clearing language cache for user {chat_id}: {e}")
            
        return True
    except sqlite3.Error as e:
        print(f"Database error setting language for user {chat_id}: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Error setting language for user {chat_id}: {e}")
        traceback.print_exc()
        return False

def get_user_language(chat_id):
    """Get user language from database"""
    log_language("GET_LANG", chat_id, "Retrieving language from database")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT language FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            log_language_event(chat_id, "Language retrieved", result[0])
            return result[0]
        else:
            log_language_event(chat_id, "Language not found", "None")
            return None
    except sqlite3.Error as e:
        log_error(e, f"Database error getting language for user {chat_id}")
        return None
    except Exception as e:
        log_error(e, f"Unexpected error getting language for user {chat_id}")
        return None

def get_user_words(chat_id, dict_type="personal"):
    """Get words for a user as a DataFrame"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Визначаємо, який словник використовувати
        if dict_type == "common":
            # Загальний словник - вибираємо всі слова
            language = get_user_language(chat_id) or "en" # Default to 'en' if no language
            print(f"Getting common dictionary words for user {chat_id} in language {language}")
            
            # Handle different languages
            if language in ["en", "uk", "ru", "tr", "ar"]:
                query = f'''
                SELECT w.id, w.word, w.{language}_tran as translation, a.article, 0.0 as rating
                FROM words w
                LEFT JOIN article a ON w.article_id = a.id
                WHERE w.{language}_tran IS NOT NULL
                ORDER BY w.word
                '''
            else:
                print(f"Unsupported language '{language}' for common dictionary. Defaulting to 'en'.")
                query = '''
                SELECT w.id, w.word, w.en_tran as translation, a.article, 0.0 as rating
                FROM words w
                LEFT JOIN article a ON w.article_id = a.id
                WHERE w.en_tran IS NOT NULL
                ORDER BY w.word
                '''
            cursor.execute(query)
        else:
            # Персональний словник - вибираємо слова користувача
            language = get_user_language(chat_id)
            if not language:
                print(f"No language set for user {chat_id}. Cannot fetch personal dictionary.")
                return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])
            
            print(f"Getting personal dictionary for user {chat_id} in language {language}")
            
            # Перевіряємо, чи існує таблиця для користувача
            cursor.execute(f"""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_{chat_id}'
            """)
            if not cursor.fetchone():
                print(f"Personal dictionary table user_{chat_id} does not exist.")
                return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])
            
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
    except sqlite3.Error as e:
        print(f"Database error in get_user_words for user {chat_id}, dict_type {dict_type}: {e}")
        traceback.print_exc()
        return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])
    except Exception as e:
        print(f"Unexpected error in get_user_words for user {chat_id}, dict_type {dict_type}: {e}")
        traceback.print_exc()
        return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])


def get_user_words_with_articles(chat_id, dict_type="personal"):
    """Get words with defined articles (not NULL/empty) for a user as a DataFrame"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Визначаємо, який словник використовувати
        if dict_type == "common":
            # Загальний словник - вибираємо всі слова з артиклями
            language = get_user_language(chat_id) or "en"
            print(f"Getting common dictionary words with articles for user {chat_id} in language {language}")
            
            # Handle different languages
            if language in ["en", "uk", "ru", "tr", "ar"]:
                query = f'''
                SELECT w.id, w.word, w.{language}_tran as translation, a.article, 0.0 as rating
                FROM words w
                JOIN article a ON w.article_id = a.id
                WHERE w.{language}_tran IS NOT NULL AND a.article IS NOT NULL AND a.article != '' AND w.article_id != 4
                ORDER BY w.word
                '''
            else:
                print(f"Unsupported language '{language}' for common dictionary with articles. Defaulting to 'en'.")
                query = '''
                SELECT w.id, w.word, w.en_tran as translation, a.article, 0.0 as rating
                FROM words w
                JOIN article a ON w.article_id = a.id
                WHERE w.en_tran IS NOT NULL AND a.article IS NOT NULL AND a.article != '' AND w.article_id != 4
                ORDER BY w.word
                '''
            cursor.execute(query)
        else:
            # Персональний словник - вибираємо слова користувача з артиклями
            language = get_user_language(chat_id)
            if not language:
                print(f"No language set for user {chat_id}. Cannot fetch personal dictionary with articles.")
                return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])

            print(f"Getting personal dictionary with articles for user {chat_id} in language {language}")
            
            # Перевіряємо, чи існує таблиця для користувача
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='user_{chat_id}'")
            if not cursor.fetchone():
                print(f"Personal dictionary table user_{chat_id} does not exist.")
                return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])

            query = f'''
            SELECT w.id, w.word, w.{language}_tran as translation, a.article, u.rating
            FROM user_{chat_id} u
            JOIN words w ON u.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.{language}_tran IS NOT NULL AND a.article IS NOT NULL AND a.article != '' AND w.article_id != 4
            ORDER BY u.rating ASC
            '''
            cursor.execute(query)
        
        # Отримуємо результати
        results = cursor.fetchall()
        
        # Convert results to DataFrame
        columns = ['id', 'word', 'translation', 'article', 'priority']
        df = pd.DataFrame(results, columns=columns)
        
        print(f"Found {len(df)} words with articles for user {chat_id} with dict_type={dict_type}")
        
        conn.close()
        return df
    except sqlite3.Error as e:
        print(f"Database error in get_user_words_with_articles for user {chat_id}, dict_type {dict_type}: {e}")
        traceback.print_exc()
        return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])
    except Exception as e:
        print(f"Unexpected error in get_user_words_with_articles for user {chat_id}, dict_type {dict_type}: {e}")
        traceback.print_exc()
        return pd.DataFrame(columns=['id', 'word', 'translation', 'article', 'priority'])


def add_word(chat_id, word, translation, dict_type="personal", article=None):
    """Add a word to user's dictionary with duplicate handling and article update.
    Returns word_id on success, None on failure.
    """
    try:
        # Check if user can add to common dictionary
        if dict_type == "common" and chat_id != ADMIN_ID:
            print(f"User {chat_id} (not admin) attempted to add to common dictionary.")
            return None
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user language
        language = get_user_language(chat_id)
        if not language:
            print(f"Cannot add word for user {chat_id}: language not set.")
            conn.close()
            return None
        
        # Перевіряємо, чи є в слові артикль
        word_to_store = word # Default to original word
        extracted_article = None
        if isinstance(word, str): # Ensure word is a string
            article_match = re.match(r'^(der|die|das)\s+(.+)$', word, re.IGNORECASE)
            if article_match:
                extracted_article = article_match.group(1).lower()
                word_to_store = article_match.group(2) # Word without article
        
        # Визначаємо ID артикля (якщо він є)
        article_id_to_use = None # Use this to store the ID of the article to be used
        final_article_text = article if article else extracted_article

        if final_article_text:
            cursor.execute('SELECT id FROM article WHERE LOWER(article) = LOWER(?)', (final_article_text,))
            article_row = cursor.fetchone()
            if article_row:
                article_id_to_use = article_row[0]
            else:
                # If article not found, add it (optional, or use default)
                # For now, let's assume we use a default if not found, or handle as error
                print(f"Article '{final_article_text}' not found in article table. Using default or skipping.")
                # Default to "no article" (ID 4) if specific article not found
                article_id_to_use = 4 # Assuming 4 is 'no article' or a placeholder
        else:
            # Якщо артикль не знайдено, використовуємо порожній артикль (ID = 4)
            article_id_to_use = 4 # Assuming 4 is 'no article'
        
        # Перевірка на дублікати - шукаємо слово не залежно від регістру
        cursor.execute('SELECT id, article_id FROM words WHERE LOWER(word) = LOWER(?)', (word_to_store,))
        existing_words_matches = cursor.fetchall()
        
        final_word_id = None # Initialize word_id to be returned

        if existing_words_matches:
            # Word exists, check if article matches or needs update
            # We might have multiple entries if word casing was different but LOWER(word) is same.
            # Prefer exact match if possible, or update existing.
            # This logic can be complex. For simplicity, take the first match.
            existing_word_id, existing_article_id = existing_words_matches[0]
            final_word_id = existing_word_id
            
            # If a new article is provided and it's different, update it
            if article_id_to_use is not None and article_id_to_use != existing_article_id:
                cursor.execute('UPDATE words SET article_id = ? WHERE id = ?', (article_id_to_use, final_word_id))
                print(f"Updated article for existing word ID {final_word_id} to article_id {article_id_to_use}")

            # Update translation if it's different or missing for the user's language
            # This assumes translations are stored in columns like en_tran, uk_tran, etc.
            translation_column = f"{language}_tran"
            cursor.execute(f'SELECT {translation_column} FROM words WHERE id = ?', (final_word_id,))
            current_translation_row = cursor.fetchone()
            current_translation = current_translation_row[0] if current_translation_row else None

            if translation != current_translation:
                 cursor.execute(f'UPDATE words SET {translation_column} = ? WHERE id = ?', (translation, final_word_id))
                 print(f"Updated {language} translation for existing word ID {final_word_id}")

        else:
            # Word does not exist, insert new word
            cursor.execute('INSERT INTO words (word, article_id) VALUES (?, ?)', (word_to_store, article_id_to_use))
            final_word_id = cursor.lastrowid
            # Add translation for the user's language
            translation_column = f"{language}_tran"
            cursor.execute(f'UPDATE words SET {translation_column} = ? WHERE id = ?', (translation, final_word_id))
            print(f"Added new word '{word_to_store}' with ID {final_word_id} and {language} translation.")
        
        # If it's a personal dictionary, add reference to user's table
        if dict_type == "personal" and final_word_id is not None:
            # Ensure user's personal table exists
            ensure_user_table_exists(chat_id) # This function should create if not exists
            cursor.execute(f'INSERT OR IGNORE INTO user_{chat_id} (word_id) VALUES (?)', (final_word_id,))
            print(f"Linked word ID {final_word_id} to personal dictionary of user {chat_id}.")
            
        conn.commit()
        conn.close()
        return final_word_id
    except sqlite3.Error as e:
        print(f"Database error in add_word for user {chat_id}, word '{word}': {e}")
        traceback.print_exc()
        if 'conn' in locals() and conn: conn.close() # Ensure connection is closed on error
        return None
    except Exception as e:
        print(f"Unexpected error in add_word for user {chat_id}, word '{word}': {e}")
        traceback.print_exc()
        if 'conn' in locals() and conn: conn.close() # Ensure connection is closed on error
        return None

def ensure_user_table_exists(chat_id):
    """Ensure that the user-specific table exists and return (table_created, has_words)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if table exists before creating
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='user_{chat_id}'")
        table_existed = cursor.fetchone() is not None
        
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS user_{chat_id} (
            id INTEGER PRIMARY KEY,
            word_id INTEGER,
            rating REAL DEFAULT 0.0,
            FOREIGN KEY (word_id) REFERENCES words(id),
            UNIQUE(word_id)
        )
        ''')
        
        # Check if table has any words
        cursor.execute(f"SELECT COUNT(*) FROM user_{chat_id}")
        word_count = cursor.fetchone()[0]
        has_words = word_count > 0
        
        conn.commit()
        conn.close()
        
        return (not table_existed, has_words)  # (table_created, has_words)
        
    except sqlite3.Error as e:
        print(f"Error ensuring user table for {chat_id}: {e}")
        traceback.print_exc()
        return (False, False)
    except Exception as e:
        print(f"Unexpected error ensuring user table for {chat_id}: {e}")
        traceback.print_exc()
        return (False, False)

def add_word_async(chat_id, word, translation, dict_type="personal", article=None):
    """Асинхронна версія add_word: виконується в пулі потоків."""
    return executor.submit(add_word, chat_id, word, translation, dict_type, article)

# New helper for duplicate detection
def get_word_id_by_word(chat_id, word):
    """Return the ID of an existing word by its text (case-insensitive), or None if not found."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM words WHERE LOWER(word) = LOWER(?)', (word.strip(),))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"Error retrieving word ID for duplicate check: {e}")
        return None

# Нова функція для отримання ID слова за його німецьким текстом
def get_word_id_by_german(german_word):
    """Get the ID of a word by its German text"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id FROM words WHERE word = ?', (german_word,))
        result = cursor.fetchone()
        word_id = result[0] if result else None
        return word_id
    except Exception as e:
        print(f"Error getting word ID for '{german_word}': {e}")
        return None
    finally:
        conn.close()

def is_user_admin_of_shared_dict(user_id, shared_dict_id):
    """Return True if the user is marked as admin in shared_dict_users."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT is_admin FROM shared_dict_users WHERE user_id = ? AND dict_id = ?',
            (user_id, shared_dict_id)
        )
        row = cursor.fetchone()
        conn.close()
        return bool(row and row[0])
    except Exception as e:
        print(f"Error checking admin rights for user {user_id} on shared dict {shared_dict_id}: {e}")
        return False

def get_user_dictionary_info(user_id):
    """Retrieve shared dictionary id and admin status for the given user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT dict_type, shared_dict_id FROM users WHERE chat_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return ("personal", None, False)
        
        dict_type = row[0] if row[0] else "personal"
        shared_dict_id = row[1] if row[1] else None
        is_admin = False
        
        if shared_dict_id and dict_type == "shared":
            cursor.execute(
                'SELECT is_admin FROM shared_dict_users WHERE user_id = ? AND dict_id = ?',
                (user_id, shared_dict_id)
            )
            admin_row = cursor.fetchone()
            is_admin = bool(admin_row and admin_row[0])
        
        conn.close()
        return (dict_type, shared_dict_id, is_admin)
    except Exception as e:
        print(f"Error retrieving shared dictionary info for user {user_id}: {e}")
        return ("personal", None, False)

def shared_dictionary_exists(shared_dict_id):
    """Check if a shared dictionary table exists."""
    table_name = f"shared_dict_{shared_dict_id}"
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
    result = execute_query(query, (table_name,), fetch_mode='one')
    return result is not None

def get_shared_dictionary_words_with_articles(chat_id, shared_dict_id=None):
    """Get words with articles from a shared dictionary for a specific user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # If shared_dict_id not provided, get it from user profile
    if not shared_dict_id:
        cursor.execute('SELECT shared_dict_id FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            conn.close()
            return pd.DataFrame()
        shared_dict_id = result[0]
    
    # Verify user has access to this dictionary
    cursor.execute('''
    SELECT 1 FROM shared_dict_users 
    WHERE user_id = ? AND dict_id = ?
    ''', (chat_id, shared_dict_id))
    
    if not cursor.fetchone():
        print(f"User {chat_id} does not have access to shared dictionary {shared_dict_id}")
        conn.close()
        return pd.DataFrame()
    
    # Get user language
    language = get_user_language(chat_id) or "uk"
    other_language = "uk" if language == "ru" else "ru"
    
    # Verify shared dictionary table exists
    cursor.execute(f"""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='shared_dict_{shared_dict_id}'
    """)
    if not cursor.fetchone():
        conn.close()
        return pd.DataFrame()
    
    # Ensure user column exists in shared dictionary table
    cursor.execute(f"PRAGMA table_info(shared_dict_{shared_dict_id})")
    columns = [col[1] for col in cursor.fetchall()]
    user_col = f"user_{chat_id}"
    
    if user_col not in columns:
        # Add column if it doesn't exist
        cursor.execute(f'''
        ALTER TABLE shared_dict_{shared_dict_id} ADD COLUMN {user_col} REAL DEFAULT 0.0
        ''')
        conn.commit()
    
    # Get words with articles (article_id != 4 excludes words without articles)
    query = f'''
    SELECT w.id, w.word, w.{language}_tran as translation, w.{other_language}_tran as other_translation,
           a.article, COALESCE(sd.{user_col}, 0.0) as priority
    FROM shared_dict_{shared_dict_id} sd
    JOIN words w ON sd.word_id = w.id
    JOIN article a ON w.article_id = a.id
    WHERE w.article_id != 4 AND w.article_id IS NOT NULL
    ORDER BY priority DESC
    '''
    
    cursor.execute(query)
    
    # Get results
    results = cursor.fetchall()
    
    # Convert results to DataFrame
    columns = ['id', 'word', 'translation', 'other_translation', 'article', 'priority']
    df = pd.DataFrame(results, columns=columns)
    
    # Auto-translate missing translations if needed
    words_to_translate = df[df['translation'].isnull() & df['other_translation'].notnull()]
    # закриваємо початкове з’єднання до мережевих викликів
    conn.close()

    if not words_to_translate.empty:
        from config import translator
        # нове з’єднання для оновлень
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        for idx, row in words_to_translate.iterrows():
            try:
                tr = translator.translate(
                    row['other_translation'],
                    src=other_language, dest=language
                ).text
                cursor2.execute(
                    f"UPDATE words SET {language}_tran = ? WHERE id = ?",
                    (tr, row['id'])
                )
                df.at[idx, 'translation'] = tr
                conn2.commit()  # коміт одразу після UPDATE
            except Exception as e:
                print(f"Auto-translate error for word {row['id']}: {e}")
        conn2.close()
    # …далі повернення df…
    df = df[df['translation'].notnull()]
    
    # Remove the now-unnecessary other_translation column
    if 'other_translation' in df.columns:
        df = df.drop(columns=['other_translation'])
    
  
    return df

def get_shared_dictionary_words(chat_id, shared_dict_id=None):
    """Get all words from a shared dictionary for a specific user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # If shared_dict_id not provided, get it from user profile
    if not shared_dict_id:
        cursor.execute('SELECT shared_dict_id FROM users WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            conn.close()
            return pd.DataFrame()
        shared_dict_id = result[0]
    
    # Verify user has access to this dictionary
    cursor.execute('''
    SELECT 1 FROM shared_dict_users 
    WHERE user_id = ? AND dict_id = ?
    ''', (chat_id, shared_dict_id))
    
    if not cursor.fetchone():
        print(f"User {chat_id} does not have access to shared dictionary {shared_dict_id}")
        conn.close()
        return pd.DataFrame()
    
    # Get user language
    language = get_user_language(chat_id) or "uk"
    other_language = "uk" if language == "ru" else "ru"
    
    # Verify shared dictionary table exists
    cursor.execute(f"""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='shared_dict_{shared_dict_id}'
    """)
    if not cursor.fetchone():
        conn.close()
        return pd.DataFrame()
    
    # Ensure user column exists in shared dictionary table
    cursor.execute(f"PRAGMA table_info(shared_dict_{shared_dict_id})")
    columns = [col[1] for col in cursor.fetchall()]
    user_col = f"user_{chat_id}"
    
    if user_col not in columns:
        # Add column if it doesn't exist
        cursor.execute(f'''
        ALTER TABLE shared_dict_{shared_dict_id} ADD COLUMN {user_col} REAL DEFAULT 0.0
        ''')
        conn.commit()
    
    # Get all words (including those without articles)
    query = f'''
    SELECT w.id, w.word, w.{language}_tran as translation, w.{other_language}_tran as other_translation,
           a.article, COALESCE(sd.{user_col}, 0.0) as priority
    FROM shared_dict_{shared_dict_id} sd
    JOIN words w ON sd.word_id = w.id
    LEFT JOIN article a ON w.article_id = a.id
    ORDER BY priority DESC
    '''
    
    cursor.execute(query)
    
    # Get results
    results = cursor.fetchall()
    
    # Convert results to DataFrame
    columns = ['id', 'word', 'translation', 'other_translation', 'article', 'priority']
    df = pd.DataFrame(results, columns=columns)
    
    # Auto-translate missing translations if needed
    words_to_translate = df[df['translation'].isnull() & df['other_translation'].notnull()]
    # Close initial connection before network calls
    conn.close()

    if not words_to_translate.empty:
        from config import translator
        # New connection for updates
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        for idx, row in words_to_translate.iterrows():
            try:
                tr = translator.translate(
                    row['other_translation'],
                    src=other_language, dest=language
                ).text
                cursor2.execute(
                    f"UPDATE words SET {language}_tran = ? WHERE id = ?",
                    (tr, row['id'])
                )
                df.at[idx, 'translation'] = tr
                conn2.commit()  # Commit immediately after UPDATE
            except Exception as e:
                print(f"Auto-translate error for word {row['id']}: {e}")
        conn2.close()
    df = df[df['translation'].notnull()]
    
    # Remove the now-unnecessary other_translation column
    if 'other_translation' in df.columns:
        df = df.drop(columns=['other_translation'])
    
    return df

def get_user_shared_dictionaries(chat_id):
    """Retrieve shared dictionaries for a user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Query to get shared dictionaries for the user
        cursor.execute('''
        SELECT sd.id, sd.name, sd.code, sdu.is_admin
        FROM shared_dictionaries sd
        JOIN shared_dict_users sdu ON sd.id = sdu.dict_id
        WHERE sdu.user_id = ?
        ''', (chat_id,))

        shared_dicts = [
            {"id": row[0], "name": row[1], "code": row[2], "is_admin": bool(row[3])}
            for row in cursor.fetchall()
        ]

        conn.close()
        return shared_dicts
    except sqlite3.Error as e:
        print(f"Database error retrieving shared dictionaries for user {chat_id}: {e}")
        traceback.print_exc()
        return []
    except Exception as e:
        print(f"Unexpected error retrieving shared dictionaries for user {chat_id}: {e}")
        traceback.print_exc()
        return []


def add_words_to_dictionary(chat_id, words_data, dict_type="personal", shared_dict_id=None):
    """
    Adds a batch of words to the specified dictionary.
    Args:
        chat_id: The user's chat ID.
        words_data: A list of dictionaries, each with 'word', 'translation', and optional 'article'.
        dict_type: "personal" or "shared".
        shared_dict_id: Required if dict_type is "shared".
    Returns:
        (added_count, failed_count)
    """
    if dict_type == "shared":
        if not shared_dict_id:
            _, shared_dict_id, _ = get_user_dictionary_info(chat_id)
            if not shared_dict_id:
                print("Error: No shared dictionary specified or found for user.")
                return 0, len(words_data)
        
        if not is_user_admin_of_shared_dict(chat_id, shared_dict_id):
            print(f"User {chat_id} is not an admin of shared dict {shared_dict_id}. Cannot add words.")
            return 0, len(words_data)

    conn = get_connection()
    cursor = conn.cursor()
    
    language = get_user_language(chat_id)
    if not language:
        print(f"Cannot add words for user {chat_id}: language not set.")
        conn.close()
        return 0, len(words_data)

    translation_column = f"{language}_tran"
    cursor.execute("PRAGMA table_info(words)")
    columns = [col[1] for col in cursor.fetchall()]
    if translation_column not in columns:
        print(f"Translation column {translation_column} does not exist.")
        conn.close()
        return 0, len(words_data)

    added_count = 0
    failed_count = 0
    
    if dict_type == "personal":
        ensure_user_table_exists(chat_id)

    for word_info in words_data:
        word = word_info.get('word')
        translation = word_info.get('translation')
        article = word_info.get('article')

        if not word or not translation:
            failed_count += 1
            continue

        try:
            word_to_store = word
            extracted_article = None
            if isinstance(word, str):
                article_match = re.match(r'^(der|die|das)\\s+(.+)$', word, re.IGNORECASE)
                if article_match:
                    extracted_article = article_match.group(1).lower()
                    word_to_store = article_match.group(2)

            final_article_text = article if article else extracted_article
            article_id_to_use = 4

            if final_article_text:
                cursor.execute('SELECT id FROM article WHERE LOWER(article) = LOWER(?)', (final_article_text,))
                article_row = cursor.fetchone()
                if article_row:
                    article_id_to_use = article_row[0]

            cursor.execute('SELECT id FROM words WHERE LOWER(word) = LOWER(?)', (word_to_store,))
            existing_word = cursor.fetchone()

            word_id = None
            if existing_word:
                word_id = existing_word[0]
                cursor.execute(f'UPDATE words SET {translation_column} = ? WHERE id = ? AND ({translation_column} IS NULL OR {translation_column} != ?)', 
                             (translation, word_id, translation))
                cursor.execute('UPDATE words SET article_id = ? WHERE id = ? AND article_id != ?', 
                             (article_id_to_use, word_id, article_id_to_use))
            else:
                cursor.execute('INSERT INTO words (word, article_id) VALUES (?, ?)', (word_to_store, article_id_to_use))
                word_id = cursor.lastrowid
                cursor.execute(f'UPDATE words SET {translation_column} = ? WHERE id = ?', (translation, word_id))

            if dict_type == "personal":
                cursor.execute(f'INSERT OR IGNORE INTO user_{chat_id} (word_id) VALUES (?)', (word_id,))
            elif dict_type == "shared":
                cursor.execute(f'INSERT OR IGNORE INTO shared_dict_{shared_dict_id} (word_id) VALUES (?)', (word_id,))
            
            if cursor.rowcount > 0:
                added_count += 1

        except sqlite3.Error as e:
            print(f"DB error processing word '{word}': {e}")
            failed_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"Batch add complete for user {chat_id}. Added: {added_count}, Failed: {failed_count}")
    return added_count, failed_count

def init_db():
    """Initialize database via db_init.create_database"""
    from db_init import create_database
    create_database()

def validate_shared_dictionary_access(user_id, shared_dict_id):
    """
    Validate if user has access to shared dictionary
    
    Args:
        user_id: User's chat ID
        shared_dict_id: Shared dictionary ID
        
    Returns:
        tuple: (exists, has_access, dict_name)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if dictionary exists
        cursor.execute('SELECT name FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return (False, False, None)
        
        dict_name = result[0]
        
        # Check if user has access (is creator or member)
        cursor.execute('SELECT created_by FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
        creator_result = cursor.fetchone()
        is_creator = creator_result and creator_result[0] == user_id
        
        if is_creator:
            conn.close()
            return (True, True, dict_name)
        
        # Check if user is a member
        cursor.execute('SELECT 1 FROM shared_dict_users WHERE user_id = ? AND dict_id = ?', (user_id, shared_dict_id))
        member_result = cursor.fetchone()
        has_access = bool(member_result)
        
        conn.close()
        return (True, has_access, dict_name)
    except Exception as e:
        print(f"Error validating shared dictionary access: {e}")
        return (False, False, None)

def reset_to_personal_dictionary(user_id):
    """
    Reset user's dictionary to personal
    
    Args:
        user_id: User's chat ID
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET dict_type = 'personal', shared_dict_id = NULL WHERE chat_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error resetting to personal dictionary: {e}")

def sync_user_state_with_db(chat_id):
    """
    Synchronize in-memory user state with database
    
    Args:
        chat_id: User's chat ID
    """
    from config import user_state
    
    try:
        dict_type, shared_dict_id, is_admin = get_user_dictionary_info(chat_id)
        
        # Update in-memory state
        if chat_id not in user_state:
            user_state[chat_id] = {}
        
        user_state[chat_id]["dict_type"] = dict_type
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        elif "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
        
        if is_admin:
            user_state[chat_id]["is_admin"] = is_admin
        elif "is_admin" in user_state[chat_id]:
            del user_state[chat_id]["is_admin"]
            
        print(f"Synced user state for {chat_id}: dict_type={dict_type}, shared_dict_id={shared_dict_id}, is_admin={is_admin}")
        
    except Exception as e:
        print(f"Error syncing user state for {chat_id}: {e}")

def create_shared_dictionary_tables():
    """Create tables for shared dictionaries functionality"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create shared_dictionaries table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_dictionaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            created_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create shared_dict_users table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_dict_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dict_id INTEGER NOT NULL,
            is_admin INTEGER DEFAULT 0,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dict_id) REFERENCES shared_dictionaries(id),
            UNIQUE(user_id, dict_id)
        )
        ''')
        
        # Add shared dictionary columns to users table if they don't exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'dict_type' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN dict_type TEXT DEFAULT 'personal'")
        
        if 'shared_dict_id' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN shared_dict_id INTEGER")
            
        if 'shared_dict_admin' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN shared_dict_admin INTEGER DEFAULT 0")
        
        conn.commit()
        conn.close()
        print("Shared dictionary tables created/updated successfully")
        
    except Exception as e:
        print(f"Error creating shared dictionary tables: {e}")
        import traceback
        traceback.print_exc()

def create_shared_dictionary(creator_id, name):
    """Create a new shared dictionary and return access code and dictionary ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Generate unique 6-character code
        code = None
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            cursor.execute('SELECT id FROM shared_dictionaries WHERE code = ?', (code,))
            if not cursor.fetchone():
                break
        
        # Create shared dictionary record
        cursor.execute('''
        INSERT INTO shared_dictionaries (name, code, created_by)
        VALUES (?, ?, ?)
        ''', (name, code, creator_id))
        
        shared_dict_id = cursor.lastrowid
        
        # Create shared dictionary table for words
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS shared_dict_{shared_dict_id} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL,
            FOREIGN KEY (word_id) REFERENCES words(id),
            UNIQUE(word_id)
        )
        ''')
        
        # Add creator to shared_dict_users as admin
        cursor.execute('''
        INSERT INTO shared_dict_users (user_id, dict_id, is_admin)
        VALUES (?, ?, 1)
        ''', (creator_id, shared_dict_id))
        
        # Update creator's user record
        cursor.execute('''
        UPDATE users SET dict_type = 'shared', shared_dict_id = ?, shared_dict_admin = 1
        WHERE chat_id = ?
        ''', (shared_dict_id, creator_id))
        
        conn.commit()
        conn.close()
        
        print(f"Created shared dictionary '{name}' with code {code} for user {creator_id}")
        return code, shared_dict_id
        
    except Exception as e:
        print(f"Error creating shared dictionary: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def join_shared_dictionary(user_id, code):
    """Join a shared dictionary using access code"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Find dictionary by code
        cursor.execute('SELECT id, name FROM shared_dictionaries WHERE code = ?', (code.upper(),))
        result = cursor.fetchone()
        
        if not result:
            return False, "Словник з таким кодом не знайдено"
        
        dict_id, dict_name = result
        
        # Check if user is already a member
        cursor.execute('SELECT 1 FROM shared_dict_users WHERE user_id = ? AND dict_id = ?', (user_id, dict_id))
        if cursor.fetchone():
            return False, f"Ви вже є учасником словника '{dict_name}'"
        
        # Add user to shared dictionary
        cursor.execute('''
        INSERT INTO shared_dict_users (user_id, dict_id, is_admin)
        VALUES (?, ?, 0)
        ''', (user_id, dict_id))
        
        # Update user's dictionary settings
        cursor.execute('''
        UPDATE users SET dict_type = 'shared', shared_dict_id = ?, shared_dict_admin = 0
        WHERE chat_id = ?
        ''', (dict_id, user_id))
        
        conn.commit()
        conn.close()
        
        print(f"User {user_id} joined shared dictionary '{dict_name}' (ID: {dict_id})")
        return True, dict_name
        
    except Exception as e:
        print(f"Error joining shared dictionary: {e}")
        import traceback
        traceback.print_exc()
        return False, "Виникла помилка при приєднанні до словника"

def check_database_integrity():
    """Check database integrity and basic tables"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if basic tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['users', 'words', 'article']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"WARNING: Missing required tables: {missing_tables}")
            return False
        
        # Check if there's any data
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM words")
        word_count = cursor.fetchone()[0]
        
        print(f"Database integrity check: {len(tables)} tables, {user_count} users, {word_count} words")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database integrity check failed: {e}")
        return False

def add_word_to_shared_dictionary(chat_id, word_id, shared_dict_id):
    """
    Add a word to a shared dictionary by creating a link in shared_dict_{id} table.
    
    Args:
        chat_id: User's chat ID
        word_id: ID of the word to add
        shared_dict_id: ID of the shared dictionary
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if the shared dictionary exists and user has access
        cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
        dict_info = cursor.fetchone()
        if not dict_info:
            conn.close()
            return False, "Словник не знайдено"
        
        dict_name = dict_info[0]
        
        # Check if user has admin rights or is a member
        cursor.execute("SELECT is_admin FROM shared_dict_users WHERE user_id = ? AND dict_id = ?", 
                      (chat_id, shared_dict_id))
        user_info = cursor.fetchone()
        if not user_info:
            conn.close()
            return False, "Немає доступу до словника"
        
        # Check if word exists
        cursor.execute("SELECT word FROM words WHERE id = ?", (word_id,))
        word_info = cursor.fetchone()
        if not word_info:
            conn.close()
            return False, "Слово не знайдено"
        
        word = word_info[0]
        
        # Check if shared_dict_{id} table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='shared_dict_{shared_dict_id}'")
        if not cursor.fetchone():
            conn.close()
            return False, f"Таблиця shared_dict_{shared_dict_id} не існує"
        
        # Check if word is already in the shared dictionary
        cursor.execute(f"SELECT id FROM shared_dict_{shared_dict_id} WHERE word_id = ?", (word_id,))
        if cursor.fetchone():
            conn.close()
            return False, f"Слово '{word}' вже є в словнику '{dict_name}'"
        
        # Add word to shared dictionary
        cursor.execute(f"INSERT INTO shared_dict_{shared_dict_id} (word_id) VALUES (?)", (word_id,))
        
        conn.commit()
        conn.close()
        
        return True, f"Слово '{word}' додано до словника '{dict_name}'"
        
    except Exception as e:
        print(f"Error adding word to shared dictionary: {e}")
        if 'conn' in locals():
            conn.close()
        return False, "Виникла помилка при додаванні слова до словника"

def delete_word_from_shared_dict(chat_id, word_id, shared_dict_id):
    """Delete a word from a shared dictionary."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check admin rights
        if not is_user_admin_of_shared_dict(chat_id, shared_dict_id):
            conn.close()
            return False
        
        # Delete from shared_dict_{id} table
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='shared_dict_{shared_dict_id}'")
        if cursor.fetchone():
            cursor.execute(f"DELETE FROM shared_dict_{shared_dict_id} WHERE word_id = ?", (word_id,))
            rows_affected = cursor.rowcount
        else:
            print(f"Shared dictionary table shared_dict_{shared_dict_id} not found")
            conn.close()
            return False
        
        conn.commit()
        conn.close()
        return rows_affected > 0
        
    except Exception as e:
        print(f"Error deleting word from shared dictionary: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def delete_word_from_personal_dict(chat_id, word_id):
    """Delete a word from user's personal dictionary."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"DELETE FROM user_{chat_id} WHERE word_id = ?", (word_id,))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error deleting word from personal dictionary: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def update_word_translation_shared_dict(chat_id, word_id, new_translation, shared_dict_id):
    """Update word translation in shared dictionary."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check admin rights
        if not is_user_admin_of_shared_dict(chat_id, shared_dict_id):
            conn.close()
            return False
        
        # Get user language and update translation
        language = get_user_language(chat_id)
        if not language:
            conn.close()
            return False
        
        translation_column = f"{language}_tran"
        cursor.execute(f"UPDATE words SET {translation_column} = ? WHERE id = ?", 
                      (new_translation, word_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error updating word translation in shared dictionary: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def update_word_translation_personal_dict(chat_id, word_id, new_translation):
    """Update word translation in personal dictionary."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user language and update translation
        language = get_user_language(chat_id)
        if not language:
            conn.close()
            return False
        
        translation_column = f"{language}_tran"
        cursor.execute(f"UPDATE words SET {translation_column} = ? WHERE id = ?", 
                      (new_translation, word_id))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
        
    except Exception as e:
        print(f"Error updating word translation in personal dictionary: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def update_word_rating_personal_dict(user_id, word_id, rating_change):
    """Update the rating of a word in the user's personal dictionary."""
    table_name = f"user_{user_id}"
    # Перевіряємо, чи існує колонка 'priority'
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    conn.close()

    if 'priority' in columns:
        query = f"UPDATE {table_name} SET priority = priority + ? WHERE word_id = ?;"
        execute_query(query, (rating_change, word_id))
    # Якщо колонки немає, нічого не робимо, або можна додати логування

def update_word_rating_shared_dict(user_id, word_id, rating_change, shared_dict_id):
    """Update the rating of a word for a user in a shared dictionary."""
    table_name = f"shared_dict_{shared_dict_id}"
    user_column = f'"user_{user_id}"'
    
    # Перевіряємо, чи існує колонка користувача
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    conn.close()

    if user_column.strip('"') in columns:
        query = f"UPDATE {table_name} SET {user_column} = {user_column} + ? WHERE word_id = ?;"
        execute_query(query, (rating_change, word_id))
    # Якщо колонки немає, нічого не робимо, або можна додати логування
