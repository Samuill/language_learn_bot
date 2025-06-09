# -*- coding: utf-8 -*-

"""
Обробники для головного меню та базової навігації.
"""

import db_manager
from config import bot, user_state
from utils import clear_state, track_activity, main_menu_keyboard
from utils.language_utils import get_text
from utils.state_helpers import save_message_id
from handlers.start import show_language_selection
from utils.console_logger import log_menu_transition, log_displayed_buttons, MENU_MAIN

@bot.message_handler(commands=["start"])
def main_menu(message):
    """Show main menu or language selection"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є мова в БД
    language = db_manager.get_user_language(chat_id)
    track_activity(chat_id)
    
    if not language:
        # Якщо мови немає, пропонуємо обрати (тільки для нових користувачів)
        show_language_selection(chat_id)
        user_state[chat_id] = {"state": "language_selection"}
    else:
        # Мова вже встановлена - показуємо головне меню
        clear_state(chat_id)
        
        # Get dictionary info
        dict_type, shared_dict_id, _ = db_manager.get_user_dictionary_info(chat_id)
        
        user_state[chat_id] = {
            "language": language,
            "dict_type": dict_type,
            "level": "easy",  # Default level
            "current_menu": "main"
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
            
        log_menu_transition(chat_id, "UNKNOWN", MENU_MAIN, "Command: /start")
        
        # Show current dictionary info in menu message
        menu_message = get_text("main_menu", chat_id)
        
        if dict_type == "shared" and shared_dict_id:
            # Get shared dictionary name
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
            result = cursor.fetchone()
            if result:
                dict_name = result[0]
                menu_message += f"\n\n📚 {get_text('current_dictionary', chat_id, 'Поточний словник')}: {dict_name} ({get_text('shared_dictionary', chat_id)})"
            conn.close()
        else:
            menu_message += f"\n\n📚 {get_text('current_dictionary', chat_id, 'Поточний словник')}: {get_text(f'{dict_type}_dictionary', chat_id)}"
        
        keyboard = main_menu_keyboard(chat_id)
        
        # Логируем отображаемые кнопки без emoji
        button_texts = [button.text for row in keyboard.keyboard for button in row]
        log_displayed_buttons(chat_id, button_texts, MENU_MAIN)
        
        sent_message = bot.send_message(
            chat_id, 
            menu_message,
            reply_markup=keyboard
        )
        save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(func=lambda message: message.text in ["✖️ Відміна", "Відміна"] or 
                                        message.text == get_text("cancel", message.chat.id))
def cancel_action(message):
    """Cancel current action and return to main menu"""
    chat_id = message.chat.id
    
    # Логируем переход в главное меню из-за отмены
    from_menu = user_state.get(chat_id, {}).get("current_menu", "UNKNOWN")
    log_menu_transition(chat_id, from_menu, MENU_MAIN, "Action: Cancel")
    
    # Сохраняем текущее меню в состоянии пользователя
    clear_state(chat_id)
    user_state[chat_id]["current_menu"] = "main"
    
    keyboard = main_menu_keyboard(chat_id)
    
    # Логируем отображаемые кнопки
    button_texts = [button.text for row in keyboard.keyboard for button in row]
    log_displayed_buttons(chat_id, button_texts, MENU_MAIN)
    
    sent_message = bot.send_message(
        chat_id, 
        get_text("cancelled", chat_id), 
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(func=lambda message: message.text == "↩️ Повернутися до головного меню" or 
                                        message.text == get_text("back_to_main_menu", message.chat.id))
def return_to_main_menu(message):
    """Return to main menu"""
    chat_id = message.chat.id
    
    # Логируем переход в главное меню
    from_menu = user_state.get(chat_id, {}).get("current_menu", "UNKNOWN")
    log_menu_transition(chat_id, from_menu, MENU_MAIN, "Action: Return to main menu")
    
    # Очищаем состояние, сохраняя тип словаря
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Явно устанавливаем текущее меню
    if chat_id in user_state:
        user_state[chat_id]["current_menu"] = "main"
    else:
        user_state[chat_id] = {"current_menu": "main"}
    
    # Get dictionary info
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    
    # Prepare menu message with dictionary info
    menu_message = get_text("main_menu", chat_id)
    
    if dict_type == "shared" and shared_dict_id:
        # Get shared dictionary name
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
        result = cursor.fetchone()
        if result:
            dict_name = result[0]
            menu_message += f"\n\n📚 {get_text('current_dictionary', chat_id, 'Поточний словник')}: {dict_name} ({get_text('shared_dictionary', chat_id)})"
        conn.close()
    else:
        menu_message += f"\n\n📚 {get_text('current_dictionary', chat_id, 'Поточний словник')}: {get_text(f'{dict_type}_dictionary', chat_id)}"
    
    keyboard = main_menu_keyboard(chat_id)
    
    # Логируем отображаемые кнопки
    button_texts = [button.text for row in keyboard.keyboard for button in row]
    log_displayed_buttons(chat_id, button_texts, MENU_MAIN)
    
    sent_message = bot.send_message(
        chat_id, 
        menu_message,
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)
