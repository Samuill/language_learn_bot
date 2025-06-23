# -*- coding: utf-8 -*-

"""
Обробники для перемикання між типами словників.
"""

from config import bot, user_state, ADMIN_ID
from utils import main_menu_keyboard, clear_state, easy_level_keyboard, medium_level_keyboard, hard_level_keyboard
from utils.keyboards import shared_dictionary_keyboard
from utils.state_helpers import save_message_id
import db_manager
from utils.language_utils import get_text
from utils.input_handlers import safe_next_step_handler, sanitize_user_input
from utils.console_logger import log_menu_transition, log_displayed_buttons, MENU_MAIN, MENU_EASY, MENU_MEDIUM, MENU_HARD, MENU_SHARED

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
        
    # Safely extract button texts for logging
    try:
        button_texts = []
        if hasattr(keyboard, 'keyboard'):
            for row in keyboard.keyboard:
                for button in row:
                    if hasattr(button, 'text'):
                        button_texts.append(button.text)
                    elif isinstance(button, dict) and 'text' in button:
                        button_texts.append(button['text'])
    except Exception as e:
        print(f"Error extracting button texts: {e}")
    
    # Log displayed buttons only if we successfully extracted texts
    if button_texts:
        log_displayed_buttons(chat_id, button_texts, menu_type)
    else:
        print(f"Warning: Could not extract button texts for user {chat_id} in {menu_type} menu")
    
    # Відправляємо меню відповідного рівня
    sent_message = bot.send_message(
        chat_id, 
        message_text, 
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(func=lambda message: message.text.startswith("👤") or message.text == get_text("personal_dictionary", message.chat.id))
def personal_dictionary_handler(message):
    """Handle switching to the personal dictionary."""
    chat_id = message.chat.id
    
    # Switch to Personal Dictionary
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET dict_type = ?, shared_dict_id = ? WHERE chat_id = ?", ('personal', None, chat_id))
    conn.commit()
    conn.close()

    db_manager.sync_user_state_with_db(chat_id)
    
    log_menu_transition(chat_id, user_state.get(chat_id, {}).get("current_menu", "UNKNOWN"), MENU_MAIN, "Switched to personal dictionary")

    from .main_menu import return_to_main_menu
    return_to_main_menu(message)

@bot.message_handler(func=lambda message: message.text == get_text("edit_word", message.chat.id) or message.text == "✏️ Редаггувати слово")
def edit_word_menu(message):
    """Show word management menu - same logic as level buttons"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника, але видаляємо повідомлення активності  
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Імпортуємо word_management_menu_keyboard
    from handlers.edit_word import word_management_menu_keyboard
    
    # Створюємо клавіатуру для меню редагування
    keyboard = word_management_menu_keyboard(chat_id)
    message_text = get_text("word_management_menu_prompt", chat_id, "Меню керування словами:")
    
    # Оновлюємо стан користувача
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    if chat_id in user_state:
        user_state[chat_id].update({
            "current_menu": "EDIT_WORD_MENU"
        })
    else:
        user_state[chat_id] = {
            "dict_type": dict_type,
            "current_menu": "EDIT_WORD_MENU"
        }
        
    if shared_dict_id:
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
    # Логирование кнопок
    try:
        button_texts = []
        if hasattr(keyboard, 'keyboard'):
            for row in keyboard.keyboard:
                for button in row:
                    if hasattr(button, 'text'):
                        button_texts.append(button.text)
                    elif isinstance(button, dict) and 'text' in button:
                        button_texts.append(button['text'])
    except Exception as e:
        print(f"Error extracting button texts: {e}")
    
    # Log displayed buttons only if we successfully extracted texts
    if button_texts:
        log_displayed_buttons(chat_id, button_texts, "EDIT_WORD_MENU")
    else:
        print(f"Warning: Could not extract button texts for user {chat_id} in EDIT_WORD_MENU menu")
    
    # Відправляємо меню редагування
    sent_message = bot.send_message(
        chat_id, 
        message_text, 
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)

def switch_dictionary(message):
    """Switch between dictionaries (personal/shared)"""
    chat_id = message.chat.id
    
    # Get current dictionary type
    current_dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Toggle between personal and shared
    if current_dict_type == "personal":
        # Show shared dictionaries menu
        from handlers.shared_dicts import shared_dictionary_menu
        shared_dictionary_menu(message)
    else:
        # Switch back to personal dictionary
        user_state[chat_id] = {
            "dict_type": "personal",
            "level": user_state.get(chat_id, {}).get("level", "easy")
        }
        
        if "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
            
        # Update database
        db_manager.update_user_dictionary_type(chat_id, "personal", None)
        
        # Send confirmation
        bot.send_message(
            chat_id, 
            get_text("switched_to_personal", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )
