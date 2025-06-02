# -*- coding: utf-8 -*-

"""
Обробники для роботи зі спільними словниками.
"""

import telebot
from config import bot, user_state
from utils import main_menu_keyboard, main_menu_cancel, shared_dictionary_keyboard
from utils import clear_state
import db_manager

@bot.message_handler(func=lambda message: message.text.startswith("👥 Спільний словник"))
def shared_dictionary_menu(message):
    """Show shared dictionary menu"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є вже активний словник
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        # Якщо вже є вибраний словник, переходимо до нього
        shared_dict_id = result[0]
        
        # Оновлюємо стан користувача
        if chat_id in user_state:
            user_state[chat_id].update({"dict_type": "shared", "shared_dict_id": shared_dict_id})
        else:
            user_state[chat_id] = {"dict_type": "shared", "shared_dict_id": shared_dict_id}
        
        # Отримуємо інформацію про словник
        cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
        dict_info = cursor.fetchone()
        dict_name = dict_info[0] if dict_info else "Невідомий словник"
        
        # Повідомляємо про активний словник
        bot.send_message(
            chat_id,
            f"📚 Обрано спільний словник: <b>{dict_name}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(chat_id)
        )
    else:
        # Ініціалізуємо таблиці для спільних словників, якщо вони не існують
        db_manager.create_shared_dictionary_tables()
        
        # Показуємо меню спільних словників
        bot.send_message(chat_id, "👥 Спільні словники - оберіть опцію:",
                        reply_markup=shared_dictionary_keyboard())
        
        # Оновлюємо тип словника у стані користувача
        if chat_id in user_state:
            user_state[chat_id].update({"dict_type": "shared"})
        else:
            user_state[chat_id] = {"dict_type": "shared"}
    
    conn.close()

@bot.message_handler(func=lambda message: message.text == "🆕 Створити спільний словник")
def create_shared_dictionary(message):
    """Create a new shared dictionary"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Зберігаємо стан користувача
    user_state[chat_id] = {
        "step": "creating_shared_dict",
    }
    
    bot.send_message(chat_id, "Введіть назву для спільного словника:",
                    reply_markup=main_menu_cancel())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "creating_shared_dict")
def handle_shared_dict_name(message):
    """Handle shared dictionary name input"""
    chat_id = message.chat.id
    
    if message.text == "Відміна" or message.text == "✖️ Відміна":
        clear_state(chat_id)
        bot.send_message(chat_id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(chat_id))
        return
    
    dict_name = message.text.strip()
    
    if len(dict_name) < 3 or len(dict_name) > 30:
        bot.send_message(chat_id, "❌ Назва словника повинна містити від 3 до 30 символів.")
        return
    
    # Створюємо спільний словник
    code, shared_dict_id = db_manager.create_shared_dictionary(chat_id, dict_name)
    
    # Повідомляємо про успішне створення та показуємо код доступу
    bot.send_message(
        chat_id,
        f"✅ Спільний словник '{dict_name}' успішно створено!\n\n"
        f"Код доступу: <code>{code}</code>\n\n"
        f"Поділіться цим кодом з друзями, щоб вони могли приєднатися до вашого словника.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(chat_id)
    )
    
    clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "🔑 Вступити до спільного словника")
