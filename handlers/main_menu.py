# -*- coding: utf-8 -*-

"""
Обробники для головного меню та базової навігації.
"""

from config import bot, user_state
from utils import clear_state, track_activity, main_menu_keyboard
from utils.language_utils import get_text
from utils.state_helpers import save_message_id
from handlers.start import show_language_selection

@bot.message_handler(commands=["start"])
def main_menu(message):
    """Show main menu or language selection"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є мова в БД
    import db_manager
    language = db_manager.get_user_language(chat_id)
    track_activity(chat_id)
    
    if not language:
        # Якщо мови немає, пропонуємо обрати (тільки для нових користувачів)
        show_language_selection(chat_id)
        user_state[chat_id] = {"state": "language_selection"}
    else:
        # Мова вже встановлена - показуємо головне меню
        clear_state(chat_id)
        user_state[chat_id] = {
            "language": language,
            "dict_type": "personal",  # Default dictionary type
            "level": "easy"  # Default level
        }
        
        sent_message = bot.send_message(
            chat_id, 
            get_text("main_menu", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )
        save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(func=lambda message: message.text in ["✖️ Відміна", "Відміна"] or message.text == get_text("cancel", message.chat.id))
def cancel_action(message):
    """Cancel current action and return to main menu"""
    chat_id = message.chat.id
    clear_state(chat_id)
    sent_message = bot.send_message(
        chat_id, 
        get_text("cancelled", chat_id), 
        reply_markup=main_menu_keyboard(chat_id)  # Передаємо chat_id для локалізації
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(func=lambda message: message.text == "↩️ Повернутися до головного меню" or message.text == get_text("back_to_main_menu", message.chat.id))
def return_to_main_menu(message):
    """Return to main menu"""
    chat_id = message.chat.id
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    sent_message = bot.send_message(
        chat_id, 
        get_text("main_menu", chat_id),
        reply_markup=main_menu_keyboard(chat_id)  # Передаємо chat_id для локалізації
    )
    save_message_id(chat_id, sent_message.message_id)
