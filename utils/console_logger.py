# -*- coding: utf-8 -*-

"""
Module for menu tracking and console logging without emojis.
"""

from datetime import datetime

# Menu type constants
MENU_MAIN = "MAIN_MENU"
MENU_EASY = "EASY_LEVEL"
MENU_MEDIUM = "MEDIUM_LEVEL"
MENU_HARD = "HARD_LEVEL"
MENU_SHARED = "SHARED_DICT"

# User state tracking
_current_menu = {}

def log_menu_transition(chat_id, from_menu, to_menu, reason=None):
    """Log a menu transition in the console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update stored menu
    _current_menu[chat_id] = to_menu
    
    # Clean menu names for display
    menu_names = {
        MENU_MAIN: "Main menu",
        MENU_EASY: "Easy level",
        MENU_MEDIUM: "Medium level",
        MENU_HARD: "Hard level", 
        MENU_SHARED: "Shared dictionaries"
    }
    
    from_name = menu_names.get(from_menu, from_menu)
    to_name = menu_names.get(to_menu, to_menu)
    
    # Log transition
    if reason:
        print(f"[{timestamp}] [MENU] User {chat_id}: {from_name} -> {to_name} ({reason})")
    else:
        print(f"[{timestamp}] [MENU] User {chat_id}: {from_name} -> {to_name}")

def log_displayed_buttons(chat_id, buttons, menu_type=None):
    """Log buttons being displayed without emojis"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Use stored menu type if none provided
    if menu_type is None:
        menu_type = _current_menu.get(chat_id, "UNKNOWN")
    
    # Clean menu names for display
    menu_names = {
        MENU_MAIN: "Main menu",
        MENU_EASY: "Easy level",
        MENU_MEDIUM: "Medium level",
        MENU_HARD: "Hard level",
        MENU_SHARED: "Shared dictionaries",
    }
    
    menu_name = menu_names.get(menu_type, menu_type)
    
    # Clean button names (remove emojis)
    clean_buttons = []
    for button in buttons:
        # Strip common emoji prefixes
        clean_name = button
        for prefix in ['🏠', '🟢', '🟠', '🔴', '👥', '📖', '🔄', '🏷️', '🧩', '➕', '✏️', '🔤', '📝', '🆕', '🔑', '📋', '↩️', '✖️']:
            clean_name = clean_name.replace(prefix, '').strip()
        clean_buttons.append(clean_name)
    
    # Log to console
    print(f"[{timestamp}] [BUTTONS] {menu_name}: {', '.join(clean_buttons)}")
