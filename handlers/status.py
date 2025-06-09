# -*- coding: utf-8 -*-

"""
Command handler for status information and debugging.
"""

from config import bot, user_state
import db_manager
from utils.navigation_tracker import get_current_menu, MENU_NAMES, MENU_ICONS
from utils.console_logger import MENU_MAIN, MENU_EASY, MENU_MEDIUM, MENU_HARD, MENU_SHARED

@bot.message_handler(commands=['status', 'debug'])
def show_status(message):
    """Show current status information for debugging"""
    chat_id = message.chat.id
    
    # Get current state information
    current_state = user_state.get(chat_id, {})
    
    # Clean up state for display (remove large objects)
    display_state = {}
    for key, value in current_state.items():
        if key == "messages" and isinstance(value, list):
            display_state[key] = f"[{len(value)} messages]"
        elif isinstance(value, (str, int, bool, float)) or value is None:
            display_state[key] = value
        else:
            display_state[key] = f"<{type(value).__name__}>"
    
    # Build status message
    status_message = f"📊 Status for user {chat_id}:\n\n"
    for key, value in display_state.items():
        status_message += f"• {key}: {value}\n"
    
    # Send status information
    bot.reply_to(message, status_message)

@bot.message_handler(commands=['menu_debug'])
def debug_menu_status(message):
    """Show current menu status for debugging"""
    chat_id = message.chat.id
    
    # Get state information
    menu = user_state.get(chat_id, {}).get("current_menu", "Unknown")
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    menu_status = f"Current menu: {menu}\nDictionary: {dict_type}\nDifficulty: {level}"
    
    # Send menu status
    bot.reply_to(message, menu_status)
