# -*- coding: utf-8 -*-
import os
import json
import telebot
import pandas as pd
from datetime import datetime
from config import bot, user_state, ADMIN_ID

def clear_state(chat_id, preserve_dict_type=False, preserve_messages=False, preserve_level=False):
    """
    Clear user state, optionally preserving some parts
    
    Args:
        chat_id (int): User's chat ID
        preserve_dict_type (bool): Whether to preserve dictionary type
        preserve_messages (bool): Whether to preserve message IDs
        preserve_level (bool): Whether to preserve difficulty level
    """
    try:
        if chat_id not in user_state:
            user_state[chat_id] = {} # Initialize if not exists
            return # Nothing to clear or preserve if it was just initialized
        
        # Store the parts we want to preserve
        current_user_state = user_state.get(chat_id, {})
        dict_type = current_user_state.get("dict_type", "personal") if preserve_dict_type else None
        shared_dict_id = current_user_state.get("shared_dict_id") if preserve_dict_type else None
        level = current_user_state.get("level", "easy") if preserve_level else None
        
        # Store message IDs if needed
        message_ids = None
        if preserve_messages and "message_ids" in current_user_state:
            message_ids = current_user_state.get("message_ids")
        
        # Clear the state
        user_state[chat_id] = {}
        
        # Restore preserved parts
        if preserve_dict_type:
            if dict_type:
                user_state[chat_id]["dict_type"] = dict_type
            if shared_dict_id:
                user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        if preserve_level and level:
            user_state[chat_id]["level"] = level
        
        if preserve_messages and message_ids:
            user_state[chat_id]["message_ids"] = message_ids
            
    except Exception as e:
        print(f"Error in clear_state for chat_id {chat_id}: {e}")
        # Initialize to a clean state in case of error
        user_state[chat_id] = {}


def get_user_params_path(chat_id):
    """Get path to user parameters file"""
    return f"params_{chat_id}.json"

def update_streak(chat_id):
    """Update user streak and return current streak count"""
    params_path = get_user_params_path(chat_id)
    
    try:
        with open(params_path, 'r') as f:
            params = json.load(f)
    except FileNotFoundError:
        params = {'streak': 0, 'last_active': None}
        
    today = datetime.now().date().isoformat()
    last_active = datetime.fromisoformat(params['last_active']).date() if params['last_active'] else None
    
    if last_active:
        delta = (datetime.now().date() - last_active).days
        if delta == 1:
            params['streak'] += 1
        elif delta > 1:
            params['streak'] = 1
    else:
        params['streak'] = 1
        
    params['last_active'] = today
    with open(params_path, 'w') as f:
        json.dump(params, f)
    return params['streak']

def track_activity(chat_id):
    """Track user activity and update streak"""
    params_path = get_user_params_path(chat_id)
    
    # Create file if not exists
    if not os.path.exists(params_path):
        update_streak(chat_id)
        
    return update_streak(chat_id)

def main_menu_keyboard(chat_id=None):
    """Create main menu keyboard with localized buttons"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # If chat_id is provided, use language-specific texts and customize for user
    if chat_id:
        from utils.language_utils import get_text
        
        # Always get dictionary type from database instead of relying on state
        dict_type = get_user_dict_type(chat_id)
        
        # Get language for this user
        import db_manager
        language = db_manager.get_user_language(chat_id) or "uk"
        
        # Dictionary type button based on actual state from database
        dict_button = get_text("shared_dictionary", chat_id) if dict_type == "shared" else get_text("personal_dictionary", chat_id)
        
        # First row - dictionary type and add word
        keyboard.row(dict_button, get_text("add_new_word", chat_id))
        
        # Second row - difficulty levels (get names from localization)
        keyboard.row(
            get_text("easy_level", chat_id),
            get_text("medium_level", chat_id),
            get_text("hard_level", chat_id)
        )
    else:
        # Fallback to Ukrainian if no chat_id provided
        # Dictionary type button
        keyboard.row("👤 Персональний словник", "➕ Додати нове слово")
        
        # Difficulty levels
        keyboard.row("🟢 Легкий рівень", "🟠 Середній рівень", "🔴 Складний рівень")
    
    return keyboard

def shared_dictionary_keyboard():
    """Create keyboard for shared dictionary options"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🆕 Створити спільний словник", "🔑 Вступити до спільного словника")
    keyboard.add("📋 Мої спільні словники")
    keyboard.add("↩️ Повернутися до головного меню")
    return keyboard

def easy_level_keyboard():
    """Create keyboard for easy level"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📖 Вчити нові слова", "🔄 Повторити")
    keyboard.add("🏷️ Вивчати артиклі", "🧩 Вивчати присвійні займенники")
    keyboard.add("↩️ Повернутися до головного меню")
    return keyboard

def medium_level_keyboard():
    """Create keyboard for medium level"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔤 Вибір правильного написання", "📝 Заповніть пропуски")
    keyboard.add("🏷️ Вивчати артиклі", "🧩 Вивчати присвійні займенники (середній)")
    keyboard.add("↩️ Повернутися до головного меню")
    return keyboard

def hard_level_keyboard():
    """Create keyboard for hard level"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🧩 Складна гра", "📝 Введення слів")
    keyboard.add("🏷️ Введення артиклів", "🧩 Вивчати присвійні займенники (складний)")
    keyboard.add("↩️ Повернутися до головного меню")
    return keyboard

def main_menu_cancel():
    """Create cancel menu keyboard"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("✖️ Відміна")  # Додаємо хрестик для візуального виділення
    return keyboard

def language_selection_keyboard():
    """Create language selection keyboard"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🇺🇦 Українська", "🇷🇺 Російська")
    return keyboard

def get_user_dict_type(chat_id):
    """Get user's dictionary type from the database (with fallback to state)"""
    import db_manager
    from config import user_state
    
    # First try to get from database
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user has a shared dictionary set
        cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            dict_type = "shared"
        else:
            # Default to personal if no shared dict is set
            dict_type = "personal"
        
        # Update the in-memory state to match database
        if chat_id in user_state:
            user_state[chat_id]["dict_type"] = dict_type
            if dict_type == "shared" and result and result[0]:
                user_state[chat_id]["shared_dict_id"] = result[0]
            elif dict_type == "personal" and "shared_dict_id" in user_state[chat_id]:
                del user_state[chat_id]["shared_dict_id"]
        else:
            # Initialize state if it doesn't exist
            user_state[chat_id] = {"dict_type": dict_type}
            if dict_type == "shared" and result and result[0]:
                user_state[chat_id]["shared_dict_id"] = result[0]
        
        return dict_type
    except Exception as e:
        print(f"Error getting dictionary type from database: {e}")
        # Fallback to in-memory state
        return user_state.get(chat_id, {}).get("dict_type", "personal")
    finally:
        conn.close()

def get_user_shared_dict_id(chat_id):
    """Get user's shared dictionary ID from the database"""
    import db_manager
    from config import user_state
    
    # First try to get from database
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        
        shared_dict_id = result[0] if result and result[0] else None
        
        # Update the in-memory state
        if shared_dict_id and chat_id in user_state:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
            user_state[chat_id]["dict_type"] = "shared"
        
        return shared_dict_id
    except Exception as e:
        print(f"Error getting shared dictionary ID from database: {e}")
        # Fallback to in-memory state
        return user_state.get(chat_id, {}).get("shared_dict_id")
    finally:
        conn.close()
