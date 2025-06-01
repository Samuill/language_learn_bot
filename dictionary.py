# -*- coding: utf-8 -*-
from config import user_state, bot, ADMIN_ID
from utils import clear_state, main_menu_keyboard
import db_manager

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
    
    data = user_state.get(chat_id, {})
    if not data or "word" not in data:
        bot.send_message(chat_id, "❌ Помилка: дані слова не знайдено.")
        clear_state(chat_id)
        return
    
    word = data["word"]
    translation = translation or data["auto_translation"]
    
    # Визначаємо артикль зі слова (якщо є)
    article = None
    import re
    article_match = re.match(r'^(der|die|das)\s+(.+)$', word, re.IGNORECASE)
    if article_match:
        article = article_match.group(1)
        # Слово без артикля передається автоматично в add_word через детекцію
    
    # Зберігаємо слово в базу даних із можливим артиклем
    success = db_manager.add_word(chat_id, word, translation, dict_type, article)
    
    if success:
        bot.send_message(
            chat_id, 
            "✅ Слово успішно додано!", 
            reply_markup=main_menu_keyboard(chat_id)
        )
    else:
        bot.send_message(
            chat_id, 
            "❌ Помилка при збереженні слова.", 
            reply_markup=main_menu_keyboard(chat_id)
        )
    
    # Очищаємо стан користувача, зберігаючи тип словника для адміна
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
    
    try:
        # Спочатку спробуємо використати SQLite для отримання слів
        import db_manager
        # Оновлюємо streak користувача
        streak = db_manager.update_user_streak(chat_id)
        print(f"User {chat_id} streak updated: {streak}")
        
        # Отримуємо слова для користувача
        df = db_manager.get_user_words(chat_id, dict_type)
        
        if df.empty:
            dict_name = "загальному словнику" if dict_type == "common" else "персональному словнику"
            bot.send_message(chat_id, f"📭 У {dict_name} ще немає доданих слів.")
            return False
    except Exception as e:
        print(f"Error using SQLite, falling back to CSV: {e}")
        # Резервний варіант: старий CSV метод
        from utils import track_activity
        track_activity(chat_id)
        from storage import get_dataframe
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
