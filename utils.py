# -*- coding: utf-8 -*-
import os
import json
import telebot
import pandas as pd
from datetime import datetime
from config import bot, user_state, ADMIN_ID

def clear_state(chat_id, preserve_dict_type=False):
    """Clear user state and delete message if exists
    
    Args:
        chat_id: User's chat ID
        preserve_dict_type: If True, preserve the dict_type setting for this user
    """
    if chat_id in user_state:
        # Зберігаємо тип словника, якщо потрібно 
        dict_type = None
        if preserve_dict_type and "dict_type" in user_state[chat_id]:
            dict_type = user_state[chat_id]["dict_type"]
            
        # Видаляємо повідомлення, якщо є
        if "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except:
                pass
        
        # Видаляємо запис користувача з user_state
        del user_state[chat_id]
        
        # Відновлюємо тип словника, якщо потрібно
        if preserve_dict_type and dict_type:
            user_state[chat_id] = {"dict_type": dict_type}
            print(f"Debug: Preserved dictionary type '{dict_type}' for user {chat_id}")

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
    
    # Add dictionary selector button
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    # Додаємо кнопку "Додати слово" тільки якщо це персональний словник 
    # або користувач адмін і використовує загальний словник
    if dict_type == "personal" or (chat_id == ADMIN_ID and dict_type == "common"):
        keyboard.add("➕ Додати нове слово")
    
    # Додаємо кнопки рівнів складності
    keyboard.add("🟢 Легкий рівень", "🟠 Середній рівень", "🔴 Складний рівень")
    
    # Додаємо кнопки перемикання словників залежно від активного словника
    if dict_type == "shared" and shared_dict_id:
        # Якщо обрано спільний словник, виводимо його назву
        import db_manager
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
        result = cursor.fetchone()
        conn.close()
        
        dict_name = result[0] if result else "Спільний"
        keyboard.add(f"👤 Персональний словник", f"👥 Спільний словник ({dict_name})")
    else:
        # В інших випадках просто показуємо основні кнопки
        keyboard.add("👤 Персональний словник", "👥 Спільний словник")
    
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
    keyboard.add("🏷️ Вивчати артиклі")  # Нова кнопка для вивчення артиклів
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
