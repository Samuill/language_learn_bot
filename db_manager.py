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
        
        word_id = best_word_id
        
        # Перевіряємо, чи є переклад для поточної мови користувача
        cursor.execute(f'SELECT {language}_tran FROM words WHERE id = ?', (word_id,))
        current_translation = cursor.fetchone()[0]
        
        if not current_translation:
            # Якщо немає перекладу для поточної мови користувача,
            # але слово існує, спробуємо отримати переклад з іншої мови
            other_language = "ru" if language == "uk" else "uk"
            cursor.execute(f'SELECT {other_language}_tran FROM words WHERE id = ?', (word_id,))
            other_translation = cursor.fetchone()[0]
            
            if other_translation:
                # Якщо є переклад на іншу мову, використовуємо перекладач
                try:
                    from config import translator
                    auto_translation = translator.translate(
                        other_translation, 
                        src=other_language, 
                        dest=language
                    ).text
                    print(f"Auto-translated '{other_translation}' ({other_language}) to '{auto_translation}' ({language})")
                    translation = auto_translation
                except Exception as e:
                    print(f"Error auto-translating: {e}")
        
        # Оновлюємо переклад та артикль для обраного слова
        if article_id != 4 and not best_has_article:
            # Оновлюємо артикль і переклад
            cursor.execute(f'UPDATE words SET {language}_tran = ?, article_id = ? WHERE id = ?', 
                         (translation, article_id, word_id))
        else:
            # Просто оновлюємо переклад
            cursor.execute(f'UPDATE words SET {language}_tran = ? WHERE id = ?', 
                         (translation, word_id))
        
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
            
            # Визначаємо рівень користувача, щоб змінити крок оновлення рейтингу
            import config
            level = config.user_state.get(chat_id, {}).get('level', 'easy')
            
            # Для складного рівня більше змінюємо рейтинг
            if level == "hard":
                change = change * 2  # Подвоюємо зміну для складного рівня
            
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
            
            print(f"Updated rating for user {chat_id}, word_id {word_id}: {current_rating} -> {new_rating}, level={level}")
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
    
    # Створюємо таблицю для зв'язку користувачів та словників
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
    
    # ВАЖЛИВО: Додаємо запис в таблицю зв'язків, чітко вказавши статус адміна
    cursor.execute('''
    INSERT OR REPLACE INTO shared_dict_users (user_id, dict_id, is_admin, joined_at)
    VALUES (?, ?, 1, datetime('now'))
    ''', (chat_id, shared_dict_id))
    
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
    
    # Додаємо запис про зв'язок користувача з словником
    cursor.execute('''
    INSERT OR IGNORE INTO shared_dict_users (user_id, dict_id, joined_at)
    VALUES (?, ?, datetime('now'))
    ''', (chat_id, shared_dict_id))
    
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
    
    # Перевіряємо словники, створені користувачем (він точно адміністратор)
    cursor.execute('''
    SELECT id, name, code 
    FROM shared_dictionaries
    WHERE created_by = ?
    ''', (chat_id,))
    
    owned_dicts = []
    for dict_id, name, code in cursor.fetchall():
        owned_dicts.append({
            'id': dict_id,
            'name': name,
            'code': code,
            'is_admin': True  # Якщо створив, то 100% адміністратор
        })
    
    # Додатково перевіряємо shared_dict_users для отримання словників, до яких користувач приєднався
    cursor.execute('''
    SELECT sd.id, sd.name, sd.code, sdu.is_admin
    FROM shared_dictionaries sd
    JOIN shared_dict_users sdu ON sd.id = sdu.dict_id
    WHERE sdu.user_id = ? AND sd.created_by != ?
    ''', (chat_id, chat_id))  # Виключаємо ті, що вже додали як створені
    
    for dict_id, name, code, is_admin in cursor.fetchall():
        # Додаємо тільки якщо такого ID ще немає у списку
        if not any(d['id'] == dict_id for d in owned_dicts):
            owned_dicts.append({
                'id': dict_id,
                'name': name,
                'code': code,
                'is_admin': bool(is_admin)
            })
    
    # Якщо немає записів у таблицях, перевіряємо shared_dict_id в таблиці users (для сумісності)
    if not owned_dicts:
        cursor.execute('''
        SELECT sd.id, sd.name, sd.code, u.shared_dict_admin 
        FROM shared_dictionaries sd
        JOIN users u ON sd.id = u.shared_dict_id
        WHERE u.chat_id = ?
        ''', (chat_id,))
        result = cursor.fetchone()
        
        if result:
            dict_id, name, code, is_admin = result
            owned_dicts.append({
                'id': dict_id,
                'name': name,
                'code': code,
                'is_admin': bool(is_admin)
            })
    
    conn.close()
    return owned_dicts

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
    
    # Перевіряємо, чи має користувач доступ до цього словника
    cursor.execute('''
    SELECT 1 FROM shared_dict_users 
    WHERE user_id = ? AND dict_id = ?
    ''', (chat_id, shared_dict_id))
    
    if not cursor.fetchone():
        print(f"User {chat_id} does not have access to shared dictionary {shared_dict_id}")
        conn.close()
        return pd.DataFrame()
    
    # Отримуємо мову користувача
    language = get_user_language(chat_id) or "uk"
    other_language = "uk" if language == "ru" else "ru"
    
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
    
    # Отримуємо ВСІ слова зі спільного словника, навіть без перекладу поточною мовою
    query = f'''
    SELECT w.id, w.word, w.{language}_tran as translation, w.{other_language}_tran as other_translation,
           a.article, COALESCE(sd.{user_col}, 0.0) as priority
    FROM shared_dict_{shared_dict_id} sd
    JOIN words w ON sd.word_id = w.id
    LEFT JOIN article a ON w.article_id = a.id
    ORDER BY priority DESC
    '''
    
    # Додаємо журнал запиту для відлагодження
    print(f"DEBUG query: {query.replace('{', '{{').replace('}', '}}')}")
    
    cursor.execute(query)
    
    # Отримуємо результати
    results = cursor.fetchall()
    
    # Convert results to DataFrame with all columns including other_translation
    columns = ['id', 'word', 'translation', 'other_translation', 'article', 'priority']
    df = pd.DataFrame(results, columns=columns)
    
    # Для слів, які не мають перекладу на мову користувача, але мають на іншу мову,
    # автоматично перекладаємо і зберігаємо в базу даних
    words_to_translate = df[df['translation'].isnull() & df['other_translation'].notnull()]
    if not words_to_translate.empty:
        print(f"Found {len(words_to_translate)} words without {language} translation. Auto-translating...")
        
        try:
            from config import translator
            for index, row in words_to_translate.iterrows():
                try:
                    # Використовуємо переклад з іншої мови як основу
                    source_text = row['other_translation']
                    source_lang = other_language
                    auto_translation = translator.translate(source_text, src=source_lang, dest=language).text
                    
                    # Оновлюємо базу даних
                    cursor.execute(f'''
                    UPDATE words SET {language}_tran = ? WHERE id = ?
                    ''', (auto_translation, row['id']))
                    
                    # Оновлюємо DataFrame
                    df.at[index, 'translation'] = auto_translation
                    print(f"Auto-translated word ID {row['id']}: '{source_text}' -> '{auto_translation}'")
                except Exception as e:
                    print(f"Error translating word ID {row['id']}: {e}")
            
            # Зберігаємо зміни в базі даних
            conn.commit()
            
        except ImportError:
            print("Google translator not available for automatic translation")
        except Exception as e:
            print(f"Error during auto-translation: {e}")
    
    # Відфільтровуємо записи, які все ще не мають перекладу
    df = df[df['translation'].notnull()]
    
    # Видаляємо колонку other_translation, яка вже не потрібна
    df = df.drop(columns=['other_translation'])
    
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
    
    try:
        # Якщо shared_dict_id не вказано, отримуємо його з профілю користувача
        if not shared_dict_id:
            cursor.execute('SELECT shared_dict_id FROM users WHERE chat_id = ?', (chat_id,))
            result = cursor.fetchone()
            if not result or not result[0]:
                print(f"ERROR: No shared_dict_id found for user {chat_id}")
                conn.close()
                return False
            shared_dict_id = result[0]
        
        # Debug: Вивід інформації для відлагодження
        print(f"DEBUG: Updating rating for user={chat_id}, word_id={word_id}, change={change}, shared_dict_id={shared_dict_id}")
        
        # Перевіряємо наявність слова в shared_dict таблиці
        cursor.execute(f"SELECT 1 FROM shared_dict_{shared_dict_id} WHERE word_id = ?", (word_id,))
        if not cursor.fetchone():
            print(f"ERROR: Word ID {word_id} not found in shared_dict_{shared_dict_id}")
            conn.close()
            return False
        
        user_col = f"user_{chat_id}"
        
        # Перевіряємо, чи є колонка для цього користувача
        cursor.execute(f"PRAGMA table_info(shared_dict_{shared_dict_id})")
        columns = [col[1] for col in cursor.fetchall()]
        
        if user_col not in columns:
            # Якщо колонки немає, додаємо її
            print(f"Adding column {user_col} to shared_dict_{shared_dict_id}")
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
            current_rating = result[0] if result[0] is not None else 0.0
            
            # Визначаємо рівень користувача, щоб змінити крок оновлення рейтингу
            import config
            level = config.user_state.get(chat_id, {}).get('level', 'easy')
            
            # Для складного рівня подвоюємо зміну рейтингу
            if level == "hard":
                change = change * 2
                
            # Застосовуємо зміну з обмеженнями
            new_rating = max(min(current_rating + change, 5.0), 0.0)
            # Округлюємо до однієї цифри після коми
            new_rating = round(new_rating, 1)
            
            # Вивід для діагностики
            print(f"DEBUG SQL: UPDATE shared_dict_{shared_dict_id} SET {user_col} = {new_rating} WHERE word_id = {word_id}")
            
            # Оновлюємо рейтинг
            cursor.execute(f'''
            UPDATE shared_dict_{shared_dict_id}
            SET {user_col} = ?
            WHERE word_id = ?
            ''', (new_rating, word_id))
            
            # Вивід для підтвердження оновлення
            cursor.execute(f"SELECT {user_col} FROM shared_dict_{shared_dict_id} WHERE word_id = ?", (word_id,))
            updated_rating = cursor.fetchone()[0]
            print(f"CONFIRMATION: Updated shared dict rating for user {chat_id}, word_id {word_id}: {current_rating} -> {updated_rating}, level={level}")
            
            conn.commit()
            conn.close()
            return True
        else:
            print(f"ERROR: No rating found for word_id={word_id} in shared_dict_{shared_dict_id}")
    except Exception as e:
        print(f"ERROR in update_word_rating_shared_dict: {e}")
        import traceback
        traceback.print_exc()
    
    conn.close()
    return False

