# -*- coding: utf-8 -*-
import os
import pandas as pd
import time
from config import COMMON_DICT_FILE, user_state
import db_manager

# Створюємо директорію для словників користувачів
USER_DICT_DIR = "user_dictionaries"
if not os.path.exists(USER_DICT_DIR):
    try:
        os.makedirs(USER_DICT_DIR)
        print(f"Created directory {USER_DICT_DIR} for user dictionaries")
    except Exception as e:
        print(f"Failed to create directory {USER_DICT_DIR}: {e}")

def get_user_file_path(chat_id):
    """
    DEPRECATED: Use db_manager.get_user_language instead
    This function is kept for backwards compatibility only
    """
    print(f"DEPRECATED: get_user_file_path called for user {chat_id}")
    
    try:
        # Використовуємо базу даних замість CSV файлів
        lang = db_manager.get_user_language(chat_id)
        if lang:
            dummy_path = os.path.join(USER_DICT_DIR, f"{lang}_words_{chat_id}.csv")
            return dummy_path, lang
    except Exception as e:
        print(f"Error accessing database in get_user_file_path: {e}")
    
    return None, None

def get_common_file_path():
    """
    DEPRECATED: Use db_manager functions instead
    This function is kept for backwards compatibility only
    """
    print("DEPRECATED: get_common_file_path called")
    return COMMON_DICT_FILE, "common"

def get_dataframe(chat_id, dict_type=None):
    """Get DataFrame for user dictionary"""
    print(f"DEPRECATED: get_dataframe called for user {chat_id}")
    
    import config
    if dict_type is None:
        dict_type = config.user_state.get(chat_id, {}).get("dict_type", "personal")
    
    file_path, language = get_user_file_path(chat_id) if dict_type == "personal" else get_common_file_path()
    
    # Перевірка наявності мови
    if language is None:
        print(f"Cannot determine language for user {chat_id}")
    
    if not file_path or not os.path.exists(file_path):
        # Create empty dataframe with required columns
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        # Set default values
        if len(df) == 0:
            df['priority'] = df['priority'].astype(float)
        
        if os.path.dirname(file_path) and not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        df.to_csv(file_path, index=False)
        print(f"Created new empty dictionary file for user {chat_id} at {file_path}")
        return df
    
    try:
        df = pd.read_csv(file_path)
        
        # Перевіряємо наявність необхідних колонок і додаємо їх, якщо відсутні
        if 'word' not in df.columns:
            df['word'] = ""
        if 'translation' not in df.columns:
            if language == 'uk' and 'uk_tran' in df.columns:
                df['translation'] = df['uk_tran']
            elif language == 'ru' and 'ru_tran' in df.columns:
                df['translation'] = df['ru_tran']
            else:
                df['translation'] = ""
        if 'priority' not in df.columns:
            df['priority'] = 0.0
            
        # Переконуємось, що priority має числовий тип
        df['priority'] = df['priority'].astype(float)
        
        return df
    except Exception as e:
        print(f"Error loading dataframe from {file_path}: {e}")
        # У випадку помилки повертаємо порожній DataFrame з правильною структурою
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        df['priority'] = df['priority'].astype(float)
        return df

def save_dataframe(chat_id, df, language="uk"):
    """Save DataFrame to file"""
    try:
        file_path = None
        if isinstance(language, str) and language.lower() in ["uk", "ru", "common"]:
            if language.lower() == "common":
                file_path, _ = get_common_file_path()
            else:
                # Ensure user directory exists
                user_dir = os.path.join(USER_DICT_DIR, str(chat_id))
                if not os.path.exists(user_dir):
                    os.makedirs(user_dir)
                
                file_path = os.path.join(user_dir, "dictionary.csv")
                
                # Update user language
                update_user_language(chat_id, language)
        
        if not file_path:
            print(f"Error: Could not determine file path for user {chat_id}, language {language}")
            return False
        
        # Перевіряємо наявність необхідних колонок перед збереженням
        if 'word' not in df.columns:
            df['word'] = ""
        if 'translation' not in df.columns:
            df['translation'] = ""
        if 'priority' not in df.columns:
            df['priority'] = 0.0
            
        # Переконуємось, що priority має числовий тип
        df['priority'] = df['priority'].astype(float)
        
        # Save DataFrame
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        print(f"Error saving dataframe: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_user_language(chat_id, language):
    """Update language preference for a user"""
    conn = db_manager.get_connection()  # Use the db_manager.get_connection function
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute('SELECT 1 FROM users WHERE chat_id = ?', (chat_id,))
    if cursor.fetchone():
        cursor.execute('UPDATE users SET language = ? WHERE chat_id = ?', (language, chat_id))
    else:
        cursor.execute('INSERT INTO users (chat_id, language) VALUES (?, ?)', (chat_id, language))
    
    conn.commit()
    conn.close()
    return True
