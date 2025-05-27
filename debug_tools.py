# -*- coding: utf-8 -*-
import os
import pandas as pd
from config import user_state, COMMON_DICT_FILE

def debug_dictionaries():
    """Print debug information about dictionaries"""
    # Перевірка загального словника
    common_exists = os.path.exists(COMMON_DICT_FILE)
    print(f"Common dictionary file ({COMMON_DICT_FILE}) exists: {common_exists}")
    
    if common_exists:
        try:
            df = pd.read_csv(COMMON_DICT_FILE, encoding='utf-8-sig')
            print(f"Common dictionary has {len(df)} entries")
            print(f"Columns: {df.columns.tolist()}")
            if not df.empty:
                print("First 3 entries:")
                print(df.head(3))
        except Exception as e:
            print(f"Error reading common dictionary: {e}")
    
    # Перевірка персональних словників
    personal_files = [f for f in os.listdir() if (f.startswith("ru_words_") or f.startswith("uk_words_")) and f.endswith(".csv")]
    print(f"Found {len(personal_files)} personal dictionary files")
    
    for file in personal_files:
        try:
            user_id = file.split("_")[2].split(".")[0]
            df = pd.read_csv(file, encoding='utf-8-sig')
            print(f"User {user_id} dictionary has {len(df)} entries")
            if not df.empty:
                print(f"First entry: {df.iloc[0].to_dict()}")
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    # Перевірка стану користувачів
    print(f"Current user_state has {len(user_state)} entries")
    for user_id, state in user_state.items():
        print(f"User {user_id}: dict_type = {state.get('dict_type', 'personal')}")

if __name__ == "__main__":
    debug_dictionaries()
