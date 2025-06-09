# -*- coding: utf-8 -*-

"""
Обробники для роботи зі спільними словниками.
"""

import telebot
from config import bot, user_state
from utils import main_menu_keyboard, main_menu_cancel, shared_dictionary_keyboard
from utils import clear_state
from utils.state_helpers import save_message_id
import db_manager
from utils.language_utils import get_text
from utils.input_handlers import safe_next_step_handler, sanitize_user_input
from utils.console_logger import log_menu_transition, log_displayed_buttons, MENU_MAIN, MENU_SHARED

# Updated handler to work with all localized button texts
@bot.message_handler(func=lambda message: message.text.startswith("👥 ") or 
                    message.text == get_text("shared_dictionary", message.chat.id))
def shared_dictionary_menu(message):
    """Show shared dictionary menu"""
    chat_id = message.chat.id
    
    # Логируем переход в меню общих словарей
    from_menu = user_state.get(chat_id, {}).get("current_menu", "UNKNOWN")
    log_menu_transition(chat_id, from_menu, MENU_SHARED, f"Button: {message.text}")
    
    # Ініціалізуємо таблиці для спільних словників, якщо вони не існують
    db_manager.create_shared_dictionary_tables()
    
    # Перевіряємо, чи є вже активний словник
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    
    # Оновлюємо тип словника у стані користувача
    if chat_id in user_state:
        user_state[chat_id].update({
            "dict_type": "shared", 
            "current_menu": MENU_SHARED
        })
    else:
        user_state[chat_id] = {
            "dict_type": "shared", 
            "current_menu": MENU_SHARED
        }
    
    # Показуємо інформацію про поточний словник, якщо є
    if result and result[0]:
        shared_dict_id = result[0]
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Отримуємо інформацію про словник
        cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
        dict_info = cursor.fetchone()
        dict_name = dict_info[0] if dict_info else get_text("unknown_dict", chat_id)
        
        # Повідомляємо про поточний активний словник
        menu_message = get_text("selected_dict", chat_id) + f"<b>{dict_name}</b>\n\n" + get_text("select_activity", chat_id)
        
        keyboard = shared_dictionary_keyboard(chat_id)
        
        # Логируем отображаемые кнопки
        button_texts = [button.text for row in keyboard.keyboard for button in row]
        log_displayed_buttons(chat_id, button_texts, MENU_SHARED)
        
        sent_message = bot.send_message(
            chat_id,
            menu_message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        # Просто показуємо меню спільних словників
        menu_message = get_text("select_option", chat_id)
        
        keyboard = shared_dictionary_keyboard(chat_id)
        
        # Логируем отображаемые кнопки
        button_texts = [button.text for row in keyboard.keyboard for button in row]
        log_displayed_buttons(chat_id, button_texts, MENU_SHARED)
        
        sent_message = bot.send_message(
            chat_id, 
            menu_message,
            parse_mode="HTML", 
            reply_markup=keyboard
        )
    
    save_message_id(chat_id, sent_message.message_id)
    conn.close()

@bot.message_handler(func=lambda message: message.text == "🆕 Створити спільний словник" or
                    message.text == get_text("create_shared_dict", message.chat.id))
def create_shared_dictionary(message):
    """Create a new shared dictionary"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Зберігаємо стан користувача
    user_state[chat_id] = {
        "step": "creating_shared_dict",
    }
    
    sent_message = bot.send_message(
        chat_id, 
        get_text("enter_dict_name", chat_id),
        reply_markup=main_menu_cancel()
    )
    save_message_id(chat_id, sent_message.message_id)
    
    # Використовуємо безпечний обробник для наступного кроку
    safe_next_step_handler(sent_message, handle_shared_dict_name)

def handle_shared_dict_name(message):
    """Handle shared dictionary name input"""
    chat_id = message.chat.id
    
    # Перевіряємо на команди
    if message.text in ["Відміна", "✖️ Відміна"]:
        clear_state(chat_id)
        bot.send_message(
            chat_id, 
            get_text("cancelled", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )
        return
    
    # Очищення і валідація вводу
    dict_name = sanitize_user_input(message.text.strip(), max_length=30)
    
    if len(dict_name) < 3 or len(dict_name) > 30:
        bot.send_message(chat_id, get_text("dict_name_length_error", chat_id))
        safe_next_step_handler(message, handle_shared_dict_name)
        return
    
    try:
        # Створюємо спільний словник
        code, shared_dict_id = db_manager.create_shared_dictionary(chat_id, dict_name)
        
        # Повідомляємо про успішне створення та показуємо код доступу
        bot.send_message(
            chat_id,
            get_text("dict_created_success", chat_id) + f"'{dict_name}'" + 
            get_text("created_success", chat_id) +  "\n\n" +
            get_text("access_code", chat_id).format(code=code) + f"<code>{code}</code>\n\n" +
            get_text("share_code", chat_id),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(chat_id)
        )
        
        clear_state(chat_id)
    except Exception as e:
        print(f"Error creating shared dictionary: {e}")
        bot.send_message(
            chat_id, 
            get_text("error_occurred", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "🔑 Вступити до спільного словника" or
                    message.text == get_text("join_shared_dict", message.chat.id))
def join_shared_dictionary(message):
    """Join an existing shared dictionary"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Зберігаємо стан користувача
    user_state[chat_id] = {
        "step": "joining_shared_dict",
    }
    
    sent_message = bot.send_message(
        chat_id, 
        get_text("enter_access_code", chat_id),
        reply_markup=main_menu_cancel()
    )
    save_message_id(chat_id, sent_message.message_id)
    
    # Використовуємо безпечний обробник для наступного кроку
    safe_next_step_handler(sent_message, handle_shared_dict_code)

def handle_shared_dict_code(message):
    """Handle shared dictionary code input"""
    chat_id = message.chat.id
    
    # Перевіряємо на команди
    if message.text in ["Відміна", "✖️ Відміна"]:
        clear_state(chat_id)
        bot.send_message(chat_id, get_text("cancelled", chat_id), reply_markup=main_menu_keyboard(chat_id))
        return
    
    # Очищення і валідація вводу
    code = sanitize_user_input(message.text.strip(), max_length=6).upper()
    
    if len(code) != 6:
        bot.send_message(chat_id, get_text("access_code_length_error", chat_id))
        safe_next_step_handler(message, handle_shared_dict_code)
        return
    
    try:
        # Приєднуємось до спільного словника
        success, result = db_manager.join_shared_dictionary(chat_id, code)
        
        if success:
            # Повідомляємо про успішне приєднання
            bot.send_message(
                chat_id,
                get_text("joined_shared_dict_success", chat_id).format(dict_name=result),
                reply_markup=main_menu_keyboard(chat_id)
            )
        else:
            # Повідомляємо про помилку
            bot.send_message(chat_id, f"❌ {result}")
        
        clear_state(chat_id)
    except Exception as e:
        print(f"Error joining shared dictionary: {e}")
        bot.send_message(
            chat_id, 
            get_text("error_occurred", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "📋 Мої спільні словники" or
                    message.text == get_text("your_dict", message.chat.id).split(":")[0].strip())
def my_shared_dictionaries(message):
    """Show user's shared dictionaries"""
    chat_id = message.chat.id
    
    # Отримуємо список спільних словників користувача
    shared_dicts = db_manager.get_user_shared_dictionaries(chat_id)
    
    if not shared_dicts:
        sent_message = bot.send_message(
            chat_id,
            get_text("no_shared_dicts", chat_id),
            reply_markup=shared_dictionary_keyboard()
        )
        save_message_id(chat_id, sent_message.message_id)
        return
    
    # Показуємо список словників
    response = get_text("your_dict",chat_id) + "\n\n"
    
    for dict_info in shared_dicts:
        admin_status = get_text("admin",chat_id) if dict_info['is_admin'] else get_text("user",chat_id)
        response += f"• <b>{dict_info['name']}</b> ({admin_status})\n"
        response += get_text("accsess_code",chat_id) +  f"<code>{dict_info['code']}</code>\n\n"
    
    response += get_text("select_dict_to_use", chat_id)
    
    # Створюємо інлайн клавіатуру для вибору словника
    markup = telebot.types.InlineKeyboardMarkup()
    
    for dict_info in shared_dicts:
        admin_icon = "👑" if dict_info['is_admin'] else "👤"
        button_text = f"{admin_icon} {dict_info['name']}"
        markup.add(telebot.types.InlineKeyboardButton(
            button_text, 
            callback_data=f"use_shared_dict_{dict_info['id']}"
        ))
    
    sent_message = bot.send_message(
        chat_id,
        response,
        parse_mode="HTML",
        reply_markup=markup
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("use_shared_dict_"))
def use_shared_dictionary(call):
    """Switch to a specific shared dictionary"""
    chat_id = call.message.chat.id
    shared_dict_id = int(call.data.replace("use_shared_dict_", ""))
    
    # Перевіряємо, чи користувач є творцем словника (першочергова перевірка)
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT created_by FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
    creator_result = cursor.fetchone()
    is_creator = creator_result and creator_result[0] == chat_id
    
    # Якщо користувач є творцем, він точно адміністратор
    if is_creator:
        is_admin = True
    else:
        # Якщо не творець, перевіряємо статус в shared_dict_users
        cursor.execute('''
        SELECT is_admin FROM shared_dict_users 
        WHERE user_id = ? AND dict_id = ?
        ''', (chat_id, shared_dict_id))
        admin_result = cursor.fetchone()
        is_admin = bool(admin_result and admin_result[0])
    
    # Оновлюємо записи в БД
    if is_admin:
        cursor.execute('UPDATE users SET shared_dict_id = ?, shared_dict_admin = 1 WHERE chat_id = ?', 
                     (shared_dict_id, chat_id))
        
        # Переконаємося, що є відповідний запис у shared_dict_users
        cursor.execute('''
        INSERT OR REPLACE INTO shared_dict_users (user_id, dict_id, is_admin, joined_at)
        VALUES (?, ?, 1, datetime('now'))
        ''', (chat_id, shared_dict_id))
    else:
        cursor.execute('UPDATE users SET shared_dict_id = ?, shared_dict_admin = 0 WHERE chat_id = ?', 
                     (shared_dict_id, chat_id))
        
        # Переконаємося, що є запис у shared_dict_users
        cursor.execute('''
        INSERT OR IGNORE INTO shared_dict_users (user_id, dict_id, is_admin, joined_at)
        VALUES (?, ?, 0, datetime('now'))
        ''', (chat_id, shared_dict_id))
    
    conn.commit()
    
    try:
        # Отримуємо назву словника для повідомлення
        cursor.execute('SELECT name FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
        dict_name = cursor.fetchone()[0]
        conn.close()
        
        # Оновлюємо стан в пам'яті
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        user_state[chat_id] = {
            "dict_type": "shared", 
            "shared_dict_id": shared_dict_id,
            "level": level,
            "is_admin": is_admin
        }
        
        # Показуємо повідомлення
        bot.answer_callback_query(call.id, get_text("selected_dict", chat_id) + f"{dict_name}")
        
        # Видаляємо попереднє повідомлення
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        
        admin_text = get_text("you_admin",chat_id) if is_admin else ""
        
        sent_message = bot.send_message(
            chat_id,
            get_text("selected_dict", chat_id) +
            f"<b>{dict_name}</b>{admin_text}\n"+
            get_text("moves_in_dict", chat_id),
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(chat_id)
        )
        save_message_id(chat_id, sent_message.message_id)
        
    except Exception as e:
        print(f"Error switching to shared dictionary: {e}")
        bot.send_message(
            chat_id, 
            get_text("error_occurred", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )
