# -*- coding: utf-8 -*-

"""
Module for menu tracking and console logging without emojis.
"""

from datetime import datetime

# Menu type constants
MENU_MAIN = "main"
MENU_EASY = "easy"
MENU_MEDIUM = "medium"
MENU_HARD = "hard" 
MENU_SHARED = "shared"

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
    
    # Safety check for buttons
    if not buttons:
        buttons = ["No buttons"]
    
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
        if not isinstance(button, str):
            # Skip non-string buttons
            continue
            
        # Strip common emoji prefixes
        clean_name = button
        for prefix in ['🏠', '🟢', '🟠', '🔴', '👥', '📖', '🔄', '🏷️', '🧩', '➕', '✏️', '🔤', '📝', '🆕', '🔑', '📋', '↩️', '✖️']:
            if isinstance(clean_name, str):
                clean_name = clean_name.replace(prefix, '').strip()
        clean_buttons.append(clean_name)
    
    if not clean_buttons:
        clean_buttons = ["No valid buttons"]
    
    # Log to console
    print(f"[{timestamp}] [BUTTONS] {menu_name}: {', '.join(clean_buttons)}")

def set_current_menu(chat_id, menu_type):
    """
    Set the current menu for a user
    """
    _current_menu[chat_id] = menu_type
    
    # Also log the menu change
    log_menu_transition(chat_id, "UNKNOWN", menu_type, "Menu changed")
    
    return True

def get_current_menu(chat_id):
    """
    Get the current menu for a user
    """
    return _current_menu.get(chat_id, MENU_MAIN)
