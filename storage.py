# -*- coding: utf-8 -*-
import os
import pandas as pd
from config import COMMON_DICT_FILE, user_state

def get_user_file_path(chat_id):
    """Get file path for user's dictionary"""
    # Check if user has a file
    ru_file = f"ru_words_{chat_id}.csv"
    uk_file = f"uk_words_{chat_id}.csv"
    
    if os.path.exists(ru_file):
        return ru_file, "ru"
    elif os.path.exists(uk_file):
        return uk_file, "uk"
    else:
        return None, None

def get_common_file_path():
    """Get file path for common dictionary"""
    if not os.path.exists(COMMON_DICT_FILE):
        # Create empty common dictionary if not exists
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        df.to_csv(COMMON_DICT_FILE, index=False, encoding='utf-8-sig')
    return COMMON_DICT_FILE, "common"

def get_dataframe(chat_id):
    """Get dataframe based on user's current dictionary choice"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    if dict_type == "common":
        file_path, _ = get_common_file_path()
    else:
        file_path, _ = get_user_file_path(chat_id)
        
    if not file_path:
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

def save_dataframe(chat_id, df, language):
    """Save dataframe to appropriate file"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    if dict_type == "common":
        file_path = COMMON_DICT_FILE
    else:
        file_path = f"{language}_words_{chat_id}.csv"
        
    df.to_csv(file_path, index=False, encoding='utf-8-sig')
