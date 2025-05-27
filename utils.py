# -*- coding: utf-8 -*-
import os
import json
import telebot
import pandas as pd
from datetime import datetime
from config import bot, user_state

def clear_state(chat_id):
    """Clear user state and delete message if exists"""
    if chat_id in user_state:
        if "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except:
                pass
        del user_state[chat_id]

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
    """Create main menu keyboard with dictionary selection"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Визначаємо, який словник активний
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Додаємо кнопку "Додати слово" тільки якщо це персональний словник 
    # або користувач адмін і використовує загальний словник
    from config import ADMIN_ID
    if dict_type == "personal" or chat_id == ADMIN_ID:
        keyboard.add("➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити")
    else:
        # Для звичайних користувачів у режимі загального словника не показуємо кнопку додавання
        keyboard.add("📖 Вчити нові слова", "🔄 Повторити")
    
    # Додаємо кнопки перемикання словників
    keyboard.add("👤 Персональний словник", "🌐 Загальний словник")
    
    return keyboard

def main_menu_cancel():
    """Create cancel menu keyboard"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Відміна")
    return keyboard

def language_selection_keyboard():
    """Create language selection keyboard"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🇺🇦 Українська", "🇷🇺 Російська")
    return keyboard
