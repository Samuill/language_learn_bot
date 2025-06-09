# -*- coding: utf-8 -*-

"""
Start handler for the bot.
"""

import telebot
from config import bot, user_state
import db_manager
from utils import main_menu_keyboard
from utils.language_utils import get_text
from utils.state_helpers import save_message_id

# Define language flags and codes for easier identification
LANGUAGE_FLAGS = {
    "🇬🇧": "en",
    "🇺🇦": "uk",
    "🇷🇺": "ru",
    "🇹🇷": "tr",
    "🇸🇾": "ar"
}

# Language names in their native form
LANGUAGE_NAMES = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
    "tr": "Türkçe",
    "ar": "العربية"
}

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Handle the /start command - only show language selection for new users"""
    chat_id = message.chat.id
    
    # Check if user already has a language set
    import db_manager
    existing_language = db_manager.get_user_language(chat_id)
    
    if existing_language:
        # User already has language - redirect to main menu
        from handlers.main_menu import main_menu
        main_menu(message)
        return
    
    # New user - show language selection
    if chat_id in user_state:
        user_state.pop(chat_id)
    
    user_state[chat_id] = {"state": "language_selection"}
    show_language_selection(chat_id)

def show_language_selection(chat_id):
    """Show language selection keyboard to user"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Add language buttons in rows of 2
    row = []
    for flag, code in LANGUAGE_FLAGS.items():
        name = LANGUAGE_NAMES.get(code, code.upper())
        button_text = f"{flag} {name}"
        row.append(button_text)
        
        if len(row) == 2:
            keyboard.row(*row)
            row = []
    
    # Add any remaining buttons
    if row:
        keyboard.row(*row)
    
    sent_message = bot.send_message(
        chat_id,
        get_text("choose_language", chat_id),  # Use the localized key instead of hardcoded text
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(commands=['language', 'change_language', 'lang'])
def change_language_command(message):
    """Handle language change commands - force language selection"""
    chat_id = message.chat.id
    
    # Save important state data
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    # Set state for language selection but preserve key settings
    user_state[chat_id] = {
        "state": "language_selection",
        "dict_type": dict_type,
        "shared_dict_id": shared_dict_id,
        "level": level
    }
    
    # Show language selection
    show_language_selection(chat_id)

# Add message handlers for each specific language button to prioritize them
@bot.message_handler(func=lambda message: message.text in ["🇬🇧 English", "🇺🇦 Українська", "🇷🇺 Русский", "🇹🇷 Türkçe", "🇸🇾 العربية"])
def handle_language_button(message):
    """Handle direct language button presses"""
    chat_id = message.chat.id
    text = message.text
    
    # Map button text to language codes
    language_map = {
        "🇬🇧 English": "en",
        "🇺🇦 Українська": "uk",
        "🇷🇺 Русский": "ru",
        "🇹🇷 Türkçe": "tr",
        "🇸🇾 العربية": "ar"
    }
    
    language_code = language_map.get(text)
    
    if language_code:
        # Backup user state
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        try:
            # Update language in database
            success = db_manager.set_user_language(chat_id, language_code)
            
            if success:
                # Update user state
                user_state[chat_id] = {
                    "state": "main_menu",
                    "dict_type": dict_type,
                    "level": level,
                    "language": language_code
                }
                
                if shared_dict_id:
                    user_state[chat_id]["shared_dict_id"] = shared_dict_id
                
                # Send confirmation using localization
                bot.send_message(chat_id, get_text("language_selected", chat_id))
                
                # Send main menu using localization
                sent_message = bot.send_message(
                    chat_id, 
                    get_text("main_menu", chat_id), 
                    reply_markup=main_menu_keyboard(chat_id)
                )
                save_message_id(chat_id, sent_message.message_id)
            else:
                bot.send_message(chat_id, get_text("error_occurred", chat_id))
        except Exception as e:
            print(f"Error setting language: {e}")
            bot.send_message(chat_id, get_text("error_occurred", chat_id))

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("state") == "language_selection")
def handle_language_selection(message):
    """Handle language selection from keyboard during language selection state"""
    chat_id = message.chat.id
    text = message.text
    
    # Define language mappings
    language_buttons = [
        ("🇬🇧", "en", "English"),
        ("🇺🇦", "uk", "Українська"),
        ("🇷🇺", "ru", "Русский"),
        ("🇹🇷", "tr", "Türkçe"),
        ("🇸🇾", "ar", "العربية")
    ]
    
    # Extract language code from button text
    language_code = None
    
    for flag, code, name in language_buttons:
        if flag in text or name in text:
            language_code = code
            break
    
    if not language_code:
        bot.send_message(chat_id, "Sorry, I couldn't recognize your language choice. Please try again.")
        return
    
    try:
        # Save previous state settings we want to keep
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        # Update language in database
        db_manager.set_user_language(chat_id, language_code)
        
        # Update user state
        user_state[chat_id] = {
            "state": "main_menu",
            "dict_type": dict_type,
            "level": level,
            "language": language_code  # Store the selected language in state
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Send confirmation message using localization
        bot.send_message(chat_id, get_text("language_selected", chat_id))
        
        # Send main menu message using localization
        menu_markup = main_menu_keyboard(chat_id)
        sent_message = bot.send_message(
            chat_id, 
            get_text("main_menu", chat_id), 
            reply_markup=menu_markup
        )
        save_message_id(chat_id, sent_message.message_id)
        
    except Exception as e:
        print(f"Error in language selection: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, get_text("error_occurred", chat_id))
