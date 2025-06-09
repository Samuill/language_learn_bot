# -*- coding: utf-8 -*-

"""
Helper functions for game activities.
"""

import telebot
from config import bot, user_state
from utils import easy_level_keyboard, medium_level_keyboard, hard_level_keyboard
from utils.language_utils import get_text
from utils.state_management import get_user_state_value, update_user_state

def handle_game_result(chat_id, is_correct, word_id, feedback_message, continue_callback=None):
    """Handle game result with unified approach for all games"""
    from utils.dictionary_helpers import update_word_rating
    
    # Get difficulty level
    level = get_user_state_value(chat_id, "level", "easy")
    
    # Update word rating
    update_word_rating(chat_id, word_id, is_correct, level)
    
    # Send feedback
    bot.send_message(chat_id, feedback_message, parse_mode="HTML")
    
    # Continue game if callback provided
    if continue_callback and callable(continue_callback):
        bot.send_message(chat_id, get_text("continue_game", chat_id))
        continue_callback(chat_id)
    
    return True

def handle_game_error(chat_id, error, return_to_menu=True):
    """Handle errors in games consistently"""
    import traceback
    print(f"Game error: {error}")
    traceback.print_exc()
    
    # Get appropriate keyboard based on level
    level = get_user_state_value(chat_id, "level", "easy")
    
    if level == "hard":
        keyboard = hard_level_keyboard(chat_id)
    elif level == "medium":
        keyboard = medium_level_keyboard(chat_id)
    else:  # Default to easy
        keyboard = easy_level_keyboard(chat_id)
    
    # Send error message
    bot.send_message(
        chat_id,
        get_text("error_activity", chat_id),
        reply_markup=keyboard if return_to_menu else None
    )
    
    return False

def create_article_options_keyboard(word_id):
    """Create consistent article selection keyboard"""
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        telebot.types.InlineKeyboardButton("der", callback_data=f"art_der_{word_id}"),
        telebot.types.InlineKeyboardButton("die", callback_data=f"art_die_{word_id}"),
        telebot.types.InlineKeyboardButton("das", callback_data=f"art_das_{word_id}")
    )
    return markup