def join_shared_dictionary(message):
    """Join an existing shared dictionary"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Зберігаємо стан користувача
    user_state[chat_id] = {
        "step": "joining_shared_dict",
    }
    
    bot.send_message(chat_id, "Введіть код доступу до спільного словника:",
                    reply_markup=main_menu_cancel())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "joining_shared_dict")
def handle_shared_dict_code(message):
    """Handle shared dictionary code input"""
    chat_id = message.chat.id
    
    if message.text == "Відміна" or message.text == "✖️ Відміна":
        clear_state(chat_id)
        bot.send_message(chat_id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(chat_id))
        return
    
    code = message.text.strip().upper()
    
    if len(code) != 6:
        bot.send_message(chat_id, "❌ Код доступу повинен містити 6 символів.")
        return
    
    # Приєднуємось до спільного словника
    success, result = db_manager.join_shared_dictionary(chat_id, code)
    
    if success:
        # Повідомляємо про успішне приєднання
        bot.send_message(
            chat_id,
            f"✅ Ви успішно приєднались до спільного словника '{result}'!",
            reply_markup=main_menu_keyboard(chat_id)
        )
    else:
        # Повідомляємо про помилку
        bot.send_message(chat_id, f"❌ {result}")
    
    clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "📋 Мої спільні словники")
def my_shared_dictionaries(message):
    """Show user's shared dictionaries"""
    chat_id = message.chat.id
    
    # Отримуємо список спільних словників користувача
    shared_dicts = db_manager.get_user_shared_dictionaries(chat_id)
    
    if not shared_dicts:
        bot.send_message(
            chat_id,
            "📭 Ви не є учасником жодного спільного словника.",
            reply_markup=shared_dictionary_keyboard()
        )
        return
    
    # Показуємо список словників
    response = "📋 Ваші спільні словники:\n\n"
    
    for dict_info in shared_dicts:
        admin_status = "👑 Адміністратор" if dict_info['is_admin'] else "👤 Учасник"
        response += f"• <b>{dict_info['name']}</b> ({admin_status})\n"
        response += f"  Код доступу: <code>{dict_info['code']}</code>\n\n"
    
    response += "Оберіть словник, який бажаєте використовувати:"
    
    # Створюємо інлайн клавіатуру для вибору словника
    markup = telebot.types.InlineKeyboardMarkup()
    
    for dict_info in shared_dicts:
        admin_icon = "👑" if dict_info['is_admin'] else "👤"
        button_text = f"{admin_icon} {dict_info['name']}"
        markup.add(telebot.types.InlineKeyboardButton(
            button_text, 
            callback_data=f"use_shared_dict_{dict_info['id']}"
        ))
    
    bot.send_message(
        chat_id,
        response,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("use_shared_dict_"))
def use_shared_dictionary(call):
    """Switch to a specific shared dictionary"""
    chat_id = call.message.chat.id
    shared_dict_id = int(call.data.replace("use_shared_dict_", ""))
    
    # Оновлюємо статус користувача
    import db_manager
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Перевіряємо, чи користувач є адміністратором цього словника
    cursor.execute('SELECT created_by FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
    creator_result = cursor.fetchone()
    is_admin = creator_result and creator_result[0] == chat_id
    
    # Оновлюємо запис у базі даних
    if is_admin:
        cursor.execute('UPDATE users SET shared_dict_id = ?, shared_dict_admin = 1 WHERE chat_id = ?', 
                     (shared_dict_id, chat_id))
    else:
        cursor.execute('UPDATE users SET shared_dict_id = ? WHERE chat_id = ?', 
                     (shared_dict_id, chat_id))
    
    conn.commit()
    
    # Отримуємо назву словника
    cursor.execute('SELECT name FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
    dict_name = cursor.fetchone()[0]
    conn.close()
    
    # Зберігаємо важливі налаштування користувача
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    # Оновлюємо стан в пам'яті ПОВНІСТЮ, не втрачаючи важливі параметри
    user_state[chat_id] = {
        "dict_type": "shared", 
        "shared_dict_id": shared_dict_id,
        "level": level
    }
    
    # Повідомляємо користувача
    bot.answer_callback_query(call.id, f"Обрано спільний словник: {dict_name}")
    bot.delete_message(chat_id, call.message.message_id)
    
    admin_text = " (ви адміністратор)" if is_admin else ""
    
    bot.send_message(
        chat_id,
        f"📚 Обрано спільний словник: <b>{dict_name}</b>{admin_text}\n"
        f"Тепер всі дії будуть виконуватись у цьому словнику.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(chat_id)
    )
