# -*- coding: utf-8 -*-

"""
Start handler for the bot.
"""

import telebot
from config import bot, user_state
import db_manager
from utils import main_menu_keyboard

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
    """Handle the /start command"""
    chat_id = message.chat.id
    
    # Clear any existing state
    if chat_id in user_state:
        user_state.pop(chat_id)
    
    # Set initial state
    user_state[chat_id] = {"state": "language_selection"}
    
    # Show language selection keyboard
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
    
    bot.send_message(
        chat_id,
        "Please select your language / Виберіть мову:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['language', 'change_language'])
def change_language_command(message):
    """Handle /language or /change_language command"""
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
    
    print(f"DIRECT LANGUAGE BUTTON DETECTED: {text}")
    
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
        print(f"Setting language for user {chat_id} to {language_code}")
        
        # Backup user state
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        # Update language in database
        success = db_manager.set_user_language(chat_id, language_code)
        print(f"Database update result: {success}")
        
        # Verify update
        new_language = db_manager.get_user_language(chat_id)
        print(f"Verified language in DB: {new_language}")
        
        # Update user state
        user_state[chat_id] = {
            "state": "main_menu",
            "dict_type": dict_type,
            "shared_dict_id": shared_dict_id,
            "level": level
        }
        
        # Send confirmation in the selected language
        confirmations = {
            "en": "✅ English language selected",
            "uk": "✅ Обрано українську мову",
            "ru": "✅ Выбран русский язык",
            "tr": "✅ Türkçe dil seçildi",
            "ar": "✅ تم اختيار اللغة العربية"
        }
        
        menu_texts = {
            "en": "Main menu:",
            "uk": "Головне меню:",
            "ru": "Главное меню:",
            "tr": "Ana menü:",
            "ar": "القائمة الرئيسية:"
        }
        
        confirmation = confirmations.get(language_code, "Language selected")
        menu_text = menu_texts.get(language_code, "Main menu:")
        
        # Send messages
        bot.send_message(chat_id, confirmation)
        bot.send_message(chat_id, menu_text, reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("state") == "language_selection")
def handle_language_selection(message):
    """Handle language selection from keyboard during language selection state"""
    chat_id = message.chat.id
    text = message.text
    
    print(f"LANGUAGE SELECTION MESSAGE RECEIVED: '{text}' (User state: {user_state.get(chat_id, {})})")
    
    # Log the button press
    log_language_event(chat_id, "BUTTON_PRESSED", f"Button text: '{text}'")
    
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
    language_name = None
    
    for flag, code, name in language_buttons:
        if flag in text or name in text:
            language_code = code
            language_name = name
            log_language_event(chat_id, "LANGUAGE_IDENTIFIED", f"Identified language: {code} ({name}) from button text: '{text}'")
            break
    
    if not language_code:
        log_language_event(chat_id, "LANGUAGE_UNKNOWN", f"Could not identify language from button text: '{text}'")
        bot.send_message(chat_id, "Sorry, I couldn't recognize your language choice. Please try again.")
        return
    
    # Log the current language in DB
    try:
        import db_manager
        current_lang = db_manager.get_user_language(chat_id)
        log_language_event(chat_id, "CURRENT_LANGUAGE", f"Current language in DB: {current_lang}")
    except Exception as e:
        log_language_event(chat_id, "DB_ERROR", f"Error getting current language: {e}")
    
    # Log that we're about to update the database
    log_language_event(chat_id, "DB_UPDATE_START", f"Updating language in database to: {language_code}")
    
    try:
        # Update language in database
        result = db_manager.set_user_language(chat_id, language_code)
        log_language_event(chat_id, "DB_UPDATE_RESULT", f"Database update result: {result}")
        
        # Verify the update
        new_lang = db_manager.get_user_language(chat_id)
        log_language_event(chat_id, "DB_VERIFY", f"Language in DB after update: {new_lang}")
        
        # Save previous state settings we want to keep
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        # Log the current state
        log_language_event(chat_id, "STATE_BEFORE", f"User state before update: {user_state.get(chat_id, {})}")
        
        # Update user state
        user_state[chat_id] = {
            "state": "main_menu",
            "dict_type": dict_type,
            "shared_dict_id": shared_dict_id,
            "level": level,
            "language": language_code  # Store the selected language in state
        }
        
        # Log the new state
        log_language_event(chat_id, "STATE_AFTER", f"User state after update: {user_state[chat_id]}")
        
        # Send confirmation message in the selected language
        if language_code == "en":
            confirmation = "✅ English language selected"
        elif language_code == "uk":
            confirmation = "✅ Обрано українську мову"
        elif language_code == "ru":
            confirmation = "✅ Выбран русский язык"
        elif language_code == "tr":
            confirmation = "✅ Türkçe dil seçildi"
        elif language_code == "ar":
            confirmation = "✅ تم اختيار اللغة العربية"
        else:
            confirmation = f"✅ Language selected: {language_name}"
        
        log_language_event(chat_id, "SENDING_CONFIRMATION", f"Sending confirmation message: '{confirmation}'")
        bot.send_message(chat_id, confirmation)
        
        # Send main menu message
        from utils import main_menu_keyboard
        
        if language_code == "en":
            menu_text = "Main menu:"
        elif language_code == "uk":
            menu_text = "Головне меню:"
        elif language_code == "ru":
            menu_text = "Главное меню:"
        elif language_code == "tr":
            menu_text = "Ana menü:"
        elif language_code == "ar":
            menu_text = "القائمة الرئيسية:"
        else:
            menu_text = "Menu:"
        
        log_language_event(chat_id, "SENDING_MENU", f"Sending main menu: '{menu_text}'")
        menu_markup = main_menu_keyboard(chat_id)
        bot.send_message(chat_id, menu_text, reply_markup=menu_markup)
        
        log_language_event(chat_id, "PROCESS_COMPLETE", f"Language selection process completed successfully")
        
    except Exception as e:
        log_language_event(chat_id, "ERROR", f"Error in language selection process: {str(e)}")
        import traceback
        log_language_event(chat_id, "TRACEBACK", traceback.format_exc())
        bot.send_message(chat_id, "Sorry, an error occurred while setting your language. Please try again later.")

def get_language_confirmation(language_code):
    """Get language selection confirmation message in the selected language"""
    messages = {
        "en": "✅ English language selected",
        "uk": "✅ Обрано українську мову",
        "ru": "✅ Выбран русский язык",
        "tr": "✅ Türkçe dil seçildi",
        "ar": "✅ تم اختيار اللغة العربية"
    }
    return messages.get(language_code, f"✅ Language selected: {language_code}")

def get_main_menu_text(language_code):
    """Get main menu text in the selected language"""
    messages = {
        "en": "Main menu:",
        "uk": "Головне меню:",
        "ru": "Главное меню:",
        "tr": "Ana menü:",
        "ar": "القائمة الرئيسية:"
    }
    return messages.get(language_code, "Menu:")
