# -*- coding: utf-8 -*-

"""
Утиліти для обробки введення користувача.
"""

import telebot
from config import bot, user_state
from utils.language_utils import get_text
from utils import clear_state, main_menu_keyboard, easy_level_keyboard, medium_level_keyboard, hard_level_keyboard
from utils.console_logger import log_menu_transition, MENU_MAIN

# Список стандартних команд, які можуть бути використані для виходу з активності
EXIT_COMMANDS = [
    "↩️ Повернутися до головного меню", 
    "🟢 Легкий рівень", 
    "🟠 Середній рівень", 
    "🔴 Складний рівень",
    "✖️ Відміна",
    "Відміна"
]

def is_system_command(message):
    """Check if message text is a system command or menu button
    
    Args:
        message: Telegram message
        
    Returns:
        bool: True if message is a system command
    """
    if not hasattr(message, 'text') or not message.text:
        return False
    
    chat_id = message.chat.id
        
    # Перевірка команд з / на початку
    if message.text.startswith('/'):
        return True
    
    # Перевірка локалізованих кнопок меню
    localized_commands = [
        get_text("back_to_main_menu", chat_id),
        get_text("easy_level", chat_id),
        get_text("medium_level", chat_id),
        get_text("hard_level", chat_id),
        get_text("cancel", chat_id),
        get_text("add_new_word", chat_id),
        get_text("learning_new_words", chat_id),
        get_text("repetition", chat_id),
        get_text("advanced_game", chat_id),
        get_text("word_typing", chat_id),
        get_text("article_typing", chat_id),
        get_text("personal_dictionary", chat_id),
        get_text("shared_dictionary", chat_id),
        get_text("choose_correct_spelling", chat_id),
        get_text("fill_in_gaps", chat_id)
    ]
    
    # Перевірка основних кнопок меню (нелокалізованих)
    if message.text in EXIT_COMMANDS or message.text in localized_commands:
        return True
    
    # Перевірка команд вибору мови
    if message.text.startswith(('🇬🇧', '🇺🇦', '🇷🇺', '🇹🇷', '🇸🇾')):
        return True
        
    return False

def sanitize_user_input(text, max_length=100):
    """Sanitize user input to prevent SQL injection and limit input length
    
    Args:
        text (str): Input text to sanitize
        max_length (int): Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
        
    # Обмеження довжини
    sanitized = text[:max_length]
    
    # Видалення потенційно небезпечних символів SQL
    sanitized = sanitized.replace("'", "''")
    sanitized = sanitized.replace(";", "")
    
    return sanitized

def handle_exit_from_activity(message, preserve_level=None):
    """Unified handler for exiting from any activity back to a menu"""
    from config import bot, user_state

    chat_id = message.chat.id
    # Recognize localized cancel as return-to-main
    localized_cancel = get_text("cancel", chat_id)
    
    # Determine which menu to go back to based on message text
    if message.text == "↩️ Повернутися до головного меню" \
       or message.text == get_text("back_to_main_menu", chat_id) \
       or message.text == localized_cancel:
        # Log transition to main menu
        log_menu_transition(chat_id, user_state.get(chat_id, {}).get("current_menu", "UNKNOWN"), MENU_MAIN, "Action: Return to main menu")
        
        # Clear state but preserve dictionary type and shared_dict_id
        preserve_level = False  # Always reset level when returning to main menu
        clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=preserve_level)
        
        # Set current menu state to main
        if chat_id in user_state:
            user_state[chat_id]["current_menu"] = MENU_MAIN
        else:
            user_state[chat_id] = {"current_menu": MENU_MAIN}
        
        # Show main menu
        from handlers.main_menu import main_menu
        main_menu(message)
        
    elif message.text == "🟢 Легкий рівень" or message.text == get_text("easy_level", chat_id):
        # Go to easy level menu
        from handlers.dictionaries import set_difficulty_level
        set_difficulty_level(message)
        
    elif message.text == "🟠 Середній рівень" or message.text == get_text("medium_level", chat_id):
        # Go to medium level menu
        from handlers.dictionaries import set_difficulty_level
        set_difficulty_level(message)
        
    elif message.text == "🔴 Складний рівень" or message.text == get_text("hard_level", chat_id):
        # Go to hard level menu
        from handlers.dictionaries import set_difficulty_level
        set_difficulty_level(message)
        
    else:
        # Default: return to the appropriate menu based on level
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        if level == "hard":
            bot.send_message(chat_id, get_text("hard_level_select_activity", chat_id), reply_markup=hard_level_keyboard(chat_id))
        elif level == "medium":
            bot.send_message(chat_id, get_text("medium_level_select_activity", chat_id), reply_markup=medium_level_keyboard(chat_id))
        else:  # Default to easy
            bot.send_message(chat_id, get_text("easy_level_select_activity", chat_id), reply_markup=easy_level_keyboard(chat_id))
        
        # Очищаємо стан, зберігаючи потрібні дані
        clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)

def safe_next_step_handler(message, callback, *args, **kwargs):
    """Safe version of register_next_step_handler that handles exit commands
    
    Args:
        message: Message to register handler for
        callback: Callback function
        *args, **kwargs: Arguments to pass to the callback
    """
    def wrapper(message):
        chat_id = message.chat.id
        
        # Отримуємо локалізовані команди виходу
        localized_back_to_main = get_text("back_to_main_menu", chat_id)
        localized_cancel = get_text("cancel", chat_id)
        
        # Перевіряємо на локалізовані та стандартні команди виходу
        if message.text in EXIT_COMMANDS or message.text == localized_back_to_main or message.text == localized_cancel:
            # Обробка команди виходу
            handle_exit_from_activity(message)
            return
            
        # Якщо не команда виходу, викликаємо оригінальний колбек
        try:
            callback(message, *args, **kwargs)
        except Exception as e:
            print(f"Error in safe_next_step_handler callback: {e}")
            import traceback
            traceback.print_exc()
            
            # Відправляємо повідомлення про помилку
            chat_id = message.chat.id
            bot.send_message(chat_id, get_text("error_occurred", chat_id))
    
    # Реєструємо обробник з нашим wrapper
    bot.register_next_step_handler(message, wrapper)

def is_menu_navigation_command(message):
    """Check if message is a menu navigation command"""
    common_menu_commands = [
        "↩️ Повернутися до головного меню", 
        "🟢 Легкий рівень", 
        "🟠 Середній рівень", 
        "🔴 Складний рівень",
        "✖️ Відміна",
        "👤 Персональний словник",
        "👥 Спільний словник"
    ]
    
    # Check direct matches or localized versions
    if hasattr(message, 'text') and message.text:
        if message.text in common_menu_commands:
            return True
        
        # Try to match with localized text if available
        if message.chat and hasattr(message, 'chat'):
            chat_id = message.chat.id
            back_text = get_text("back_to_main_menu", chat_id, "")
            easy_text = get_text("easy_level", chat_id, "")
            medium_text = get_text("medium_level", chat_id, "")
            hard_text = get_text("hard_level", chat_id, "")
            cancel_text = get_text("cancel", chat_id, "")
            
            localized_commands = [back_text, easy_text, medium_text, hard_text, cancel_text]
            if message.text in localized_commands:
                return True
    
    return False