def ensure_user_table_exists(chat_id):
    """Check if user's table exists, and create it if it doesn't"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user table exists
    cursor.execute(f"""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name='user_{chat_id}'
    """)
    
    if not cursor.fetchone():
        # Table doesn't exist, create it
        print(f"Creating table user_{chat_id} for new user")
        
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS user_{chat_id} (
            id INTEGER PRIMARY KEY,
            word_id INTEGER NOT NULL,
            rating REAL DEFAULT 0.0,
            last_practiced TEXT,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
        ''')
        
        # Check if user exists in users table
        cursor.execute("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,))
        if not cursor.fetchone():
            # Add user to users table
            cursor.execute("""
            INSERT INTO users (chat_id, last_active, streak) 
            VALUES (?, datetime('now'), 0)
            """, (chat_id,))
            
        conn.commit()
        conn.close()
        return True, False  # Table created, no words
    
    # Check if the table has any words
    cursor.execute(f"SELECT COUNT(*) FROM user_{chat_id}")
    count = cursor.fetchone()[0]
    
    conn.close()
    return False, count > 0  # Table exists, has words if count > 0

def get_case_explanation(case, language="uk"):
    """Get explanation for grammatical cases"""
    explanations = {
        "Nominativ": {
            "uk": "Називний відмінок (Nominativ) використовується для підмета речення і відповідає на питання 'хто/що?'",
            "ru": "Именительный падеж (Nominativ) используется для подлежащего і отвечает на вопрос 'кто/что?'"
        },
        "Akkusativ": {
            "uk": "Знахідний відмінок (Akkusativ) використовується для прямого додатка і відповідає на питання 'кого/що?'",
            "ru": "Винительный падеж (Akkusativ) используется для прямого дополнения і отвечает на вопрос 'кого/что?'"
        },
        "Dativ": {
            "uk": "Давальний відмінок (Dativ) використовується для непрямого додатка і відповідає на питання 'кому/чому?'",
            "ru": "Дательный падеж (Dativ) используется для непрямого дополнения і отвечает на вопрос 'кому/чему?'"
        }
    }
    
    return explanations.get(case, {}).get(language, explanations[case]["uk"])
