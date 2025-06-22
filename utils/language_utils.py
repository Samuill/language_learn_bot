# -*- coding: utf-8 -*-

"""
Утиліти для роботи з локалізацією та мовами.
"""

import json
import os
import db_manager
from config import user_state
import telebot

# Шлях до каталогу локалізацій
LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")

# Кеш локалізацій для оптимізації
_localization_cache = {}

# Add a language cache to reduce database calls
_language_cache = {}

# Define language flags and codes for easier identification
LANGUAGE_FLAGS = {
    "🇬🇧": "en",
    "🇺🇦": "uk",
    "🇷🇺": "ru",
    "🇹🇷": "tr",
    "🇸🇾": "ar"
}

# Language names in their native form
LANGUAGE_NAMES = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
    "tr": "Türkçe",
    "ar": "العربية"
}

def create_language_keyboard():
    """Create a keyboard with language selection buttons
    
    Returns:
        ReplyKeyboardMarkup: Keyboard with language selection buttons
    """
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Add language buttons in rows of 2
    row = []
    for flag, code in LANGUAGE_FLAGS.items():
        name = LANGUAGE_NAMES.get(code, code.upper())
        button_text = f"{flag} {name}"
        row.append(button_text)
        
        if len(row) == 2:
            keyboard.row(*row)
            row = []
    
    # Add any remaining buttons
    if row:
        keyboard.row(*row)
    
    return keyboard

def load_localization(lang_code="uk"):
    """Load localization file for a given language
    
    Args:
        lang_code (str): Language code
        
    Returns:
        dict: Localization strings
    """
    # Перевіряємо кеш
    if lang_code in _localization_cache:
        return _localization_cache[lang_code]
    
    # Завантажуємо локалізацію з файлу
    try:
        file_path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
        
        if not os.path.exists(file_path):
            # Якщо файл не існує, використовуємо англійську як запасну
            if lang_code != "en":
                print(f"Warning: Localization file for {lang_code} not found, using English")
                return load_localization("en")
            # Якщо і англійська не існує, використовуємо українську
            return load_localization("uk")
        
        with open(file_path, "r", encoding="utf-8") as file:
            localization = json.load(file)
            # Зберігаємо в кеші
            _localization_cache[lang_code] = localization
            return localization
    except Exception as e:
        print(f"Error loading localization for {lang_code}: {e}")
        # Повертаємо порожній словник у разі помилки
        return {}

def clear_localization_cache():
    """Clear the localization cache"""
    global _localization_cache
    _localization_cache = {}

def get_user_language(chat_id):
    """Get user's language from database with caching"""
    # Check cache first
    if chat_id in _language_cache:
        return _language_cache[chat_id]
        
    # Otherwise query database
    print(f"[LANG] [User {chat_id}] GET_LANG: Retrieving language from database")
    import db_manager  # Import here to avoid circular imports
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT language FROM users WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        language = result[0]
        print(f"[LANG] [User {chat_id}] GET_LANG_RESULT: Found language: {language}")
        # Store in cache
        _language_cache[chat_id] = language
        return language
    
    # Default to Ukrainian
    print(f"[LANG] [User {chat_id}] GET_LANG_RESULT: No language found, defaulting to 'uk'")
    return "uk"

def clear_language_cache(chat_id=None):
    """Clear language cache for a specific user or all users"""
    global _language_cache
    if chat_id is not None:
        if chat_id in _language_cache:
            del _language_cache[chat_id]
            print(f"[LANG] [User {chat_id}] Language cache cleared")
    else:
        _language_cache = {}
        print("[LANG] All language cache cleared")

# Add this as an alias to maintain compatibility 
def get_localized_text(key, chat_id, default=""):
    """Alias for get_text for backward compatibility"""
    return get_text(key, chat_id, default)

def set_user_language(chat_id, language):
    """Set user's language in database and update cache"""
    # Clear cache for this user to force a refresh
    clear_language_cache(chat_id)
    
    # Update cache
    _language_cache[chat_id] = language
    
    try:
        # Update language in database
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (chat_id, language)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET language = ?
        ''', (chat_id, language, language))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error setting user language: {e}")

def get_text(key, chat_id=None, default=None, **kwargs):
    """Get localized text by key and format it with provided arguments
    
    Args:
        key (str): Localization key
        chat_id: User's chat ID to determine language
        default (str, optional): Default value if key not found
        **kwargs: Format arguments
        
    Returns:
        str: Localized and formatted text
    """
    if chat_id is None:
        language = "uk"  # Default language
    else:
        language = get_user_language(chat_id)
    
    localization = load_localization(language)
      # Пошук ключа в локалізації
    if key in localization:
        text = localization[key]
    else:
        # Якщо ключ не знайдено, спробуємо знайти в англійській локалізації
        if language != "en":
            en_localization = load_localization("en")
            if key in en_localization:
                text = en_localization[key]
            else:
                # Якщо і в англійській немає, повертаємо значення за замовчуванням або ключ
                text = default if default is not None else key
        else:
            text = default if default is not None else key
    
    # Форматування тексту з переданими аргументами
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            print(f"Error formatting text for key '{key}': Missing key {e}")
        except Exception as e:
            print(f"Error formatting text for key '{key}': {e}")
    
    return text

def is_command(message, specific_command=None):
    """Check if message is a command or matches a specific command
    
    Args:
        message: Telegram message
        specific_command (str, optional): Check for a specific command
        
    Returns:
        bool: True if message is a command or matches specific command
    """
    from utils.input_handlers import is_system_command
    
    if not hasattr(message, 'text') or not message.text:
        return False
    
    # Якщо вказано конкретну команду, перевіряємо тільки її
    if specific_command:
        chat_id = message.chat.id
        return message.text in [specific_command, get_text(specific_command, chat_id)]
    
    # Інакше перевіряємо чи це системна команда
    return is_system_command(message)
