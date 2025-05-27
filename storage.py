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
    """Get file path for user's dictionary"""
    # Нові шляхи до файлів у директорії користувача
    ru_file = os.path.join(USER_DICT_DIR, f"ru_words_{chat_id}.csv")
    uk_file = os.path.join(USER_DICT_DIR, f"uk_words_{chat_id}.csv")
    
    if os.path.exists(ru_file):
        return ru_file, "ru"
    elif os.path.exists(uk_file):
        return uk_file, "uk"
    else:
        # Перевіряємо старі шляхи (для зворотної сумісності)
        old_ru_file = f"ru_words_{chat_id}.csv"
        old_uk_file = f"uk_words_{chat_id}.csv"
        
        if os.path.exists(old_ru_file):
            try:
                import shutil
                new_file = os.path.join(USER_DICT_DIR, f"ru_words_{chat_id}.csv")
                shutil.move(old_ru_file, new_file)
                print(f"Moved {old_ru_file} to {new_file}")
                return new_file, "ru"
            except Exception as e:
                print(f"Failed to move file {old_ru_file}: {e}")
                return old_ru_file, "ru"
        elif os.path.exists(old_uk_file):
            try:
                import shutil
                new_file = os.path.join(USER_DICT_DIR, f"uk_words_{chat_id}.csv")
                shutil.move(old_uk_file, new_file)
                print(f"Moved {old_uk_file} to {new_file}")
                return new_file, "uk"
            except Exception as e:
                print(f"Failed to move file {old_uk_file}: {e}")
                return old_uk_file, "uk"
        
        return None, None

def get_common_file_path():
    """Get file path for common dictionary"""
    common_file = os.path.join(USER_DICT_DIR, "common_dictionary.csv")
    
    # Перевіряємо, чи існує директорія, і створюємо її, якщо потрібно
    if not os.path.exists(USER_DICT_DIR):
        try:
            os.makedirs(USER_DICT_DIR)
            print(f"Created directory {USER_DICT_DIR}")
        except Exception as e:
            print(f"Cannot create directory {USER_DICT_DIR}: {e}")
            # Якщо не можемо створити директорію, використовуємо поточну
            common_file = "common_dictionary.csv"
    
    if not os.path.exists(common_file):
        # Create empty common dictionary if not exists
        df = pd.DataFrame(columns=["word", "translation", "priority", "article"])
        try:
            # Спочатку створюємо директорію, якщо вона не існує
            os.makedirs(os.path.dirname(common_file), exist_ok=True)
            df.to_csv(common_file, index=False, encoding='utf-8-sig')
            print(f"Created new common dictionary: {common_file}")
        except Exception as e:
            print(f"Failed to create common dictionary: {e}")
            # Якщо не вдалося створити файл у новому місці, використовуємо старий шлях
            if not os.path.exists(COMMON_DICT_FILE):
                try:
                    df.to_csv(COMMON_DICT_FILE, index=False, encoding='utf-8-sig')
                    print(f"Created common dictionary at old path: {COMMON_DICT_FILE}")
                except Exception as e2:
                    print(f"Cannot create common dictionary anywhere: {e2}")
            return COMMON_DICT_FILE, "common"
    
    return common_file, "common"

def get_dataframe(chat_id):
    """Get dataframe based on user's current dictionary choice"""
    # Визначаємо тип словника та виводимо для дебагу
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: get_dataframe for user {chat_id}, dict_type={dict_type}")
    
    if dict_type == "common":
        file_path, _ = get_common_file_path()
        print(f"Debug: Using common dictionary: {file_path}")
    else:
        file_path, _ = get_user_file_path(chat_id)
        print(f"Debug: Using personal dictionary: {file_path}")
        
    if not file_path:
        return None
    
    try:
        # Перевіряємо, чи існує файл перед читанням
        if not os.path.exists(file_path):
            # Якщо файл не існує, але це загальний словник
            if dict_type == "common":
                # Створюємо загальний словник, якщо він не існує
                df = pd.DataFrame(columns=["word", "translation", "priority", "article"])
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                return None
        
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        # Ensure 'article' column exists
        if 'article' not in df.columns:
            df['article'] = ''
            save_dataframe(chat_id, df, "uk" if "uk_" in file_path else "ru" if "ru_" in file_path else "common")
        
        return df
    except Exception as e:
        print(f"Error reading dataframe: {e}")
        # Якщо не вдалося прочитати файл, повертаємо None
        return None

def save_dataframe(chat_id, df, language):
    """Save dataframe to appropriate file with error handling"""
    # Визначаємо тип словника та виводимо для дебагу
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: save_dataframe for user {chat_id}, dict_type={dict_type}")
    
    try:
        if dict_type == "common":
            # Для загального словника завжди використовуємо шлях common_dictionary.csv
            file_path, _ = get_common_file_path()
            print(f"Debug: Saving to common dictionary: {file_path}")
        else:
            # Зберігаємо в директорію користувача з правильним префіксом (uk_ або ru_)
            if language not in ["uk", "ru"]:
                # Якщо мова не визначена, використовуємо uk за замовчуванням
                language = "uk"
            file_path = os.path.join(USER_DICT_DIR, f"{language}_words_{chat_id}.csv")
            print(f"Debug: Saving to personal dictionary: {file_path}")
        
        # Створюємо директорію для CSV файлів, якщо потрібно
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Пробуємо зберегти файл кілька разів
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                print(f"Successfully saved to {file_path}")
                return True
            except PermissionError as e:
                if attempt < max_attempts - 1:
                    print(f"PermissionError saving {file_path}. Retrying in 1 second...")
                    time.sleep(1)
                else:
                    print(f"Failed to save {file_path} after {max_attempts} attempts: {e}")
                    # Спробуємо зберегти в іншому місці як резервний варіант
                    backup_file = f"{language}_words_{chat_id}_backup.csv"
                    try:
                        df.to_csv(backup_file, index=False, encoding='utf-8-sig')
                        print(f"Saved backup to {backup_file}")
                        from config import bot
                        bot.send_message(chat_id, "⚠️ Виникли проблеми зі збереженням словника. Створено резервну копію.")
                        return True
                    except Exception as inner_e:
                        print(f"Failed to save backup file: {inner_e}")
            except Exception as e:
                print(f"Error saving {file_path}: {e}")
                break
        
        return False  # Не вдалося зберегти
    except Exception as e:
        print(f"Critical error in save_dataframe: {e}")
        import traceback
        traceback.print_exc()
        return False
