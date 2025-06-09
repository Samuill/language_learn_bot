# -*- coding: utf-8 -*-

"""
Обробники для перемикання між типами словників.
"""

from config import bot, user_state, ADMIN_ID
from utils import main_menu_keyboard, clear_state, easy_level_keyboard, medium_level_keyboard, hard_level_keyboard
from utils.state_helpers import save_message_id
from dictionary import toggle_dictionary, set_dictionary_type
import db_manager
from utils.language_utils import get_text
from utils.input_handlers import safe_next_step_handler, sanitize_user_input
from utils.console_logger import log_menu_transition, log_displayed_buttons, MENU_MAIN, MENU_EASY, MENU_MEDIUM, MENU_HARD, MENU_SHARED

# Make sure switch_dictionary function exists for backward compatibility
def switch_dictionary(message):
    """Toggle between personal and common dictionaries - compatibility function"""
    if hasattr(message, 'chat'):
        toggle_dictionary(message.chat.id)
    elif isinstance(message, int):
        toggle_dictionary(message)

# Додаємо функцію switch_dictionary, яка відсутня
@bot.message_handler(func=lambda message: message.text in ["🌐 Загальний словник", "👤 Персональний словник"])
def switch_dictionary_handler(message):
    """Handler for dictionary switching button"""
    toggle_dictionary(message.chat.id)

# Універсальний обробник для встановлення рівня складності
@bot.message_handler(func=lambda message: message.text in [
    "🟢 Легкий рівень", "🟠 Середній рівень", "🔴 Складний рівень", 
    get_text("easy_level", message.chat.id), 
    get_text("medium_level", message.chat.id), 
    get_text("hard_level", message.chat.id)
])
def set_difficulty_level(message):
    """Set difficulty level based on button pressed"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника, але видаляємо повідомлення активності
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Визначаємо рівень та клавіатуру в залежності від кнопки
    if message.text in ["🟢 Легкий рівень", get_text("easy_level", chat_id)]:
        level = "easy"
        menu_type = MENU_EASY
        keyboard = easy_level_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("easy_level_select_activity", chat_id)
        log_menu_transition(chat_id, user_state.get(chat_id, {}).get("current_menu", "UNKNOWN"), MENU_EASY, f"Button: {message.text}")
    elif message.text in ["🟠 Середній рівень", get_text("medium_level", chat_id)]:
        level = "medium"
        menu_type = MENU_MEDIUM
        keyboard = medium_level_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("medium_level_select_activity", chat_id)
        log_menu_transition(chat_id, user_state.get(chat_id, {}).get("current_menu", "UNKNOWN"), MENU_MEDIUM, f"Button: {message.text}")
    else:  # "🔴 Складний рівень" або локалізований варіант
        level = "hard"
        menu_type = MENU_HARD
        keyboard = hard_level_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("hard_level_select_activity", chat_id)
        log_menu_transition(chat_id, user_state.get(chat_id, {}).get("current_menu", "UNKNOWN"), MENU_HARD, f"Button: {message.text}")
    
    # Оновлюємо рівень у стані користувача
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    if chat_id in user_state:
        user_state[chat_id].update({
            "level": level,
            "current_menu": menu_type
        })
    else:
        user_state[chat_id] = {
            "dict_type": dict_type, 
            "level": level,
            "current_menu": menu_type
        }
        
    if shared_dict_id:
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
    # Логируем отображаемые кнопки
    button_texts = [button.text for row in keyboard.keyboard for button in row]
    log_displayed_buttons(chat_id, button_texts, menu_type)
    
    # Відправляємо меню відповідного рівня
    sent_message = bot.send_message(
        chat_id, 
        message_text, 
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(func=lambda message: message.text in ["👤 Персональний словник", get_text("personal_dictionary", message.chat.id)])
def personal_dictionary_button(message):
    """Switch to personal dictionary"""
    chat_id = message.chat.id
    
    # Log transition
    log_menu_transition(chat_id, user_state.get(chat_id, {}).get("current_menu", "UNKNOWN"), MENU_MAIN, "Switched to personal dictionary")
    
    # Оновлюємо БД для очищення shared_dict_id
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET shared_dict_id = NULL WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    
    # Оновлюємо стан в пам'яті
    if chat_id in user_state:
        user_state[chat_id].update({"dict_type": "personal", "current_menu": "main"})
        if "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
    else:
        user_state[chat_id] = {"dict_type": "personal", "current_menu": "main"}
    
    # Зберігаємо важливі дані, такі як рівень складності
    level = user_state.get(chat_id, {}).get("level", "easy")
    if level:
        user_state[chat_id]["level"] = level
        
    keyboard = main_menu_keyboard(chat_id)
    
    # Логируем отображаемые кнопки
    button_texts = [button.text for row in keyboard.keyboard for button in row]
    log_displayed_buttons(chat_id, button_texts, MENU_MAIN)
    
    sent_message = bot.send_message(
        chat_id, 
        get_text("selected_dict", chat_id),
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)
