# -*- coding: utf-8 -*-

"""
Обробники для головного меню та базової навігації.
"""

import pandas as pd
from config import bot, user_state
from utils import clear_state, track_activity, main_menu_keyboard, language_selection_keyboard, main_menu_cancel
from storage import get_user_file_path, save_dataframe

@bot.message_handler(commands=["start"])
def main_menu(message):
    """Show main menu or language selection"""
    clear_state(message.chat.id)
    file_path, language = get_user_file_path(message.chat.id)
    track_activity(message.chat.id)
    
    if not file_path:
        # If file doesn't exist, offer language selection
        bot.send_message(message.chat.id, "🌍 Виберіть мову, на якій бажаєте отримувати переклад слів:", 
                         reply_markup=language_selection_keyboard())
        user_state[message.chat.id] = {"step": "language_selection"}
    else:
        # If file exists, show main menu
        bot.send_message(message.chat.id, "Оберіть дію:", 
                         reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: message.text in ["🇺🇦 Українська", "🇷🇺 Російська"])
def handle_language_selection(message):
    """Handle language selection"""
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("step") == "language_selection":
        language = "uk" if message.text == "🇺🇦 Українська" else "ru"
        
        # Create empty dictionary for user
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        save_dataframe(chat_id, df, language)
        
        bot.send_message(chat_id, f"✅ Мову перекладу обрано: {message.text}. Тепер ви можете додавати слова та вивчати їх.", 
                         reply_markup=main_menu_keyboard(chat_id))
        clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text in ["✖️ Відміна", "Відміна"])
def cancel_action(message):
    """Cancel current action and return to main menu"""
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "↩️ Повернутися до головного меню")
def return_to_main_menu(message):
    """Return to main menu"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника, але видаляємо повідомлення активності
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Відправляємо повідомлення головного меню
    bot.send_message(chat_id, "Головне меню:", 
                   reply_markup=main_menu_keyboard(chat_id))
