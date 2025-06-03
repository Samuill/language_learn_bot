# -*- coding: utf-8 -*-
import os
import json
import telebot
import pandas as pd
from datetime import datetime
from config import bot, user_state, ADMIN_ID

def clear_state(chat_id, preserve_dict_type=False, preserve_messages=False, preserve_level=False):
    """Clear user state and delete message if exists
    
    Args:
        chat_id: User's chat ID
        preserve_dict_type: If True, preserve the dict_type setting for this user
        preserve_messages: If True, don't delete associated messages
        preserve_level: If True, preserve the level setting for this user
    """
    if chat_id in user_state:
        # Зберігаємо важливі дані перед очищенням
        preserved_data = {}
        
        # Тип словника
        if preserve_dict_type and "dict_type" in user_state[chat_id]:
            preserved_data["dict_type"] = user_state[chat_id]["dict_type"]
        
        # Рівень складності
        if preserve_level and "level" in user_state[chat_id]:
            preserved_data["level"] = user_state[chat_id]["level"]
        
        # Shared dict ID, якщо є
        if preserve_dict_type and "shared_dict_id" in user_state[chat_id]:
            preserved_data["shared_dict_id"] = user_state[chat_id]["shared_dict_id"]
            
        # ID повідомлення, якщо потрібно зберегти
        message_id = None
        if preserve_messages and "message_id" in user_state[chat_id]:
            message_id = user_state[chat_id]["message_id"]
            preserved_data["message_id"] = message_id
            
        # Видаляємо повідомлення, якщо є і не потрібно зберігати
        if not preserve_messages and "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except Exception as e:
                print(f"Error deleting message: {e}")
        
        # Видаляємо запис користувача з user_state
        del user_state[chat_id]
        
        # Відновлюємо збережені дані
        if preserved_data:
            user_state[chat_id] = preserved_data
            debug_info = ", ".join([f"{k}={v}" for k, v in preserved_data.items()])
            print(f"Debug: Preserved data for user {chat_id}: {debug_info}")

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
    
    print(f"Debug main_menu_keyboard: chat_id={chat_id}, dict_type={dict_type}, shared_dict_id={shared_dict_id}")
    
    # Додаємо кнопку "Додати слово" відповідно до типу словника і прав
    add_word_button = False
    
    if dict_type == "personal":
        # У персональному словнику всі можуть додавати слова
        add_word_button = True
    elif dict_type == "common" and chat_id == ADMIN_ID:
        # У загальному словнику тільки адмін може додавати слова
        add_word_button = True
    elif dict_type == "shared":
        # Перевіряємо, чи користувач є адміністратором цього спільного словника
        try:
            import db_manager
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Отримуємо ID спільного словника, якщо його немає у стані
            if not shared_dict_id:
                cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    shared_dict_id = result[0]
                    # Оновлюємо стан користувача, щоб зберегти ID
                    if chat_id in user_state:
                        user_state[chat_id]["shared_dict_id"] = shared_dict_id
            
            # Якщо є shared_dict_id, перевіряємо, чи користувач є адміном
            if shared_dict_id:
                # Перевірка чи користувач є творцем словника
                cursor.execute("""
                    SELECT 1 FROM shared_dictionaries 
                    WHERE id = ? AND created_by = ?
                """, (shared_dict_id, chat_id))
                is_creator = cursor.fetchone() is not None
                
                # Перевірка чи користувач є адміном словника
                cursor.execute("""
                    SELECT shared_dict_admin FROM users
                    WHERE chat_id = ? AND shared_dict_id = ?
                """, (chat_id, shared_dict_id))
                admin_result = cursor.fetchone()
                is_admin = admin_result and admin_result[0]
                
                # Якщо користувач адмін або творець, показуємо кнопку
                add_word_button = is_creator or is_admin or chat_id == ADMIN_ID
                
            conn.close()
        except Exception as e:
            print(f"Error checking shared dictionary admin status: {e}")
    
    # Додаємо кнопку додавання слова, якщо потрібно
    if add_word_button:
        keyboard.add("➕ Додати нове слово")
    
    # Додаємо кнопки рівнів складності
    keyboard.add("🟢 Легкий рівень", "🟠 Середній рівень", "🔴 Складний рівень")
    
    # Додаємо кнопки перемикання словників
    if dict_type == "shared":
        # Для спільного словника показуємо назву
        try:
            import db_manager
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Отримуємо ID словника, якщо його немає в стані
            if not shared_dict_id:
                cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    shared_dict_id = result[0]
            
            # Отримуємо назву словника
            if shared_dict_id:
                cursor.execute('SELECT name FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
                result = cursor.fetchone()
                dict_name = result[0] if result else "Невідомий"
                
                keyboard.add(
                    f"👤 Персональний словник", 
                    f"👥 Спільний словник ({dict_name})"
                )
            else:
                keyboard.add("👤 Персональний словник", "👥 Спільний словник")
            
            conn.close()
        except Exception as e:
            print(f"Error getting shared dictionary name: {e}")
            keyboard.add("👤 Персональний словник", "👥 Спільний словник")
    else:
        # Для персонального та загального словника
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
    keyboard.add("🏷️ Вивчати артиклі", "🧩 Вивчати присвійні займенники")  # Added possessive articles
    keyboard.add("↩️ Повернутися до головного меню")
    return keyboard

def hard_level_keyboard():
    """Create keyboard for hard level"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🧩 Складна гра", "📝 Введення слів")
    keyboard.add("🏷️ Введення артиклів")
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
