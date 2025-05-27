# -*- coding: utf-8 -*-
import pandas as pd
import os
from config import translator, user_state, bot, ADMIN_ID
from storage import get_dataframe, save_dataframe, get_user_file_path, get_common_file_path
from utils import clear_state, main_menu_keyboard

def save_word(chat_id, translation=None):
    """Save word to dictionary"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: save_word for user {chat_id}, dict_type={dict_type}")
    
    # Check permissions for common dictionary
    if dict_type == "common" and chat_id != ADMIN_ID:
        bot.send_message(
            chat_id, 
            "❌ Додати слово неможливо, змініть свій словник на персональний.", 
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)
        return
    
    # Отримуємо мову зі стану користувача або використовуємо uk за замовчуванням
    language = user_state.get(chat_id, {}).get("language", "uk")
    
    # Визначаємо шлях до файлу залежно від типу словника
    if dict_type == "common" and chat_id == ADMIN_ID:
        # Для адміна використовуємо загальний словник
        file_path, _ = get_common_file_path()
        print(f"Debug: Admin is adding word to common dictionary: {file_path} using language: {language}")
    else:
        # Для всіх інших використовуємо персональний словник
        file_path, dict_language = get_user_file_path(chat_id)
        if dict_language:  # Якщо мова визначена в файлі, використовуємо її
            language = dict_language
        print(f"Debug: User is adding word to personal dictionary: {file_path} using language: {language}")
        
    if not file_path:
        bot.send_message(chat_id, "❌ Мову перекладу не обрано. Спробуйте /start.")
        return
    
    # Отримуємо DataFrame для відповідного словника (залежно від dict_type)
    if dict_type == "common" and chat_id == ADMIN_ID:
        # Для адміна ми явно отримуємо загальний словник
        common_path, _ = get_common_file_path()
        if os.path.exists(common_path):
            df = pd.read_csv(common_path, encoding='utf-8-sig')
        else:
            df = pd.DataFrame(columns=["word", "translation", "priority", "article"])
    else:
        # Для звичайних користувачів використовуємо звичайний get_dataframe
        df = get_dataframe(chat_id)
        
    if df is None:
        df = pd.DataFrame(columns=["word", "translation", "priority", "article"])
    
    data = user_state[chat_id]
    translation = translation or data["auto_translation"]
    
    new_row = pd.DataFrame({
        "word": [data["word"]],
        "translation": [translation],
        "priority": [0.0],
        "article": [""]  # Додаємо порожній артикль за замовчуванням
    })
    
    if not new_row.empty:
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Зберігаємо у відповідний файл, явно передаючи тип словника
        if dict_type == "common" and chat_id == ADMIN_ID:
            # Для адміна зберігаємо безпосередньо в загальний словник
            common_path, _ = get_common_file_path()
            df.to_csv(common_path, index=False, encoding='utf-8-sig')
            print(f"Debug: Directly saved to common dictionary: {common_path}")
            
            # Викликаємо clear_state з збереженням типу словника для адміна
            clear_state(chat_id, preserve_dict_type=True)
        else:
            # Для звичайних користувачів використовуємо стандартну функцію
            save_dataframe(chat_id, df, language)
            clear_state(chat_id)
    else:
        # Якщо не додавали нові рядки, просто очищуємо стан
        preserve_dict_type = (chat_id == ADMIN_ID and dict_type == "common")
        clear_state(chat_id, preserve_dict_type=preserve_dict_type)

def start_activity(chat_id, mode):
    """Start learning or repetition activity"""
    # Зберігаємо поточний тип словника перед очищенням стану
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: Starting {mode} activity for user {chat_id} with dict_type={dict_type}")
    
    clear_state(chat_id)
    
    # Відразу встановлюємо поточний тип словника після очищення
    user_state[chat_id] = {"dict_type": dict_type}
    
    from utils import track_activity
    track_activity(chat_id)
    
    df = get_dataframe(chat_id)
    if df is None or df.empty:
        dict_name = "загальному словнику" if dict_type == "common" else "персональному словнику"
        bot.send_message(chat_id, f"📭 У {dict_name} ще немає доданих слів.")
        return False
    
    if mode == 'repeat':
        from handlers import start_repetition
        return start_repetition(chat_id, df)
    elif mode == 'learn':
        from handlers import start_learning
        return start_learning(chat_id, df)
    return False

def set_dictionary_type(chat_id, dict_type):
    """Set dictionary type to personal or common"""
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    # Зберігаємо попередній тип для порівняння
    prev_type = user_state[chat_id].get("dict_type", "personal")
    
    # Встановлюємо новий тип словника
    user_state[chat_id]["dict_type"] = dict_type
    print(f"Set dictionary type for {chat_id} to {dict_type}")
    
    # Перевіряємо доступність вибраного словника
    if dict_type == "common":
        common_file, _ = get_common_file_path()
        if not os.path.exists(common_file):
            print(f"Warning: Common dictionary file does not exist: {common_file}")
            # Якщо файл не існує, спробуємо його створити
            try:
                common_df = pd.DataFrame(columns=["word", "translation", "priority", "article"])
                os.makedirs(os.path.dirname(common_file), exist_ok=True)
                common_df.to_csv(common_file, index=False, encoding='utf-8-sig')
                print(f"Created common dictionary: {common_file}")
            except Exception as e:
                print(f"Error creating common dictionary: {e}")
    else:  # personal
        file_path, _ = get_user_file_path(chat_id)
        if not file_path:
            print(f"Warning: User {chat_id} has no personal dictionary")
    
    # Інформуємо користувача про зміну
    dict_name = "загальний" if dict_type == "common" else "персональний"
    message = f"📚 Обрано {dict_name} словник."
    
    # Додаємо попередження для звичайних користувачів щодо загального словника
    if dict_type == "common" and chat_id != ADMIN_ID:
        message += "\n⚠️ У загальному словнику ви можете тільки вчити та повторювати слова."
    
    # Завжди надсилаємо повідомлення про вибір словника
    try:
        bot.send_message(chat_id, message, reply_markup=main_menu_keyboard(chat_id))
    except Exception as e:
        print(f"Error sending dictionary change message: {e}")
    
    return dict_type

# Залишаємо toggle_dictionary для зворотної сумісності
def toggle_dictionary(chat_id):
    """Toggle between personal and common dictionary"""
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    current = user_state[chat_id].get("dict_type", "personal")
    new_type = "common" if current == "personal" else "personal"
    return set_dictionary_type(chat_id, new_type)
