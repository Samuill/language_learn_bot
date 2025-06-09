# -*- coding: utf-8 -*-

"""
Утиліти для обробки введення користувача.
"""

import telebot
from config import bot, user_state
from utils.language_utils import get_text

# Список команд, які можуть бути використані для виходу з активності
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
        
    # Перевірка команд з / на початку
    if message.text.startswith('/'):
        return True
    
    # Перевірка основних кнопок меню
    if message.text in [
        "➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити",
        "🧩 Складна гра", "📝 Введення слів", "🏷️ Введення артиклів",
        "👤 Персональний словник", "👥 Спільний словник",
        "🔤 Вибір правильного написання", "📝 Заповніть пропуски"
    ] + EXIT_COMMANDS:
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

def handle_exit_from_activity(message):
    """Handle exit from activity using menu buttons
    
    Args:
        message: Telegram message with exit command
    """
    from utils import clear_state, main_menu_keyboard
    from utils import easy_level_keyboard, medium_level_keyboard, hard_level_keyboard
    
    chat_id = message.chat.id
    preserve_dict_type = True
    
    # Визначаємо, яке меню показати в залежності від команди, використовуючи локалізацію
    if message.text in ["↩️ Повернутися до головного меню", get_text("back_to_main_menu", chat_id)]:
        keyboard = main_menu_keyboard(chat_id)  # Передаємо chat_id для локалізації кнопок
        message_text = get_text("main_menu", chat_id)
        preserve_level = False
    elif message.text in ["🟢 Легкий рівень", get_text("easy_level", chat_id)]:
        keyboard = easy_level_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("easy_level_select_activity", chat_id)
        preserve_level = True
        if chat_id in user_state:
            user_state[chat_id]["level"] = "easy"
    elif message.text in ["🟠 Середній рівень", get_text("medium_level", chat_id)]:
        keyboard = medium_level_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("medium_level_select_activity", chat_id)
        preserve_level = True
        if chat_id in user_state:
            user_state[chat_id]["level"] = "medium"
    elif message.text in ["🔴 Складний рівень", get_text("hard_level", chat_id)]:
        keyboard = hard_level_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("hard_level_select_activity", chat_id)
        preserve_level = True
        if chat_id in user_state:
            user_state[chat_id]["level"] = "hard"
    else:  # "✖️ Відміна" або "Відміна" або локалізовані версії
        keyboard = main_menu_keyboard(chat_id)  # Передаємо chat_id для локалізації
        message_text = get_text("cancelled", chat_id)
        preserve_level = False
    
    # Очищаємо стан, зберігаючи потрібні дані
    clear_state(chat_id, preserve_dict_type=preserve_dict_type, preserve_level=preserve_level)
    
    # Відправляємо повідомлення з відповідною клавіатурою
    bot.send_message(chat_id, message_text, reply_markup=keyboard)

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
