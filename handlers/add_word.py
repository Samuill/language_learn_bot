# -*- coding: utf-8 -*-

"""
Handlers for adding new words to user's dictionary.
"""

import telebot
import db_manager
from config import bot, user_state, translator
from utils.language_utils import get_text
from utils import clear_state, main_menu_keyboard, main_menu_cancel
from utils.input_handlers import safe_next_step_handler, sanitize_user_input
from utils.state_helpers import save_message_id
import asyncio

# Import the functions that were previously undefined
from utils.input_handlers import is_menu_navigation_command, handle_exit_from_activity

@bot.message_handler(func=lambda message: message.text.strip() == "➕ Додати нове слово" or message.text == get_text("add_new_word", message.chat.id))
def add_word_started(message):
    try:
        chat_id = message.chat.id
        
        # Ensure user_state[chat_id] exists before trying to access it
        if chat_id not in user_state:
            user_state[chat_id] = {}
            
        state = user_state[chat_id]
        dict_type = state.get("dict_type", "personal")
        
        # Check if user can add words to the current dictionary
        if dict_type == "shared":
            shared_dict_id = state.get("shared_dict_id")
            if not shared_dict_id or not db_manager.is_user_admin_of_shared_dict(chat_id, shared_dict_id): # Added check for shared_dict_id
                bot.send_message(chat_id,
                                 get_text("cannot_add_word_in_shared", chat_id,
                                          "Ви не маєте дозволу додавати нові слова до спільного словника або словник не обрано."))
                return
        # Removed the common dictionary type check
        
        # Clear state but preserve dictionary type
        clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
        
        # Set state for adding a word
        user_state[chat_id]["step"] = "add_word"
        
        # Log the action for analytics
        from utils.logging_utils import log_action
        log_action("add_word_started", {"chat_id": chat_id})

        # Send message to request word
        sent_message = bot.send_message(
            chat_id, 
            get_text("add_word_prompt", chat_id, "Введіть слово, яке хочете додати:"),
            reply_markup=main_menu_cancel()
        )
        
        # Register handler for user's response
        safe_next_step_handler(sent_message, process_word_input)

    except Exception as e:
        print(f"Error in add_word_started for chat_id {message.chat.id if message else 'N/A'}: {e}")
        if message and message.chat:
            bot.send_message(message.chat.id, get_text("error_occurred", message.chat.id))
        # Potentially clear state or offer main menu
        if message and message.chat:
            clear_state(message.chat.id) # Or preserve dict type if appropriate
            bot.send_message(message.chat.id, get_text("main_menu", message.chat.id), reply_markup=main_menu_keyboard(message.chat.id))


# Add an alias for backward compatibility with existing imports
add_word = add_word_started

def process_word_input(message):
    """Process the word input from the user"""
    try:
        chat_id = message.chat.id

        # Check for menu navigation commands (e.g. "Cancel", "Main Menu")
        if is_menu_navigation_command(message):
            handle_exit_from_activity(message)
            return  # exit only on navigation commands
    
        # Validate input
        if not message.text:
            bot.send_message(chat_id, get_text("enter_word_error", chat_id, "❌ Please enter a word as text!"))
            safe_next_step_handler(message, process_word_input)
            return
        
        word_to_add = sanitize_user_input(message.text.strip())
        
        if not word_to_add:
            bot.send_message(chat_id, get_text("empty_word_error", chat_id, "❌ Please enter a non-empty word!"))
            safe_next_step_handler(message, process_word_input)
            return
        
        # Store the word in user state
        user_state[chat_id]["word_to_add"] = word_to_add
        
        # Try to translate the word from German
        try:
            language = db_manager.get_user_language(chat_id)
            if not language:
                bot.send_message(chat_id, get_text("language_not_selected", chat_id, "❌ Translation language not selected. Try /start."))
                return
            
            # Translate from German to user's language
            translation_result = asyncio.run(translator.translate(word_to_add, src='de', dest=language))
            translation = translation_result.text
            
            # Ask for confirmation
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(get_text("yes", chat_id), get_text("no", chat_id), get_text("cancel", chat_id))
            
            confirm_msg = bot.send_message(
                chat_id,
                f"{get_text('found_translation_confirm', chat_id)} {translation}{get_text('translation_confirm', chat_id)}",
                reply_markup=markup
            )
            
            # Register handler for confirmation on the sent message
            safe_next_step_handler(confirm_msg, lambda m: process_translation_confirm(m, word_to_add, translation, None))
            
        except Exception as e:
            print(f"Translation error for word '{word_to_add}': {e}")
            bot.send_message(chat_id, get_text("translation_failed", chat_id, "Failed to translate word. Please try again."))
            
            # Ask for manual translation
            manual_msg = bot.send_message(
                chat_id,
                get_text("enter_translation_manually", chat_id, "Enter the correct translation manually:"),
                reply_markup=main_menu_cancel()
            )
            
            # Register handler for manual translation on the sent message
            safe_next_step_handler(manual_msg, lambda m: process_manual_translation(m, word_to_add))
    except Exception as e:
        print(f"Error in process_word_input for chat_id {message.chat.id if message else 'N/A'}: {e}")
        if message and message.chat:
            bot.send_message(message.chat.id, get_text("error_occurred", message.chat.id))
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, get_text("main_menu", message.chat.id), reply_markup=main_menu_keyboard(message.chat.id))

