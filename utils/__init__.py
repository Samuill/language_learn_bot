# -*- coding: utf-8 -*-

"""
Модуль з утилітами для бота.
"""

from .state_helpers import clear_state, save_message_id
from .activity_tracking import track_activity
from .path_helpers import *
from .keyboards import (
    main_menu_keyboard,
    main_menu_cancel,
    easy_level_keyboard,
    medium_level_keyboard,
    hard_level_keyboard,
    shared_dictionary_keyboard,
    yes_no_cancel_keyboard
)

def clear_state(chat_id, preserve_dict_type=False, preserve_messages=False, preserve_level=False):
    """Clear user state to prevent conflicts between activities"""
    from config import user_state, bot
    
    # Store values we want to preserve
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    level = user_state.get(chat_id, {}).get("level", "easy")
    language = user_state.get(chat_id, {}).get("language")
    current_menu = user_state.get(chat_id, {}).get("current_menu", "main")
    
    # Log the state clearing event
    try:
        from utils.console_logger import log_menu_transition
        log_menu_transition(chat_id, current_menu, current_menu, "State cleared")
    except:
        pass
    
    # Delete messages if they exist and we are not preserving them
    if not preserve_messages and chat_id in user_state:
        # Delete active messages
        active_messages = user_state[chat_id].get("active_messages", [])
        if active_messages:
            for msg_id in active_messages:
                try:
                    bot.delete_message(chat_id, msg_id)
                except Exception as e:
                    # Silently ignore message deletion errors
                    pass
                    
        # Delete single message if exists
        message_id = user_state[chat_id].get("message_id")
        if message_id:
            try:
                bot.delete_message(chat_id, message_id)
            except Exception as e:
                # Silently ignore message deletion errors
                pass
    
    # Clear state
    if chat_id in user_state:
        user_state[chat_id] = {}
    
    # Restore preserved values
    if chat_id in user_state:
        # Always preserve these important settings
        user_state[chat_id]["current_menu"] = current_menu
        
        if language:
            user_state[chat_id]["language"] = language
            
        if preserve_dict_type:
            user_state[chat_id]["dict_type"] = dict_type
            if shared_dict_id:
                user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        if preserve_level and level:
            user_state[chat_id]["level"] = level
            
# Backward compatibility
def get_user_params_path(chat_id):
    from .path_helpers import get_user_params_path as gup
    return gup(chat_id)

def medium_level_keyboard(chat_id=None):
    """Create medium level keyboard with localized buttons if chat_id provided"""
    from telebot.types import ReplyKeyboardMarkup
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    if chat_id:
        from utils.language_utils import get_text
        keyboard.row(get_text("choose_correct_spelling", chat_id), get_text("fill_in_gaps", chat_id))
        keyboard.row(get_text("learn_possessive_pronouns", chat_id) + " (" + get_text("medium_level", chat_id) + ")")
        keyboard.row(get_text("back_to_main_menu", chat_id))
    else:
        keyboard.row("🔤 Вибір правильного написання", "📝 Заповніть пропуски")
        keyboard.row("🧩 Вивчати присвійні займенники (середній)")
        keyboard.row("↩️ Повернутися до головного меню")
    
    return keyboard

def hard_level_keyboard(chat_id=None):
    """Create hard level keyboard with localized buttons if chat_id provided"""
    from telebot.types import ReplyKeyboardMarkup
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    if chat_id:
        from utils.language_utils import get_text
        keyboard.row(get_text("advanced_game", chat_id), get_text("word_typing", chat_id))
        keyboard.row(get_text("article_typing", chat_id))
        keyboard.row(get_text("learn_possessive_pronouns", chat_id) + " (" + get_text("hard_level", chat_id) + ")")
        keyboard.row(get_text("back_to_main_menu", chat_id))
    else:
        keyboard.row("🧩 Складна гра", "📝 Введення слів")
        keyboard.row("🏷️ Введення артиклів")
        keyboard.row("🧩 Вивчати присвійні займенники (складний)")
        keyboard.row("↩️ Повернутися до головного меню")
    
    return keyboard
