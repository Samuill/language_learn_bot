# -*- coding: utf-8 -*-

"""
Helper functions for multilingual grammatical explanations.
"""

import db_manager
from utils.language_utils import get_text

def get_case_name_in_ukrainian(case_name, chat_id):
    """
    Get localized name for German grammatical cases
    
    Args:
        case_name (str): German case name (Nominativ, Akkusativ, etc.)
        chat_id (int): User's chat ID for localization
        
    Returns:
        str: The case name in user's language
    """
    # Map case names to translation keys
    case_keys = {
        "Nominativ": "case_Nominativ",
        "Akkusativ": "case_Akkusativ", 
        "Dativ": "case_Dativ",
        "Genitiv": "case_Genitiv"
    }
    
    # Get the translation key for this case
    translation_key = case_keys.get(case_name, case_name.lower())
    
    # Default translations if localized versions not available
    defaults = {
        "Nominativ": "Називний",
        "Akkusativ": "Знахідний",
        "Dativ": "Давальний",
        "Genitiv": "Родовий"
    }
    
    return get_text(translation_key, chat_id, defaults.get(case_name, case_name))

def get_pronoun_translation(pronoun, chat_id):
    """
    Get translation of German pronouns in user's language
    
    Args:
        pronoun (str): German pronoun
        chat_id (int): User's chat ID for localization
        
    Returns:
        str: Translated pronoun
    """
    # Simple pronouns can be directly used as translation keys
    # uk.json already has these keys defined
    
    # For pronouns with special characters, we need to convert them
    pronoun_key = pronoun.replace(" ", "_").replace("(", "").replace(")", "")
    
    # Default translations as fallback
    defaults = {
        "ich": "я",
        "du": "ти",
        "er": "він",
        "es": "воно",
        "sie_singular": "вона",
        "wir": "ми",
        "ihr": "ви",
        "sie_plural": "вони",
        "Sie_formal": "Ви (ввічливе)"
    }
    
    # Get the default value from our mapping or use the original pronoun
    default = defaults.get(pronoun_key, pronoun)
    
    # Return localized text or fallback
    return get_text(pronoun_key, chat_id, default)

def get_case_explanation(case, chat_id, language=None):
    """
    Get explanation for grammatical cases in user's preferred language
    
    Args:
        case (str): German case name
        chat_id (int): User's chat ID
        language (str, optional): Language code. If None, get from user settings
        
    Returns:
        str: Localized explanation text 
    """
    # Get user language if not provided
    if language is None:
        language = db_manager.get_user_language(chat_id) or "uk"
    
    # Use the pattern from uk.json: nominativ_explanation_uk
    translation_key = f"{case.lower()}_explanation_{language}"
    
    # Ключі пояснень відмінків
    explanation_keys = {
        "Nominativ": "nominativ_explanation_uk",
        "Akkusativ": "akkusativ_explanation_uk",
        "Dativ": "dativ_explanation_uk",
        "Genitiv": "genitiv_explanation_uk"
    }
    
    # Спробуємо отримати локалізований текст
    key = explanation_keys.get(case)
    if key:
        return get_text(key, chat_id)
    
    # Словник запасних варіантів для різних мов
    defaults = {
        "uk": {
            "Nominativ": "Називний відмінок використовується для підмета речення і відповідає на питання 'хто/що?'",
            "Akkusativ": "Знахідний відмінок використовується для прямого додатка і відповідає на питання 'кого/що?'",
            "Dativ": "Давальний відмінок використовується для непрямого додатка і відповідає на питання 'кому/чому?'",
            "Genitiv": "Родовий відмінок використовується для вираження приналежності і відповідає на питання 'кого/чого?'"
        },
        "en": {
            "Nominativ": "The nominative case is used for the subject of a sentence",
            "Akkusativ": "The accusative case is used for the direct object",
            "Dativ": "The dative case is used for the indirect object",
            "Genitiv": "The genitive case is used for possession"
        }
    }
    
    # Використовуємо відповідні запасні варіанти або англійські, якщо переклад відсутній
    language_defaults = defaults.get(language, defaults.get("uk", defaults["en"]))
    return language_defaults.get(case, "")
