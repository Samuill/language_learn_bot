# -*- coding: utf-8 -*-

"""
Допоміжні функції для роботи з ботом, включаючи логування відповідей.
"""

from config import bot
from utils.logger import log_response, log_error, extract_user_info

def send_message_with_logging(chat_id, text, reply_markup=None, parse_mode=None):
    """
    Відправляє повідомлення користувачеві та логує його.
    
    Args:
        chat_id: ID чату користувача
        text: Текст повідомлення для відправки
        reply_markup: Об'єкт клавіатури (опціонально)
        parse_mode: Режим парсингу (HTML, Markdown, None)
        
    Returns:
        telebot.types.Message: Об'єкт відправленого повідомлення
    """
    try:
        # Отримуємо інформацію про користувача
        user_info = None
        try:
            # Спроба отримати інформацію про користувача
            user = bot.get_chat_member(chat_id, chat_id).user
            user_info = {
                "user_id": user.id,
                "username": user.username if user.username else "No username",
                "first_name": user.first_name if user.first_name else "No first name",
                "last_name": user.last_name if user.last_name else "No last name"
            }
        except Exception as e:
            # Якщо не вдалося отримати інформацію, використовуємо мінімальні дані
            user_info = {
                "user_id": chat_id,
                "username": "Unknown",
                "first_name": "Unknown",
                "last_name": "Unknown"
            }
        
        # Відправляємо повідомлення
        sent_message = bot.send_message(
            chat_id, 
            text, 
            reply_markup=reply_markup, 
            parse_mode=parse_mode
        )
        
        # Логуємо відправлене повідомлення
        log_response(
            user_info["user_id"],
            user_info["username"],
            user_info["first_name"],
            user_info["last_name"],
            text
        )
        
        return sent_message
    
    except Exception as e:
        # Логуємо помилку
        log_error(e, f"Error sending message to {chat_id}: {text[:50]}...")
        raise

def edit_message_with_logging(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    """
    Редагує повідомлення користувачеві та логує його.
    
    Args:
        chat_id: ID чату користувача
        message_id: ID повідомлення для редагування
        text: Новий текст повідомлення
        reply_markup: Об'єкт клавіатури (опціонально)
        parse_mode: Режим парсингу (HTML, Markdown, None)
        
    Returns:
        telebot.types.Message: Об'єкт редагованого повідомлення
    """
    try:
        # Отримуємо інформацію про користувача
        user_info = None
        try:
            # Спроба отримати інформацію про користувача
            user = bot.get_chat_member(chat_id, chat_id).user
            user_info = {
                "user_id": user.id,
                "username": user.username if user.username else "No username",
                "first_name": user.first_name if user.first_name else "No first name",
                "last_name": user.last_name if user.last_name else "No last name"
            }
        except Exception:
            # Якщо не вдалося отримати інформацію, використовуємо мінімальні дані
            user_info = {
                "user_id": chat_id,
                "username": "Unknown",
                "first_name": "Unknown",
                "last_name": "Unknown"
            }
        
        # Редагуємо повідомлення
        edited_message = bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        
        # Логуємо відредаговане повідомлення
        log_response(
            user_info["user_id"],
            user_info["username"],
            user_info["first_name"],
            user_info["last_name"],
            f"[EDITED] {text}"
        )
        
        return edited_message
    
    except Exception as e:
        # Логуємо помилку
        log_error(e, f"Error editing message {message_id} for {chat_id}: {text[:50]}...")
        raise

def register_next_step_handler_with_logging(message, callback, *args, **kwargs):
    """
    Реєструє обробник для наступного кроку з логуванням.
    
    Args:
        message: Повідомлення, для якого реєструється обробник
        callback: Функція-callback для обробки наступного кроку
        *args, **kwargs: Аргументи для передачі в callback
    """
    def logged_callback(next_message, *callback_args, **callback_kwargs):
        # Логуємо вхідне повідомлення
        from utils.logger import log_message
        log_message(next_message)
        
        # Викликаємо оригінальний callback
        return callback(next_message, *callback_args, **callback_kwargs)
    
    # Реєструємо обробник з нашим логуючим wrapper
    bot.register_next_step_handler(message, logged_callback, *args, **kwargs)
