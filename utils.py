# -*- coding: utf-8 -*-
import os
import json
import telebot
import pandas as pd
from datetime import datetime
from config import bot, user_state, ADMIN_ID

def clear_state(chat_id):
    """Clear user state"""
    if chat_id in user_state:
        if "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except:
                pass
        # Preserve dictionary type when clearing state
        dict_type = user_state[chat_id].get("dict_type", "personal")
        user_state[chat_id] = {"dict_type": dict_type}

def get_user_params_path(chat_id):
    """Get path to user parameters file"""
    return f"params_{chat_id}.json"

def update_streak(chat_id):
    """Update user's streak"""
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
    """Get main menu keyboard with dictionary toggle button"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити")
    
    # Add dictionary toggle button if chat_id provided
    if chat_id is not None:
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        toggle_text = "🌐 Загальний словник" if dict_type == "personal" else "👤 Персональний словник"
        keyboard.add(toggle_text)
        
    return keyboard

def main_menu_cancel():
    """Get cancel keyboard"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Відміна")
    return keyboard

def language_selection_keyboard():
    """Get language selection keyboard"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🇺🇦 Українська", "🇷🇺 Російська")
    return keyboard

def is_admin(user_id):
    """Check if user is an admin"""
    return user_id == ADMIN_ID
