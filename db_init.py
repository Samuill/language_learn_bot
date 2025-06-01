# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd
import glob
import re

# Шлях до бази даних
DB_DIR = "database"
DB_PATH = os.path.join(DB_DIR, "german_words.db")

def create_database():
    """Create the SQLite database with all necessary tables"""
    # Створюємо директорію для бази даних, якщо не існує
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    
    print(f"Initializing database at {DB_PATH}")
    
    # Підключаємось до бази даних (створюється автоматично, якщо не існує)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Створюємо таблицю для артиклів
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS article (
        id INTEGER PRIMARY KEY,
        article TEXT NOT NULL UNIQUE
    )
    ''')
    
    # Заповнюємо таблицю артиклів базовими значеннями
    articles = [('der',), ('die',), ('das',), ('',)]  # Додаємо порожній артикль для слів без артиклів
    try:
        cursor.executemany('INSERT OR IGNORE INTO article (article) VALUES (?)', articles)
    except sqlite3.IntegrityError:
        pass  # Ігноруємо помилки унікальності, якщо артиклі вже існують
    
    # Створюємо таблицю для слів
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY,
        article_id INTEGER,
        word TEXT NOT NULL,
        ru_tran TEXT,
        uk_tran TEXT,
        tr_tran TEXT,
        ar_tran TEXT,
        FOREIGN KEY (article_id) REFERENCES article(id),
        UNIQUE(word, article_id)
    )
    ''')
    
    # Створюємо індекс для швидкого пошуку слів
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON words(word)')
    
    # Створюємо таблицю для відстеження користувачів
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        chat_id INTEGER UNIQUE,
        language TEXT,
        last_active TEXT,
        streak INTEGER DEFAULT 0
    )
    ''')
    
    # Зберігаємо зміни і закриваємо з'єднання
    conn.commit()
    conn.close()
    
    print("Database initialized successfully")

def create_user_table(chat_id):
    """Create a table for a specific user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Створюємо таблицю для зберігання слів конкретного користувача
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS user_{chat_id} (
        id INTEGER PRIMARY KEY,
        word_id INTEGER,
        rating REAL DEFAULT 0.0,
        FOREIGN KEY (word_id) REFERENCES words(id),
        UNIQUE(word_id)
    )
    ''')
    
    # Перевіряємо, чи користувач вже існує в таблиці користувачів
    cursor.execute('SELECT 1 FROM users WHERE chat_id = ?', (chat_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (chat_id) VALUES (?)', (chat_id,))
    
    conn.commit()
    conn.close()
    
    print(f"User table for {chat_id} created successfully")

def migrate_from_csv():
    """Migrate data from CSV files to SQLite database"""
    from storage import USER_DICT_DIR
    
    # Перевіряємо, чи існує директорія зі словниками
    if not os.path.exists(USER_DICT_DIR):
        print(f"No CSV dictionaries found in {USER_DICT_DIR}")
        return
    
    # Створюємо підключення до бази даних
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Отримуємо мапінг артиклів до їх ID
    cursor.execute('SELECT id, article FROM article')
    article_map = {article: aid for aid, article in cursor.fetchall()}
    
    # Збираємо всі CSV файли словників (включаючи root директорію для сумісності)
    user_dict_files = []
    
    # Пошук у USER_DICT_DIR
    user_dict_pattern = os.path.join(USER_DICT_DIR, "*_words_*.csv")
    user_dict_files.extend(glob.glob(user_dict_pattern))
    
    # Пошук у root директорії (для сумісності)
    root_dict_pattern = "*_words_*.csv"
    user_dict_files.extend(glob.glob(root_dict_pattern))
    
    # Загальний словник
    common_dict_path = os.path.join(USER_DICT_DIR, "common_dictionary.csv")
    if os.path.exists(common_dict_path):
        print(f"Found common dictionary: {common_dict_path}")
        try:
            # Читаємо CSV файл
            df = pd.read_csv(common_dict_path, encoding='utf-8-sig')
            print(f"Migrating common dictionary with {len(df)} words")
            
            # Додаємо кожне слово в таблицю words
            for _, row in df.iterrows():
                word = row['word']
                translation = row['translation']
                article = row.get('article', '')
                article_id = article_map.get(article, article_map[''])
                
                # Додаємо слово в таблицю words
                try:
                    cursor.execute('''
                    INSERT OR IGNORE INTO words (article_id, word, uk_tran) VALUES (?, ?, ?)
                    ''', (article_id, word, translation))
                    conn.commit()
                except sqlite3.IntegrityError as e:
                    print(f"IntegrityError for word {word}: {e}")
                except Exception as e:
                    print(f"Error adding word {word} to common dictionary: {e}")
            
            print(f"Successfully migrated common dictionary")
        except Exception as e:
            print(f"Error processing common dictionary: {e}")
    
    # Обробляємо словники користувачів
    print(f"Found {len(user_dict_files)} user dictionaries")
    migrated_users = 0
    
    for file_path in user_dict_files:
        filename = os.path.basename(file_path)
        
        try:
            # Визначаємо мову та ID користувача з імені файлу
            lang_match = re.match(r'(uk|ru)_words_(\d+)\.csv', filename)
            if not lang_match:
                print(f"Cannot parse filename: {filename}, skipping...")
                continue
            
            lang_prefix, chat_id_str = lang_match.groups()
            chat_id = int(chat_id_str)
            
            print(f"Processing {lang_prefix} dictionary for user {chat_id}: {file_path}")
            
            # Читаємо CSV файл
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                print(f"  - Found {len(df)} words")
            except Exception as e:
                print(f"  - Error reading CSV: {e}")
                continue
            
            # Створюємо або оновлюємо запис користувача
            try:
                cursor.execute('SELECT 1 FROM users WHERE chat_id = ?', (chat_id,))
                if not cursor.fetchone():
                    # Створюємо запис користувача, якщо він не існує
                    cursor.execute(
                        'INSERT INTO users (chat_id, language, streak, last_active) VALUES (?, ?, 0, NULL)',
                        (chat_id, lang_prefix)
                    )
                else:
                    # Оновлюємо мову користувача
                    cursor.execute('UPDATE users SET language = ? WHERE chat_id = ?', (lang_prefix, chat_id))
                conn.commit()
                print(f"  - User {chat_id} added/updated with language {lang_prefix}")
            except Exception as e:
                print(f"  - Error creating/updating user: {e}")
                continue
            
            # Створюємо таблицю для користувача
            try:
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
                print(f"  - Table user_{chat_id} created or already exists")
            except Exception as e:
                print(f"  - Error creating table for user {chat_id}: {e}")
                continue
            
            # Обробляємо кожне слово
            words_added = 0
            for _, row in df.iterrows():
                try:
                    word = row['word']
                    translation = row['translation']
                    priority = float(row.get('priority', 0.0))
                    
                    # Додаємо слово в загальну таблицю words, якщо воно ще не існує
                    cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
                    result = cursor.fetchone()
                    
                    if result:
                        # Слово існує, отримуємо його ID
                        word_id = result[0]
                        
                        # Оновлюємо переклад для відповідної мови, якщо він не заданий
                        cursor.execute(f'SELECT {lang_prefix}_tran FROM words WHERE id = ?', (word_id,))
                        existing_translation = cursor.fetchone()[0]
                        
                        if not existing_translation:
                            cursor.execute(f'UPDATE words SET {lang_prefix}_tran = ? WHERE id = ?', 
                                         (translation, word_id))
                    else:
                        # Додаємо нове слово
                        cursor.execute(f'''
                        INSERT INTO words (article_id, word, {lang_prefix}_tran) 
                        VALUES (?, ?, ?)
                        ''', (article_map[''], word, translation))
                        conn.commit()
                        
                        # Отримуємо ID доданого слова
                        cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
                        word_id = cursor.fetchone()[0]
                    
                    # Додаємо слово в таблицю користувача з рейтингом
                    cursor.execute(f'''
                    INSERT OR REPLACE INTO user_{chat_id} (word_id, rating)
                    VALUES (?, ?)
                    ''', (word_id, priority))
                    conn.commit()
                    
                    words_added += 1
                except Exception as e:
                    print(f"  - Error processing word '{word}': {e}")
            
            print(f"  - Added/updated {words_added} words for user {chat_id}")
            migrated_users += 1
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
    
    # Закриваємо з'єднання
    conn.commit()
    conn.close()
    
    print(f"Migration complete. Processed {migrated_users} user dictionaries.")

if __name__ == "__main__":
    create_database()
    migrate_from_csv()
