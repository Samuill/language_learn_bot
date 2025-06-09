# -*- coding: utf-8 -*-

"""
Уніфікована система логування для бота.
Всі події логуються в одному форматі та в один файл.
"""

import os
import json
import traceback
from datetime import datetime
from config import ADMIN_ID

# Створення директорії для логів, якщо вона не існує
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Шлях до єдиного файлу логу
LOG_FILE = os.path.join(LOGS_DIR, "bot_log.log")

# Рівні логування
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_DEBUG = "DEBUG"

def _get_timestamp():
    """Повертає відформатований timestamp для логування"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def _format_log_entry(level, message, additional_data=None):
    """Форматує запис логу в єдиний формат"""
    timestamp = _get_timestamp()
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Додаємо деталі, якщо вони є
    if additional_data:
        if isinstance(additional_data, dict):
            # Форматуємо словник в JSON
            try:
                log_entry += f" | {json.dumps(additional_data, ensure_ascii=False)}"
            except Exception:
                log_entry += f" | {str(additional_data)}"
        else:
            log_entry += f" | {str(additional_data)}"
    
    return log_entry

def extract_user_info(message):
    """Витягує інформацію про користувача з повідомлення"""
    if not message or not hasattr(message, 'from_user'):
        return {"user_id": "Unknown", "username": "Unknown", "first_name": "Unknown", "last_name": "Unknown"}
    
    user = message.from_user
    return {
        "user_id": user.id,
        "username": user.username if user.username else "No username",
        "first_name": user.first_name if user.first_name else "No first name",
        "last_name": user.last_name if user.last_name else "No last name",
        "is_admin": (user.id == ADMIN_ID),
        "chat_id": message.chat.id if hasattr(message, 'chat') else None,
        "chat_type": message.chat.type if hasattr(message, 'chat') else None
    }

# Для зворотної сумісності
_extract_user_info = extract_user_info

def _write_to_log(entry):
    """Записує запис логу у файл та виводить в консоль"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(entry + "\n")
        
        # Вивід в консоль для негайного зворотного зв'язку
        print(entry)
    except Exception as e:
        # Якщо не вдалося записати в файл, виводимо тільки в консоль
        print(f"ERROR writing to log file: {e}")
        print(entry)

def log_message(message, level=LOG_LEVEL_INFO):
    """Логує вхідне повідомлення з інформацією про користувача та часовою міткою"""
    if not message:
        return
    
    user_info = extract_user_info(message)
    
    # Отримуємо вміст повідомлення
    content = message.text if hasattr(message, 'text') and message.text else "No text"
    
    # Визначаємо, чи це команда
    is_command = content.startswith('/') if isinstance(content, str) else False
    
    # Формуємо запис логу
    log_data = {
        "message_type": "command" if is_command else "text",
        "content": content,
        "user": user_info
    }
    
    # Додаємо messageId, якщо він є
    if hasattr(message, 'message_id'):
        log_data["message_id"] = message.message_id
    
    # Створюємо текстове представлення для логу
    user_str = f"{user_info['first_name']} {user_info['last_name']}".strip()
    if user_info['username']:
        user_str += f" (@{user_info['username']})"
    user_str += f" [ID: {user_info['user_id']}]"
    
    admin_mark = " [ADMIN]" if user_info["is_admin"] else ""
    log_text = f"Received message from {user_str}{admin_mark}: '{content}'"
    
    # Записуємо в лог
    log_entry = _format_log_entry(
        LOG_LEVEL_INFO if not is_command else "COMMAND", 
        log_text, 
        log_data
    )
    _write_to_log(log_entry)
    
    return log_data

