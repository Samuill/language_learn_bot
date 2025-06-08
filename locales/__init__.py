# -*- coding: utf-8 -*-

"""
Localization module for the bot.
This module handles loading translations from JSON files.
"""

import os
import json
import logging

# Directory containing the localization files
LOCALES_DIR = os.path.dirname(os.path.abspath(__file__))

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

def get_text(key, language_code):
    """
    Get translated text for the given key in the specified language.
    Falls back to English if translation is not available.
    """
    translations = load_language(language_code)
    
    if key in translations:
        return translations[key]
    
    # If translation not found in specified language, try English
    if language_code != DEFAULT_LANGUAGE:
        en_translations = load_language(DEFAULT_LANGUAGE)
        if key in en_translations:
            return en_translations[key]
    
    # If all else fails, return the key itself
    logging.warning(f"Translation for key '{key}' not found in any language")
    return key
