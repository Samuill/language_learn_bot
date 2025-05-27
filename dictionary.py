# -*- coding: utf-8 -*-
import pandas as pd
from config import translator, user_state, bot, ADMIN_ID
from storage import get_dataframe, save_dataframe, get_user_file_path, get_common_file_path
from utils import clear_state, main_menu_keyboard

def save_word(chat_id, translation=None):
    """Save word to dictionary"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Check permissions for common dictionary
    if dict_type == "common" and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ Тільки адміністратор може додавати слова до загального словника!")
        clear_state(chat_id)
        return
        
    if dict_type == "common":
        file_path, language = get_common_file_path()
    else:
        file_path, language = get_user_file_path(chat_id)
        
    if not file_path:
        bot.send_message(chat_id, "❌ Мову перекладу не обрано. Спробуйте /start.")
        return
    
    df = get_dataframe(chat_id)
    if df is None:
        df = pd.DataFrame(columns=["word", "translation", "priority"])
    data = user_state[chat_id]
    translation = translation or data["auto_translation"]
    
    new_row = pd.DataFrame({
        "word": [data["word"]],
        "translation": [translation],
        "priority": [0.0]
    })
    
    if not new_row.empty:
        df = pd.concat([df, new_row], ignore_index=True)
        save_dataframe(chat_id, df, language)
    clear_state(chat_id)

def start_activity(chat_id, mode):
    """Start learning or repetition activity"""
    clear_state(chat_id)
    from utils import track_activity
    track_activity(chat_id)
    
    df = get_dataframe(chat_id)
    if df is None or df.empty:
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        dict_name = "загальному словнику" if dict_type == "common" else "вас"
        bot.send_message(chat_id, f"📭 У {dict_name} ще немає доданих слів.")
        return False
    
    if mode == 'repeat':
        from handlers import start_repetition
        return start_repetition(chat_id, df)
    elif mode == 'learn':
        from handlers import start_learning
        return start_learning(chat_id, df)
    return False

def toggle_dictionary(chat_id):
    """Toggle between personal and common dictionary"""
    if chat_id not in user_state:
        user_state[chat_id] = {}
        
    current = user_state[chat_id].get("dict_type", "personal")
    new_type = "common" if current == "personal" else "personal"
    user_state[chat_id]["dict_type"] = new_type
    
    # Inform user of the change
    dict_name = "загальний" if new_type == "common" else "персональний"
    bot.send_message(chat_id, f"📚 Обрано {dict_name} словник.", reply_markup=main_menu_keyboard(chat_id))
    
    return new_type