def log_callback(callback, level=LOG_LEVEL_INFO):
    """Логує callback запити з інлайн кнопок"""
    if not callback:
        return
    
    user_info = extract_user_info(callback)
    
    # Отримуємо дані callback
    callback_data = callback.data if hasattr(callback, 'data') else "No callback data"
    
    # Формуємо запис логу
    log_data = {
        "message_type": "callback",
        "content": callback_data,
        "user": user_info
    }
    
    # Додаємо messageId, якщо він є
    if hasattr(callback, 'message') and hasattr(callback.message, 'message_id'):
        log_data["message_id"] = callback.message.message_id
    
    # Створюємо текстове представлення для логу
    user_str = f"{user_info['first_name']} {user_info['last_name']}".strip()
    if user_info['username']:
        user_str += f" (@{user_info['username']})"
    user_str += f" [ID: {user_info['user_id']}]"
    
    admin_mark = " [ADMIN]" if user_info["is_admin"] else ""
    log_text = f"Received callback from {user_str}{admin_mark}: '{callback_data}'"
    
    # Записуємо в лог
    log_entry = _format_log_entry(level, log_text, log_data)
    _write_to_log(log_entry)
    
    return log_data

def log_response(user_id, username, first_name, last_name, response_text, level=LOG_LEVEL_INFO):
    """Логує відповідь бота з часовою міткою"""
    # Формуємо запис логу
    user_str = f"{first_name} {last_name}".strip()
    if username:
        user_str += f" (@{username})"
    user_str += f" [ID: {user_id}]"
    
    admin_mark = " [ADMIN]" if user_id == ADMIN_ID else ""
    
    # Обмежуємо довжину відповіді в лозі для кращої читабельності
    short_response = response_text[:100] + ('...' if len(response_text) > 100 else '')
    
    log_data = {
        "message_type": "bot_response",
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "is_admin": (user_id == ADMIN_ID),
        "content": response_text
    }
    
    log_text = f"Bot response to {user_str}{admin_mark}: '{short_response}'"
    
    # Записуємо в лог
    log_entry = _format_log_entry(level, log_text, log_data)
    _write_to_log(log_entry)
    
    return log_data

def log_error(error, context=None, user=None, level=LOG_LEVEL_ERROR):
    """Логує помилки з часовою міткою та контекстом"""
    # Форматуємо помилку та отримуємо трасування
    error_text = str(error)
    error_trace = traceback.format_exc()
    
    # Формуємо логічний запис
    log_data = {
        "error": error_text,
        "traceback": error_trace,
        "context": context
    }
    
    if user:
        log_data["user"] = user
        user_str = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        if user.get('username'):
            user_str += f" (@{user['username']})"
        user_str += f" [ID: {user.get('user_id', 'Unknown')}]"
        admin_mark = " [ADMIN]" if user.get('is_admin') else ""
        error_context = f" for {user_str}{admin_mark}"
    else:
        error_context = ""
    
    log_text = f"ERROR{error_context}: {error_text}"
    
    if context:
        log_text += f" | Context: {context}"
    
    # Записуємо в лог
    log_entry = _format_log_entry(level, log_text, log_data)
    _write_to_log(log_entry)
    
    return log_data

def log_action(action, data=None, user=None, level=LOG_LEVEL_INFO):
    """Логує будь-яку дію в системі з часовою міткою"""
    # Формуємо запис логу
    log_data = {"action": action}
    
    if data:
        log_data["data"] = data
    
    if user:
        log_data["user"] = user
        user_str = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        if user.get('username'):
            user_str += f" (@{user['username']})"
        user_str += f" [ID: {user.get('user_id', 'Unknown')}]"
        admin_mark = " [ADMIN]" if user.get('is_admin', False) else ""
        action_user = f" by {user_str}{admin_mark}"
    else:
        action_user = ""
    
    log_text = f"Action '{action}'{action_user}"
    
    if isinstance(data, dict):
        # Вибірково додаємо важливі поля з даних до текстового логу
        important_keys = ['dict_type', 'shared_dict_id', 'word', 'translation', 'level']
        for key in important_keys:
            if key in data:
                log_text += f" | {key}: {data[key]}"
    elif data:
        log_text += f" | {data}"
    
    # Записуємо в лог
    log_entry = _format_log_entry(level, log_text, log_data)
    _write_to_log(log_entry)
    
    return log_data

# Створюємо декоратор для логування обробників
def log_handler(func):
    """Декоратор для логування вхідних повідомлень та відповідей для обробників"""
    def wrapper(message, *args, **kwargs):
        # Логуємо вхідне повідомлення
        log_data = log_message(message)
        
        # Викликаємо оригінальний обробник
        result = func(message, *args, **kwargs)
        
        # Повертаємо результат (якщо є)
        return result
        
    return wrapper