def process_manual_translation(message, word_to_add):
    """Process manually entered translation"""
    try:
        chat_id = message.chat.id
        
        # Check for menu navigation commands
        if is_menu_navigation_command(message):
            handle_exit_from_activity(message)
            return
    
        translation = sanitize_user_input(message.text)
        
        if not translation:
            bot.send_message(chat_id, get_text("empty_translation_error", chat_id, "❌ Please enter a non-empty translation!"))
            safe_next_step_handler(message, lambda m: process_manual_translation(m, word_to_add))
            return
        
        # Save the translation
        user_state[chat_id]["translation_to_add"] = translation
        
        # Ask for confirmation
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(get_text("yes", chat_id), get_text("no", chat_id), get_text("cancel", chat_id))
        
        bot.send_message(
            chat_id,
            f"{get_text('found_translation_confirm', chat_id)}{translation}{get_text('translation_confirm', chat_id)}",
            reply_markup=markup
        )
        
        # Register handler for confirmation
        safe_next_step_handler(message, lambda m: process_translation_confirm(m, word_to_add, translation, None))
    except Exception as e:
        print(f"Error in process_manual_translation for chat_id {message.chat.id if message else 'N/A'}: {e}")
        if message and message.chat:
            bot.send_message(message.chat.id, get_text("error_occurred", message.chat.id))
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, get_text("main_menu", message.chat.id), reply_markup=main_menu_keyboard(message.chat.id))

def process_translation_confirm(message, word_to_add, translation_to_add, article_to_add):
    """Process translation confirmation"""
    try:
        chat_id = message.chat.id
        
        # Check for menu navigation commands
        if is_menu_navigation_command(message):
            handle_exit_from_activity(message)
            return
    
        user_input = sanitize_user_input(message.text)
        
        if user_input.lower() == get_text("yes", chat_id).lower():
            dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
            shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
            
            # Determine the dict_type to pass to db_manager.add_word.
            # If current dict_type is "shared", we still add to global `words` table,
            # so pass "common" (or any non-"personal") to prevent linking to user_X table by add_word itself.
            # The linking to shared_dict_X will be handled separately.
            add_word_dict_param = "personal" if dict_type == "personal" else "common"
            
            word_id = db_manager.add_word(
                chat_id,
                word_to_add,
                translation_to_add,
                dict_type=add_word_dict_param, 
                article=article_to_add
            )
            
            if word_id:
                if dict_type == "shared":
                    if shared_dict_id:
                        # Attempt to add to shared dictionary
                        shared_add_success, shared_add_message = db_manager.add_word_to_shared_dictionary(
                            chat_id, word_id, shared_dict_id
                        )
                        if shared_add_success:
                            # Try to get shared dictionary name for a more informative message
                            dict_name_for_msg = shared_add_message # Default to code/message from add_word_to_shared_dictionary
                            try:
                                conn = db_manager.get_connection()
                                cursor = conn.cursor()
                                cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
                                name_res = cursor.fetchone()
                                if name_res:
                                    dict_name_for_msg = f"«{name_res[0]}»"
                                conn.close()
                            except Exception: # pylint: disable=broad-except
                                pass # Ignore error, use default message
                        
                            bot.send_message(chat_id, get_text("word_added_to_shared_successfully", chat_id, f"✅ Слово успішно додано до спільного словника {dict_name_for_msg}!"), reply_markup=main_menu_keyboard(chat_id))
                        else:
                            bot.send_message(chat_id, get_text("word_added_to_shared_failed", chat_id, f"⚠️ Не вдалося додати слово до спільного словника: {shared_add_message}"), reply_markup=main_menu_keyboard(chat_id))
                    else:
                        # This case should ideally not happen if dict_type is shared and state is consistent
                        bot.send_message(chat_id, get_text("error_shared_dict_not_selected_for_add", chat_id, "Помилка: спільний словник не обрано або не існує для додавання."), reply_markup=main_menu_keyboard(chat_id))
                # Removed the common dictionary type message
                else:  # Personal dictionary (default)
                    bot.send_message(chat_id, get_text("word_added_successfully", chat_id, "✅ Слово успішно додано!"), reply_markup=main_menu_keyboard(chat_id))
            else:
                bot.send_message(chat_id, get_text("error_adding_word", chat_id, "❌ Error adding word."), reply_markup=main_menu_keyboard(chat_id))
                
            clear_state(chat_id)
            
        elif user_input.lower() == get_text("no", chat_id).lower():
            # Ask for manual translation
            manual_msg = bot.send_message(
                chat_id,
                get_text("enter_translation_manually", chat_id, "Enter the correct translation manually:"),
                reply_markup=main_menu_cancel()
            )
            
            # Register handler for manual translation on the sent message
            safe_next_step_handler(manual_msg, lambda m: process_manual_translation(m, word_to_add))
            
        elif user_input.lower() == get_text("cancel", chat_id).lower():
            handle_exit_from_activity(message)
            
        else:
            # Invalid input
            bot.send_message(chat_id, get_text("choose_yes_no_cancel", chat_id))
            
            # Re-register handler for confirmation
            safe_next_step_handler(message, lambda m: process_translation_confirm(m, word_to_add, translation_to_add, article_to_add))
    except Exception as e:
        print(f"Error in process_translation_confirm for chat_id {message.chat.id if message else 'N/A'}: {e}")
        if message and message.chat:
            bot.send_message(message.chat.id, get_text("error_occurred", message.chat.id))
            clear_state(message.chat.id)
            bot.send_message(message.chat.id, get_text("main_menu", message.chat.id), reply_markup=main_menu_keyboard(message.chat.id))
