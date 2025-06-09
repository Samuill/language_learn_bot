# -*- coding: utf-8 -*-

"""
Module for tracking user menu navigation and displaying current location.
"""

from config import user_state

# Constants for menu types
MENU_MAIN = "main"
MENU_EASY = "easy"
MENU_MEDIUM = "medium" 
MENU_HARD = "hard"
MENU_SHARED_DICT = "shared_dict"

# Menu breadcrumb icons
MENU_ICONS = {
    MENU_MAIN: "🏠",
    MENU_EASY: "🟢",
    MENU_MEDIUM: "🟠",
    MENU_HARD: "🔴",
    MENU_SHARED_DICT: "👥"
}

# Menu names per language
MENU_NAMES = {
    "uk": {
        MENU_MAIN: "Головне меню",
        MENU_EASY: "Легкий рівень",
        MENU_MEDIUM: "Середній рівень",
        MENU_HARD: "Складний рівень",
        MENU_SHARED_DICT: "Спільні словники"
    },
    "ru": {
        MENU_MAIN: "Главное меню",
        MENU_EASY: "Легкий уровень",
        MENU_MEDIUM: "Средний уровень", 
        MENU_HARD: "Сложный уровень",
        MENU_SHARED_DICT: "Общие словари"
    },
    "en": {
        MENU_MAIN: "Main menu",
        MENU_EASY: "Easy level",
        MENU_MEDIUM: "Medium level",
        MENU_HARD: "Hard level",
        MENU_SHARED_DICT: "Shared dictionaries"
    },
    "ar": {
        MENU_MAIN: "القائمة الرئيسية",
        MENU_EASY: "المستوى السهل",
        MENU_MEDIUM: "المستوى المتوسط",
        MENU_HARD: "المستوى الصعب",
        MENU_SHARED_DICT: "القواميس المشتركة"
    }
}

# Default to English if language not found
DEFAULT_LANGUAGE = "uk"

def set_current_menu(chat_id, menu_type):
    """
    Set the current menu for a user
    """
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    user_state[chat_id]["current_menu"] = menu_type
    
    # Also log the menu change
    try:
        from debug_logger import log_section_change
        log_section_change(chat_id, f"Menu changed to: {menu_type}")
    except ImportError:
        pass
    
    return True

def get_current_menu(chat_id):
    """
    Get the current menu for a user
    """
    return user_state.get(chat_id, {}).get("current_menu", MENU_MAIN)

def get_menu_header(chat_id):
    """
    Get a formatted header showing the current menu location
    """
    import db_manager
    
    # Get user language
    language = db_manager.get_user_language(chat_id) or DEFAULT_LANGUAGE
    
    # If language not in our translations, use default
    if language not in MENU_NAMES:
        language = DEFAULT_LANGUAGE
    
    # Get current menu
    current_menu = get_current_menu(chat_id)
    
    # Get menu name in user's language
    menu_name = MENU_NAMES[language].get(current_menu, MENU_NAMES[DEFAULT_LANGUAGE][current_menu])
    
    # Get menu icon
    icon = MENU_ICONS.get(current_menu, "📍")
    
    # Create the header
    return f"{icon} <b>{menu_name}</b>\n\n"
