# -*- coding: utf-8 -*-
import os
import sqlite3
import pandas as pd

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
    
    # Знаходимо всі CSV файли словників
    csv_files = [f for f in os.listdir(USER_DICT_DIR) if f.endswith('.csv')]
    
    for csv_file in csv_files:
        file_path = os.path.join(USER_DICT_DIR, csv_file)
        
        try:
            # Читаємо CSV файл
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            
            # Перевіряємо, чи це загальний словник
            if csv_file == "common_dictionary.csv":
                print(f"Migrating common dictionary from {file_path}")
                
                # Додаємо кожне слово в таблицю words
                for _, row in df.iterrows():
                    word = row['word']
                    translation = row['translation']
                    article = row.get('article', '')
                    article_id = article_map.get(article, article_map[''])  # За замовчуванням порожній артикль
                    
                    # Додаємо слово в таблицю words
                    try:
                        cursor.execute('''
                        INSERT OR IGNORE INTO words (article_id, word, uk_tran) VALUES (?, ?, ?)
                        ''', (article_id, word, translation))
                    except sqlite3.IntegrityError:
                        pass
            else:
                # Визначаємо мову зі шляху файлу
                lang_prefix = 'uk' if 'uk_words_' in csv_file else 'ru' if 'ru_words_' in csv_file else None
                if not lang_prefix:
                    print(f"Cannot determine language for file {csv_file}, skipping...")
                    continue
                
                # Отримуємо chat_id з імені файлу
                try:
                    chat_id = int(csv_file.split('_')[-1].split('.')[0])
                except (ValueError, IndexError):
                    print(f"Cannot extract chat_id from file name {csv_file}, skipping...")
                    continue
                
                print(f"Migrating {lang_prefix} dictionary for user {chat_id} from {file_path}")
                
                # Створюємо таблицю для користувача, якщо не існує
                create_user_table(chat_id)
                
                # Оновлюємо мову користувача
                cursor.execute('UPDATE users SET language = ? WHERE chat_id = ?', (lang_prefix, chat_id))
                
                # Додаємо кожне слово в таблицю words і user_XXX
                for _, row in df.iterrows():
                    word = row['word']
                    translation = row['translation']
                    rating = row.get('priority', 0.0)
                    
                    # Додаємо слово в таблицю words з правильним перекладом залежно від мови
                    if lang_prefix == 'uk':
                        cursor.execute('''
                        INSERT OR IGNORE INTO words (article_id, word, uk_tran) VALUES (?, ?, ?)
                        ''', (article_map[''], word, translation))
                    else:  # ru
                        cursor.execute('''
                        INSERT OR IGNORE INTO words (article_id, word, ru_tran) VALUES (?, ?, ?)
                        ''', (article_map[''], word, translation))
                    
                    # Отримуємо ID доданого слова
                    cursor.execute('SELECT id FROM words WHERE word = ?', (word,))
                    word_id = cursor.fetchone()[0]
                    
                    # Додаємо слово до словника користувача
                    cursor.execute(f'''
                    INSERT OR IGNORE INTO user_{chat_id} (word_id, rating) VALUES (?, ?)
                    ''', (word_id, rating))
        except Exception as e:
            print(f"Error migrating {csv_file}: {e}")
    
    # Зберігаємо зміни і закриваємо з'єднання
    conn.commit()
    conn.close()
    
    print("CSV migration completed")

if __name__ == "__main__":
    create_database()
    migrate_from_csv()
