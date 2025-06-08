# -*- coding: utf-8 -*-

"""
Utilities for language handling.
"""

from locales import get_text, SUPPORTED_LANGUAGES
import db_manager
from utils.logging_utils import log_language
import os
import json
import logging

# Directory containing the localization files
LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'locales')

# Supported languages with their native names
SUPPORTED_LANGUAGES = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
    "tr": "Türkçe",
    "ar": "العربية"
}

# Default language to use as fallback
DEFAULT_LANGUAGE = "en"

# Cache for loaded translations
_translations = {}

def load_language(language_code):
    """
    Load translations for the specified language.
    Falls back to English if the language is not supported.
    """
    # Return from cache if already loaded
    if language_code in _translations:
        return _translations[language_code]
    
    # Load the language file
    language_file = os.path.join(LOCALES_DIR, f"{language_code}.json")
    
    try:
        if os.path.exists(language_file):
            with open(language_file, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            _translations[language_code] = translations
            return translations
        else:
            # If language file doesn't exist, fall back to English
            if language_code != DEFAULT_LANGUAGE:
                logging.warning(f"Language file {language_file} not found, falling back to {DEFAULT_LANGUAGE}")
                return load_language(DEFAULT_LANGUAGE)
            else:
                logging.error(f"Default language file {language_file} not found!")
                return {}
    except Exception as e:
        logging.error(f"Error loading language file {language_file}: {e}")
        if language_code != DEFAULT_LANGUAGE:
            return load_language(DEFAULT_LANGUAGE)
        return {}

def get_user_language(chat_id):
    """Get language code for user from database"""
    import db_manager
    lang = db_manager.get_user_language(chat_id)
    
    # If no language is set, default to English
    if not lang or lang not in SUPPORTED_LANGUAGES:
        return DEFAULT_LANGUAGE
        
    return lang

def get_text(key, chat_id):
    """
    Get translated text for the given key for a specific user.
    
    Args:
        key: Translation key
        chat_id: User's chat ID to determine language
        
    Returns:
        str: Translated text or key itself if not found
    """
    # Get user's language code
    language_code = get_user_language(chat_id)
    
    # Load translations for this language
    translations = load_language(language_code)
    
    # Return the translation if it exists
    if key in translations:
        return translations[key]
    
    # Try English as fallback
    if language_code != DEFAULT_LANGUAGE:
        en_translations = load_language(DEFAULT_LANGUAGE)
        if key in en_translations:
            return en_translations[key]
    
    # If all else fails, return the key itself
    logging.warning(f"Translation for key '{key}' not found in language {language_code}")
    return key

def get_localized_text(key, chat_id):
    """
    Get localized text for the given key and user.
    
    Args:
        key: The translation key
        chat_id: The user's chat ID
    
    Returns:
        str: Translated text for the user's language
    """
    # Get user's language from database
    language = db_manager.get_user_language(chat_id) or "en"
    
    # Get translated text
    return get_text(key, language)

def create_language_keyboard():
    """Create a keyboard with language selection buttons"""
    import telebot
    
    log_language("KEYBOARD", "SYSTEM", "Creating language selection keyboard")
    
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Language flags and their names
    language_buttons = [
        ("🇬🇧", "English"),
        ("🇺🇦", "Українська"),
        ("🇷🇺", "Русский"),
        ("🇹🇷", "Türkçe"),
        ("🇸🇾", "العربية")
    ]
    
    # Log the buttons we're adding
    log_language("KEYBOARD_BUTTONS", "SYSTEM", f"Adding buttons: {language_buttons}")
    
    # Add buttons in rows of 2
    row = []
    for flag, name in language_buttons:
        button_text = f"{flag} {name}"
        row.append(button_text)
        
        if len(row) == 2:
            keyboard.row(*row)
            log_language("KEYBOARD_ROW", "SYSTEM", f"Added row: {row}")
            row = []
    
    # Add any remaining buttons
    if row:
        keyboard.row(*row)
        log_language("KEYBOARD_ROW", "SYSTEM", f"Added final row: {row}")
    
    return keyboard

def get_language_flag(code):
    """Get flag emoji for language"""
    flags = {
        "en": "🇬🇧",
        "uk": "🇺🇦",
        "ru": "🇷🇺",
        "tr": "🇹🇷",
        "ar": "🇸🇾"
    }
    return flags.get(code, "🌐")

def get_language_code_from_button(button_text):
    """
    Extract language code from button text.
    Example: "🇺🇦 Українська" -> "uk"
    
    Args:
        button_text: The text of the pressed button
        
    Returns:
        str: Language code or None if not found
    """
    # Debug print
    print(f"Extracting language code from: '{button_text}'")
    
    # Map of flag emojis to language codes
    flag_to_code = {
        "🇬🇧": "en",
        "🇺🇦": "uk",
        "🇷🇺": "ru",
        "🇹🇷": "tr",
        "🇸🇾": "ar"
    }
    
    # First try to extract directly from emoji
    for flag, code in flag_to_code.items():
        if button_text.startswith(flag):
            print(f"Found language code {code} from flag {flag}")
            return code
    
    # If that fails, try matching the language name
    from locales import SUPPORTED_LANGUAGES
    for code, name in SUPPORTED_LANGUAGES.items():
        if name in button_text:
            print(f"Found language code {code} from name {name}")
            return code
    
    print(f"No language code found for '{button_text}'")
    return None

def is_command(message, command_key):
    """
    Check if message text matches the localized command text.
    
    Args:
        message: Telegram message object
        command_key: The key for the command in the localization files
        
    Returns:
        bool: True if the message text matches the localized command
    """
    if not hasattr(message, 'text') or not message.text:
        return False
        
    chat_id = message.chat.id
    localized_text = get_text(command_key, chat_id)
    
    return message.text == localized_text
