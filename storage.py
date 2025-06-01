# -*- coding: utf-8 -*-
import os
import pandas as pd
import time
from config import COMMON_DICT_FILE, user_state

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
        import db_manager
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

def get_dataframe(chat_id):
    """
    DEPRECATED: Use db_manager.get_user_words instead
    This function forwards the request to the database
    """
    print(f"DEPRECATED: get_dataframe called for user {chat_id}")
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    try:
        import db_manager
        return db_manager.get_user_words(chat_id, dict_type)
    except Exception as e:
        print(f"ERROR: Failed to get words from database: {e}")
        import traceback
        traceback.print_exc()
        
    return pd.DataFrame(columns=["id", "word", "translation", "article", "priority"])

def save_dataframe(chat_id, df, language):
    """
    DEPRECATED: This function does nothing, updates should use db_manager functions
    """
    print(f"DEPRECATED: save_dataframe called but ignored for user {chat_id}")
    return False
