# -*- coding: utf-8 -*-

"""
Обробники для перемикання між типами словників.
"""

from config import bot, user_state, ADMIN_ID
from utils import main_menu_keyboard, clear_state  # Добавляем импорт clear_state
from dictionary import toggle_dictionary, set_dictionary_type
import db_manager

@bot.message_handler(func=lambda message: message.text in ["🌐 Загальний словник", "👤 Персональний словник"])
def switch_dictionary(message):
    toggle_dictionary(message.chat.id)

@bot.message_handler(func=lambda message: message.text.startswith("👤 Персональний словник"))
def personal_dictionary_button(message):
    """Switch to personal dictionary"""
    chat_id = message.chat.id
    
    # Оновлюємо БД для очищення shared_dict_id
    import db_manager
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET shared_dict_id = NULL WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    
    # Оновлюємо стан в пам'яті
    if chat_id in user_state:
        user_state[chat_id].update({"dict_type": "personal"})
        if "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
    else:
        user_state[chat_id] = {"dict_type": "personal"}
    
    # Зберігаємо важливі дані, такі як рівень складності
    level = user_state.get(chat_id, {}).get("level", "easy")
    if level:
        user_state[chat_id]["level"] = level
    
    bot.send_message(chat_id, "📚 Обрано персональний словник.",
                    reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "🟢 Легкий рівень")
def easy_level(message):
    """Show easy level menu with learning activities"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника, але видаляємо повідомлення активності
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Оновлюємо рівень у стані
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        user_state[chat_id]["level"] = "easy"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "easy"}
    
    from utils import easy_level_keyboard
    bot.send_message(chat_id, "🟢 Легкий рівень - оберіть активність:", 
                   reply_markup=easy_level_keyboard())

@bot.message_handler(func=lambda message: message.text == "🟠 Середній рівень")
def medium_level(message):
    """Show medium level menu (placeholder)"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника, але видаляємо повідомлення активності
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Оновлюємо рівень у стані
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        user_state[chat_id]["level"] = "medium"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "medium"}
    
    # Show "under development" message
    bot.send_message(chat_id, "🟠 Середній рівень у розробці. Будь ласка, оберіть інший рівень.", 
                   reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "🔴 Складний рівень")
def hard_level(message):
    """Show hard level menu with learning activities"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника, але видаляємо повідомлення активності
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Оновлюємо рівень у стані
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        user_state[chat_id]["level"] = "hard"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "hard"}
    
    # Show hard level menu
    from utils import hard_level_keyboard
    bot.send_message(chat_id, "🔴 Складний рівень - оберіть активність:", 
                   reply_markup=hard_level_keyboard())
