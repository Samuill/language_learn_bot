# -*- coding: utf-8 -*-

"""
Функции для создания клавиатур.
"""

import telebot
from config import user_state, ADMIN_ID

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
