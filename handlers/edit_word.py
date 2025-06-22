# -*- coding: utf-8 -*-

"""
Обробники для редагування слів у словнику.
"""

import telebot  # Add explicit import for telebot
from googletrans import Translator
import asyncio
from config import bot, user_state, translator
from utils import clear_state, main_menu_keyboard, main_menu_cancel
from utils.state_helpers import save_message_id
from utils.language_utils import get_text
from utils.input_handlers import safe_next_step_handler, sanitize_user_input, is_system_command, is_menu_navigation_command, handle_exit_from_activity
import db_manager
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Створюємо пул потоків для асинхронної обробки запитів до БД
executor = ThreadPoolExecutor()

WORDS_PER_PAGE_EDIT = 18

# Helper function to create the word management menu keyboard
def word_management_menu_keyboard(chat_id):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(
        telebot.types.KeyboardButton(get_text("edit_delete_single_word_button", chat_id, "✏️ Редагувати/Видалити слово"))
    )
    keyboard.add(
        telebot.types.KeyboardButton(get_text("bulk_delete_words_button", chat_id, "🗑️ Масове видалення слів"))
    )
    keyboard.add(
        telebot.types.KeyboardButton(get_text("bulk_add_words_button", chat_id, "➕ Масове додавання слів")) # Placeholder for bulk add
    )
    keyboard.add(
        telebot.types.KeyboardButton(get_text("back_to_main_menu", chat_id, "↩️ Повернутися до головного меню"))
    )
    return keyboard

# Удален старый обработчик edit_word_start - теперь обрабатывается в dictionaries.py

# Обработчики кнопок меню редактирования - работают как кнопки активностей в уровнях
@bot.message_handler(func=lambda message: message.text == get_text("edit_delete_single_word_button", message.chat.id))
def handle_edit_delete_single_word(message):
    """Handle single word edit/delete button"""
    initiate_single_word_edit_or_delete(message)

@bot.message_handler(func=lambda message: message.text == get_text("bulk_delete_words_button", message.chat.id))
def handle_bulk_delete_words(message):
    """Handle bulk delete words button"""
    initiate_bulk_delete(message)

@bot.message_handler(func=lambda message: message.text == get_text("bulk_add_words_button", message.chat.id))
def handle_bulk_add_words(message):
    """Handle bulk add words button"""
    initiate_bulk_add_words(message)

# Удален старый handle_word_management_choice - теперь каждая кнопка имеет свой обработчик

def handle_word_management_choice(message):
    """Заглушка для обратной совместимости - перенаправляет в меню"""
    from handlers.main_menu import return_to_main_menu
    return_to_main_menu(message)

def initiate_single_word_edit_or_delete(message):
    """Start the process for editing or deleting a single word."""
    chat_id = message.chat.id
    # Зберігаємо стан користувача у змінній, щоб передати її у асинхронний метод
    current_state = {
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal"),
        "shared_dict_id": user_state.get(chat_id, {}).get("shared_dict_id")
    }
    # Запуск завантаження даних у окремому потоці
    executor.submit(_async_load_words_for_edit, chat_id, current_state, message)

def _async_load_words_for_edit(chat_id, state, message):
    """Асинхронно завантажує слова для редагування."""
    try:
        dict_type = state["dict_type"]
        shared_dict_id = state["shared_dict_id"]
        
        # Перевіряємо стан і втановлюємо його
        if chat_id not in user_state:
            user_state[chat_id] = {}
          # Завантажуємо слова з БД
        df = None
        if dict_type == "shared" and shared_dict_id:
            df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
        else: # Personal or common
            df = db_manager.get_user_words(chat_id, dict_type)
        
        if df is None or df.empty:
            dict_name_key = f"{dict_type}_dictionary" if dict_type != "common" else "common_dictionary"
            dict_name_text = get_text(dict_name_key, chat_id)
            
            bot.send_message(
                chat_id, 
                f"{get_text('in', chat_id)} {dict_name_text} {get_text('no_words_to_edit', chat_id, 'немає слів для редагування.')}",
                reply_markup=word_management_menu_keyboard(chat_id) # Back to word management menu
            )
            return
        
        # Update user state for selecting a single word to edit
        user_state[chat_id]["step"] = "selecting_word_to_edit" # This state is used by callback handlers
        user_state[chat_id]["available_words_list"] = df.to_dict('records') # Store as list of dicts
        user_state[chat_id]['edit_current_page'] = 0
        # dict_type and shared_dict_id should be preserved
        user_state[chat_id]["dict_type"] = dict_type
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Show word selection (inline keyboard)
        show_word_selection_page(chat_id, message_to_edit=None) # Send initial page
            
    except Exception as e:
        print(f"Error in _async_load_words_for_edit for chat_id {chat_id}: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)

def show_word_selection_page(chat_id, message_to_edit=None):
    """Show a page of available words for editing with pagination."""
    try:
        if chat_id not in user_state or "available_words_list" not in user_state[chat_id]:
            bot.send_message(chat_id, get_text("error_occurred", chat_id), reply_markup=main_menu_keyboard(chat_id))
            return

        all_words_list = user_state[chat_id]["available_words_list"]
        current_page = user_state[chat_id].get('edit_current_page', 0)

        start_index = current_page * WORDS_PER_PAGE_EDIT
        end_index = start_index + WORDS_PER_PAGE_EDIT
        words_to_show_list = all_words_list[start_index:end_index]

        markup = telebot.types.InlineKeyboardMarkup(row_width=2) # Max 2 words per row
        
        temp_row_buttons = []
        for word_data in words_to_show_list:
            word = word_data['word']
            translation = word_data.get('translation', '') # Ensure translation exists
            button_text = f"{word} - {translation[:15]}{'...' if len(translation) > 15 else ''}"
            button = telebot.types.InlineKeyboardButton(
                button_text,
                callback_data=f"edit_word_{word_data['id']}"
            )
            temp_row_buttons.append(button)
            if len(temp_row_buttons) == 2:
                markup.row(*temp_row_buttons)
                temp_row_buttons = []
        if temp_row_buttons: # Add any remaining button if odd number
            markup.row(*temp_row_buttons)

        pagination_buttons = []
        if current_page > 0:
            pagination_buttons.append(telebot.types.InlineKeyboardButton(
                get_text("previous_page_button", chat_id, "⬅️ Попередня"),
                callback_data="edit_page_prev"
            ))
        
        if end_index < len(all_words_list):
            pagination_buttons.append(telebot.types.InlineKeyboardButton(
                get_text("next_page_button", chat_id, "➡️ Наступна"),
                callback_data="edit_page_next"
            ))
        
        if pagination_buttons:
            markup.row(*pagination_buttons) # Add pagination buttons in a new row

        message_text = get_text("select_word_to_edit", chat_id, "Оберіть слово для редагування:")
        
        if not words_to_show_list and current_page == 0: # No words at all
             message_text = get_text("no_words_to_edit_in_list", chat_id, "Немає слів для редагування у поточному списку.")


        if message_to_edit:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_to_edit.message_id,
                text=message_text,
                reply_markup=markup
            )
        else:
            sent_message = bot.send_message(
                chat_id,
                message_text,
                reply_markup=markup
            )
            save_message_id(chat_id, sent_message.message_id)
            
    except Exception as e:
        print(f"Error in show_word_selection_page for chat_id {chat_id}: {e}")
        bot.send_message(chat_id, get_text("error_occurred", chat_id), reply_markup=main_menu_keyboard(chat_id))


@bot.callback_query_handler(func=lambda call: call.data == "edit_page_prev")
def handle_edit_prev_page(call):
    """Handle 'Previous Page' for word editing selection."""
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or "available_words_list" not in user_state[chat_id]:
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id, "Сесія застаріла, спробуйте знову."))
            return

        current_page = user_state[chat_id].get('edit_current_page', 0)
        if current_page > 0:
            user_state[chat_id]['edit_current_page'] = current_page - 1
            show_word_selection_page(chat_id, message_to_edit=call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_prev_page: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))

@bot.callback_query_handler(func=lambda call: call.data == "edit_page_next")
def handle_edit_next_page(call):
    """Handle 'Next Page' for word editing selection."""
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or "available_words_list" not in user_state[chat_id]:
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id, "Сесія застаріла, спробуйте знову."))
            return

        current_page = user_state[chat_id].get('edit_current_page', 0)
        all_words_list = user_state[chat_id]["available_words_list"]
        if (current_page + 1) * WORDS_PER_PAGE_EDIT < len(all_words_list):
            user_state[chat_id]['edit_current_page'] = current_page + 1
            show_word_selection_page(chat_id, message_to_edit=call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_next_page: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_word_"))
def handle_word_selection_for_edit(call):
    """Handle word selection for editing"""
    chat_id = call.message.chat.id
    word_id = int(call.data.replace("edit_word_", ""))
    
    if chat_id not in user_state or user_state[chat_id].get("step") != "selecting_word_to_edit":
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    # Find selected word in available words
    available_words_list = user_state[chat_id].get("available_words_list", [])
    selected_word = next((word for word in available_words_list if word['id'] == word_id), None)
    
    if not selected_word:
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))
        return
    
    # Update user state
    user_state[chat_id].update({
        "step": "editing_word",
        "selected_word": selected_word,
        "edit_mode": "choose_action"
    })
    
    # Show edit options
    show_edit_options(call.message, selected_word)

def show_edit_options(message, word_data):
    """Show editing options for the selected word"""
    chat_id = message.chat.id
    
    # Create keyboard with edit options
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(
            get_text("edit_translation", chat_id, "✏️ Редагувати переклад"),
            callback_data="edit_translation"
        )
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            get_text("delete_word", chat_id, "🗑️ Видалити слово"),
            callback_data="delete_word"
        )
    )
    markup.add(
        telebot.types.InlineKeyboardButton(
            get_text("cancel", chat_id),
            callback_data="cancel_edit"
        )
    )
    
    try:
        bot.edit_message_text(
            f"📝 {get_text('selected_word_for_edit', chat_id, 'Обране слово для редагування')}:\n\n"
            f"<b>{word_data['word']}</b> - <b>{word_data['translation']}</b>\n\n"
            f"{get_text('choose_edit_action', chat_id, 'Оберіть дію:')}",
            chat_id=chat_id,
            message_id=message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        bot.send_message(
            chat_id,
            f"📝 {get_text('selected_word_for_edit', chat_id, 'Обране слово для редагування')}:\n\n"
            f"<b>{word_data['word']}</b> - <b>{word_data['translation']}</b>\n\n"
            f"{get_text('choose_edit_action', chat_id, 'Оберіть дію:')}",
            parse_mode="HTML",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data in ["edit_translation", "delete_word", "cancel_edit"])
def handle_edit_action(call):
    """Handle edit action selection"""
    try:
        chat_id = call.message.chat.id
        
        if chat_id not in user_state or user_state[chat_id].get("step") != "editing_word":
            bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
            return
    
        if call.data == "cancel_edit":
            # Go back to word management menu
            user_state[chat_id]["step"] = "word_management_menu"
            bot.edit_message_text( # Edit the inline message to remove it
                get_text("cancelled", chat_id),
                chat_id=chat_id,
                message_id=call.message.message_id
            )
            sent_msg = bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id, "Меню керування словами:"), reply_markup=word_management_menu_keyboard(chat_id))
            safe_next_step_handler(sent_msg, handle_word_management_choice)
            return
    
        elif call.data == "edit_translation":
            user_state[chat_id]["edit_mode"] = "editing_translation"
            
            bot.edit_message_text(
                f"{get_text('enter_new_translation', chat_id, 'Введіть новий переклад для слова')}:\n\n"
                f"<b>{user_state[chat_id]['selected_word']['word']}</b>\n\n"
                f"{get_text('current_translation', chat_id, 'Поточний переклад')}: <b>{user_state[chat_id]['selected_word']['translation']}</b>",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
            
            safe_next_step_handler(call.message, handle_new_translation)
    
        elif call.data == "delete_word":
            # Show confirmation for deletion
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    get_text("yes", chat_id, "✅ Так"),
                    callback_data="confirm_delete"
                ),
                telebot.types.InlineKeyboardButton(
                    get_text("no", chat_id, "❌ Ні"),
                    callback_data="cancel_delete"
                )
            )
            
            bot.edit_message_text(
                f"⚠️ {get_text('confirm_delete_word', chat_id, 'Ви впевнені, що хочете видалити слово')}?\n\n"
                f"<b>{user_state[chat_id]['selected_word']['word']}</b> - <b>{user_state[chat_id]['selected_word']['translation']}</b>",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
    except Exception as e:
        print(f"Error in handle_edit_action (call data: {call.data if call else 'N/A'}): {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_delete", "cancel_delete"])
def handle_delete_confirmation(call):
    """Handle word deletion confirmation"""
    try:
        chat_id = call.message.chat.id
        
        if chat_id not in user_state or user_state[chat_id].get("step") != "editing_word":
            bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
            return
    
        if call.data == "cancel_delete":
            # Go back to edit options for the current word
            show_edit_options(call.message, user_state[chat_id]['selected_word'])
            return
    
        elif call.data == "confirm_delete":
            try:
                word_data = user_state[chat_id]['selected_word']
                dict_type = user_state[chat_id]['dict_type']
                shared_dict_id = user_state[chat_id].get('shared_dict_id')
                
                # Delete word from database
                success = False
                if dict_type == "shared" and shared_dict_id:
                    success = db_manager.delete_word_from_shared_dict(chat_id, word_data['id'], shared_dict_id)
                else:
                    success = db_manager.delete_word_from_personal_dict(chat_id, word_data['id'])
                
                if success:
                    bot.edit_message_text(
                        f"✅ {get_text('word_deleted_success', chat_id, 'Слово успішно видалено')}:\n\n"
                        f"<b>{word_data['word']}</b> - <b>{word_data['translation']}</b>",
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        parse_mode="HTML"
                    )
                else:
                    bot.edit_message_text(
                        get_text("error_deleting_word", chat_id, "❌ Помилка при видаленні слова"),
                        chat_id=chat_id,
                        message_id=call.message.message_id
                    )
                
                clear_state(chat_id, preserve_dict_type=True) # Preserve dict type
                user_state[chat_id]["step"] = "word_management_menu"
                sent_msg = bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id, "Меню керування словами:"), reply_markup=word_management_menu_keyboard(chat_id))
                safe_next_step_handler(sent_msg, handle_word_management_choice)
                
            except Exception as e:
                print(f"Error deleting word: {e}")
                bot.edit_message_text(
                    get_text("error_occurred", chat_id),
                    chat_id=chat_id,
                    message_id=call.message.message_id
                )
    except Exception as e:
        print(f"Error in handle_delete_confirmation: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )

def handle_new_translation(message):
    """Handle new translation input"""
    try:
        chat_id = message.chat.id
        
        # Check for menu navigation commands first
        if is_menu_navigation_command(message): # This function needs to be robust
            # If user sends a command like "Cancel" or "Back to Main Menu"
            # Decide where to go: word management menu or main menu
            if message.text == get_text("back_to_main_menu", chat_id):
                from handlers.main_menu import return_to_main_menu
                return_to_main_menu(message)
                return
            elif message.text == get_text("cancel", chat_id): # Generic cancel
                user_state[chat_id]["step"] = "word_management_menu"
                bot.send_message(chat_id, get_text("cancelled", chat_id))
                sent_msg = bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id, "Меню керування словами:"), reply_markup=word_management_menu_keyboard(chat_id))
                safe_next_step_handler(sent_msg, handle_word_management_choice)
                return

        if is_system_command(message): # Make sure is_system_command is defined or imported
            bot.send_message(chat_id, get_text("invalid_translation_input", chat_id))
            safe_next_step_handler(message, handle_new_translation)
            return
    
        new_translation = sanitize_user_input(message.text.strip())
        
        if not new_translation:
            bot.send_message(chat_id, get_text("empty_translation_error", chat_id, "❌ Будь ласка, введіть непорожній переклад!"))
            safe_next_step_handler(message, handle_new_translation)
            return
        
        try:
            word_data = user_state[chat_id]['selected_word']
            dict_type = user_state[chat_id]['dict_type']
            shared_dict_id = user_state[chat_id].get('shared_dict_id')
            
            # Update translation in database
            success = False
            if dict_type == "shared" and shared_dict_id:
                success = db_manager.update_word_translation_shared_dict(chat_id, word_data['id'], new_translation, shared_dict_id)
            else:
                success = db_manager.update_word_translation_personal_dict(chat_id, word_data['id'], new_translation)
            
            if success:
                bot.send_message(
                    chat_id,
                    f"✅ {get_text('translation_updated_success', chat_id, 'Переклад успішно оновлено')}:\n\n"
                    f"<b>{word_data['word']}</b>\n"
                    f"{get_text('old_translation', chat_id, 'Старий переклад')}: <b>{word_data['translation']}</b>\n"
                    f"{get_text('new_translation', chat_id, 'Новий переклад')}: <b>{new_translation}</b>",
                    parse_mode="HTML",
                    reply_markup=main_menu_keyboard(chat_id)
                )
            else:
                bot.send_message(
                    chat_id,
                    get_text("error_updating_translation", chat_id, "❌ Помилка при оновленні перекладу"),
                    reply_markup=main_menu_keyboard(chat_id)
                )
        
            clear_state(chat_id, preserve_dict_type=True) # Preserve dict type
            user_state[chat_id]["step"] = "word_management_menu"
            sent_msg = bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id, "Меню керування словами:"), reply_markup=word_management_menu_keyboard(chat_id))
            safe_next_step_handler(sent_msg, handle_word_management_choice)
            
        except Exception as e:
            print(f"Error updating translation: {e}")
            bot.send_message(
                chat_id,
                get_text("error_occurred", chat_id),
                reply_markup=main_menu_keyboard(chat_id) # Or word_management_menu_keyboard
            )
        
        clear_state(chat_id, preserve_dict_type=True) # Preserve dict type
        user_state[chat_id]["step"] = "word_management_menu"
        sent_msg = bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id, "Меню керування словами:"), reply_markup=word_management_menu_keyboard(chat_id))
        safe_next_step_handler(sent_msg, handle_word_management_choice)
        
    except Exception as e:
        print(f"Error updating translation: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id) # Or word_management_menu_keyboard
        )
        clear_state(chat_id, preserve_dict_type=True) # Preserve dict type

# --- Bulk Delete Functions ---

def initiate_bulk_delete(message):
    """Start the process for bulk deleting words."""
    chat_id = message.chat.id
    current_state = {
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal"),
        "shared_dict_id": user_state.get(chat_id, {}).get("shared_dict_id")
    }
    # Запуск завантаження даних у окремому потоці
    executor.submit(_async_load_words_for_bulk_delete, chat_id, current_state, message)

def _async_load_words_for_bulk_delete(chat_id, state, message):
    """Асинхронно завантажує слова для масового видалення."""
    try:
        if chat_id not in user_state:
            user_state[chat_id] = {}
            
        # Preserve dict_type, clear other relevant states for bulk delete
        clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
        user_state[chat_id]["step"] = "bulk_deleting_words"
        user_state[chat_id]["bulk_delete_selected_ids"] = set()
        user_state[chat_id]['bulk_delete_current_page'] = 0
        user_state[chat_id]["dict_type"] = state["dict_type"]
        user_state[chat_id]["shared_dict_id"] = state["shared_dict_id"]
        
        dict_type = state["dict_type"]
        shared_dict_id = state["shared_dict_id"]
        
        # Завантаження даних з БД
        df = None
        if dict_type == "shared" and shared_dict_id:
            df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        if df is None or df.empty:
            dict_name_key = f"{dict_type}_dictionary" if dict_type != "common" else "common_dictionary"
            dict_name_text = get_text(dict_name_key, chat_id)
            bot.send_message(
                chat_id, 
                f"{get_text('in', chat_id)} {dict_name_text} {get_text('no_words_to_edit', chat_id)}", # Using existing no_words_to_edit
                reply_markup=word_management_menu_keyboard(chat_id)
            )
            safe_next_step_handler(message, handle_word_management_choice)
            return
            
        user_state[chat_id]["bulk_available_words_list"] = df.to_dict('records')
        show_bulk_delete_page(chat_id, message_to_edit=None)
            
    except Exception as e:
        print(f"Error in _async_load_words_for_bulk_delete for chat_id {chat_id}: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)

def show_bulk_delete_page(chat_id, message_to_edit=None):
    """Show a page of available words for bulk editing with pagination."""
    try:
        if chat_id not in user_state or "bulk_available_words_list" not in user_state[chat_id]:
            bot.send_message(chat_id, get_text("error_occurred", chat_id), reply_markup=word_management_menu_keyboard(chat_id))
            safe_next_step_handler(bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id), reply_markup=word_management_menu_keyboard(chat_id)), handle_word_management_choice)
            return

        all_words_list = user_state[chat_id]["bulk_available_words_list"]
        current_page = user_state[chat_id].get('bulk_delete_current_page', 0)
        selected_ids = user_state[chat_id].get("bulk_delete_selected_ids", set())

        start_index = current_page * WORDS_PER_PAGE_EDIT
        end_index = start_index + WORDS_PER_PAGE_EDIT
        words_to_show_list = all_words_list[start_index:end_index]

        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        
        temp_row_buttons = []
        for word_data in words_to_show_list:
            prefix = "✅ " if word_data['id'] in selected_ids else ""
            button_text = f"{prefix}{word_data['word'][:25]}" # Show only word, no translation
            button = telebot.types.InlineKeyboardButton(
                button_text,
                callback_data=f"bulk_toggle_{word_data['id']}"
            )
            temp_row_buttons.append(button)
            if len(temp_row_buttons) == 2:
                markup.row(*temp_row_buttons)
                temp_row_buttons = []
        if temp_row_buttons:
            markup.row(*temp_row_buttons)

        action_buttons_row = []
        if selected_ids:
            action_buttons_row.append(telebot.types.InlineKeyboardButton(
                f"🗑️ {get_text('delete_selected_words_button', chat_id, 'Видалити вибрані')}",
                callback_data="bulk_delete_selected_action"
            ))
        if action_buttons_row:
             markup.row(*action_buttons_row)

        pagination_buttons_row = []
        if current_page > 0:
            pagination_buttons_row.append(telebot.types.InlineKeyboardButton(
                f"🗑️ {get_text('previous_page_button', chat_id)}",
                callback_data="bulk_delete_prev_page"
            ))
        
        if end_index < len(all_words_list):
            pagination_buttons_row.append(telebot.types.InlineKeyboardButton(
                f"🗑️ {get_text('next_page_button', chat_id)}",
                callback_data="bulk_delete_next_page"
            ))
        
        if pagination_buttons_row:
            markup.row(*pagination_buttons_row)

        message_text = get_text("bulk_delete_prompt", chat_id, "Оберіть слова для видалення (натисніть для позначки):")
        if not all_words_list:
             message_text = get_text("no_words_to_edit", chat_id) # Re-use existing key

        if message_to_edit:
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_to_edit.message_id, text=message_text, reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass # Ignore if message content and markup are identical
                else:
                    print(f"Error editing message in show_bulk_delete_page: {e}")
                    # Fallback: send new message if edit fails for other reasons
                    sent_new_message = bot.send_message(chat_id, message_text, reply_markup=markup)
                    save_message_id(chat_id, sent_new_message.message_id)
        else:
            sent_message = bot.send_message(chat_id, message_text, reply_markup=markup)
            save_message_id(chat_id, sent_message.message_id)
            
    except Exception as e:
        print(f"Error in show_bulk_delete_page for chat_id {chat_id}: {e}")
        bot.send_message(chat_id, get_text("error_occurred", chat_id), reply_markup=word_management_menu_keyboard(chat_id))
        safe_next_step_handler(bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id), reply_markup=word_management_menu_keyboard(chat_id)), handle_word_management_choice)

def perform_bulk_delete(chat_id):
    """Deletes selected words and returns the count of deleted words."""
    if chat_id not in user_state or "bulk_delete_selected_ids" not in user_state[chat_id]:
        return 0
        
    selected_ids = user_state[chat_id]["bulk_delete_selected_ids"]
    if not selected_ids:
        return 0

    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    deleted_count = 0

    for word_id_to_delete in list(selected_ids): # Iterate over a copy
        success = False
        if dict_type == "shared" and shared_dict_id:
            success = db_manager.delete_word_from_shared_dict(chat_id, word_id_to_delete, shared_dict_id)
        else: # Personal or common (though common shouldn't be bulk-deletable by non-admins this way)
            success = db_manager.delete_word_from_personal_dict(chat_id, word_id_to_delete)
        if success:
            deleted_count += 1
    
    user_state[chat_id]["bulk_delete_selected_ids"] = set() # Clear selected IDs
    return deleted_count

def refresh_bulk_delete_word_list(chat_id):
    """Refreshes the list of available words for bulk deletion from the DB."""
    # Запускаємо в окремому потоці для уникнення блокування
    executor.submit(_async_refresh_bulk_delete_word_list, chat_id)

def _async_refresh_bulk_delete_word_list(chat_id):
    """Асинхронно оновлює список слів для масового видалення."""
    try:
        dict_type = user_state[chat_id].get("dict_type", "personal")
        shared_dict_id = user_state[chat_id].get("shared_dict_id")
        df_new = None
        
        if dict_type == "shared" and shared_dict_id:
            df_new = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
        else:
            df_new = db_manager.get_user_words(chat_id, dict_type)
        
        user_state[chat_id]["bulk_available_words_list"] = df_new.to_dict('records') if df_new is not None and not df_new.empty else []

        # Adjust current page if it's now out of bounds
        all_words_list_new = user_state[chat_id]["bulk_available_words_list"]
        current_page = user_state[chat_id].get('bulk_delete_current_page', 0)
        max_page = (len(all_words_list_new) - 1) // WORDS_PER_PAGE_EDIT
        if max_page < 0: max_page = 0 # Handle empty list
        if current_page > max_page:
            user_state[chat_id]['bulk_delete_current_page'] = max_page
            
    except Exception as e:
        print(f"Error in _async_refresh_bulk_delete_word_list for chat_id {chat_id}: {e}")
        # Не показуємо користувачеві помилку, оскільки ця функція викликається асинхронно

@bot.callback_query_handler(func=lambda call: call.data.startswith("bulk_toggle_"))
def handle_bulk_toggle_word(call):
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or user_state[chat_id].get("step") != "bulk_deleting_words":
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id))
            return

        word_id = int(call.data.replace("bulk_toggle_", ""))
        selected_ids = user_state[chat_id].get("bulk_delete_selected_ids", set())
        
        if word_id in selected_ids:
            selected_ids.remove(word_id)
        else:
            selected_ids.add(word_id)
        user_state[chat_id]["bulk_delete_selected_ids"] = selected_ids
        
        show_bulk_delete_page(chat_id, message_to_edit=call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_bulk_toggle_word: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))


@bot.callback_query_handler(func=lambda call: call.data in ["bulk_delete_prev_page", "bulk_delete_next_page"])
def handle_bulk_delete_and_paginate(call):
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or user_state[chat_id].get("step") != "bulk_deleting_words":
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id))
            return

        deleted_count = perform_bulk_delete(chat_id)
        if deleted_count > 0:
            bot.answer_callback_query(call.id, get_text("words_deleted_success_bulk_short", chat_id, f"{deleted_count} слів видалено."), show_alert=False)
        else:
            bot.answer_callback_query(call.id) # Acknowledge click even if no words were selected to delete

        refresh_bulk_delete_word_list(chat_id) # Refresh list from DB and adjust page

        current_page = user_state[chat_id].get('bulk_delete_current_page', 0)
        if call.data == "bulk_delete_prev_page":
            if current_page > 0:
                user_state[chat_id]['bulk_delete_current_page'] = current_page - 1
        elif call.data == "bulk_delete_next_page":
            all_words_list = user_state[chat_id]["bulk_available_words_list"]
            if (current_page + 1) * WORDS_PER_PAGE_EDIT < len(all_words_list):
                user_state[chat_id]['bulk_delete_current_page'] = current_page + 1
        
        show_bulk_delete_page(chat_id, message_to_edit=call.message)
        # No separate answer_callback_query here as it's handled above or by show_bulk_delete_page indirectly
    except Exception as e:
        print(f"Error in handle_bulk_delete_and_paginate: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))

@bot.callback_query_handler(func=lambda call: call.data == "bulk_delete_selected_action")
def handle_do_bulk_delete_selected(call):
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or user_state[chat_id].get("step") != "bulk_deleting_words":
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id))
            return

        if not user_state[chat_id].get("bulk_delete_selected_ids"):
            bot.answer_callback_query(call.id, get_text("no_words_selected_for_bulk_delete", chat_id, "Не вибрано слів для видалення."), show_alert=False)
            return

        deleted_count = perform_bulk_delete(chat_id)
        
        if deleted_count > 0:
            bot.answer_callback_query(call.id, get_text("words_deleted_success_bulk_short", chat_id, f"{deleted_count} слів видалено."), show_alert=True) # show_alert might be good here
        else:
            # This case should be caught by the check above, but as a fallback:
            bot.answer_callback_query(call.id, get_text("no_words_selected_for_bulk_delete", chat_id, "Не вибрано слів для видалення."), show_alert=False)

        refresh_bulk_delete_word_list(chat_id) # Refresh list from DB and adjust page
        show_bulk_delete_page(chat_id, message_to_edit=call.message)
    except Exception as e:
        print(f"Error in handle_do_bulk_delete_selected: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))

# --- End Bulk Delete Functions ---

# --- Bulk Add Words Functions ---

BULK_ADD_MAX_WORDS = 20

def bulk_add_reply_keyboard(chat_id):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(telebot.types.KeyboardButton(get_text("bulk_add_done_button_reply", chat_id, "Готово")))
    # Можна додати кнопку "Скасувати" для повернення до меню керування словами
    # keyboard.add(telebot.types.KeyboardButton(get_text("cancel_to_word_management", chat_id, "↩️ До меню слів")))
    return keyboard

def initiate_bulk_add_words(message):
    chat_id = message.chat.id
    # Перевірка прав на додавання слів до поточного типу словника
    current_dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    current_shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")

    can_add = True
    if current_dict_type == "shared":
        # Перевіряємо права адміна у окремому потоці, щоб не блокувати основний
        executor.submit(_async_check_admin_and_start_bulk_add, chat_id, current_dict_type, current_shared_dict_id, message)
        return
    elif current_dict_type == "common" and str(chat_id) != str(db_manager.ADMIN_ID): # Ensure ADMIN_ID is string for comparison if chat_id is string
        can_add = False
        bot.send_message(chat_id, get_text("add_word_common_not_admin", chat_id), reply_markup=word_management_menu_keyboard(chat_id))
        user_state[chat_id]["step"] = "word_management_menu"
        safe_next_step_handler(message, handle_word_management_choice)
        return
    
    if not can_add: # Подвійна перевірка, хоча вище вже є return
        return
        
    # Для персонального словника продовжуємо без додаткових перевірок
    _start_bulk_add_process(chat_id, message)

def _async_check_admin_and_start_bulk_add(chat_id, dict_type, shared_dict_id, message):
    """Асинхронно перевіряє права адміна для спільного словника."""
    try:
        can_add = True
        if dict_type == "shared":
            if not shared_dict_id or not db_manager.is_user_admin_of_shared_dict(chat_id, shared_dict_id):
                can_add = False
                bot.send_message(chat_id, get_text("add_word_shared_not_admin", chat_id), reply_markup=word_management_menu_keyboard(chat_id))
                # Повернення до меню керування словами
                user_state[chat_id]["step"] = "word_management_menu"
                safe_next_step_handler(message, handle_word_management_choice)
                return
                
        if can_add:
            _start_bulk_add_process(chat_id, message)
            
    except Exception as e:
        print(f"Error in _async_check_admin_and_start_bulk_add for chat_id {chat_id}: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=word_management_menu_keyboard(chat_id)
        )

def _start_bulk_add_process(chat_id, message):
    """Запускає процес масового додавання слів після перевірки прав."""
    if chat_id not in user_state: 
        user_state[chat_id] = {}
    
    # Очищаємо стан, зберігаючи тип словника
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=True)
    user_state[chat_id]["step"] = "bulk_add_awaiting_words"
    user_state[chat_id]["bulk_add_words_data"] = [] 
    user_state[chat_id]["bulk_add_active_word_index"] = None
    user_state[chat_id]["bulk_add_list_message_id"] = None
    user_state[chat_id]["bulk_add_confirm_message_id"] = None

    prompt_text = get_text("bulk_add_prompt_words", chat_id, 
                           f"Введіть слова для додавання (кожне з нового рядка, максимум {BULK_ADD_MAX_WORDS} слів).\nКоли закінчите, натисніть кнопку 'Готово' нижче.")
    
    sent_msg = bot.send_message(chat_id, prompt_text, reply_markup=bulk_add_reply_keyboard(chat_id))
    safe_next_step_handler(sent_msg, handle_bulk_words_input)


def handle_bulk_words_input(message):
    chat_id = message.chat.id
    user_text = message.text.strip()

    # Check for "Done" button
    if user_text == get_text("bulk_add_done_button_reply", chat_id):
        finalize_bulk_add(chat_id, "done_button_on_input")
        return
    
    words_input_list = [w.strip() for w in user_text.split('\n') if w.strip()]

    if not words_input_list:
        bot.send_message(chat_id, get_text("bulk_add_no_words_entered", chat_id, "Ви не ввели жодного слова. Спробуйте ще раз або натисніть 'Готово'."), reply_markup=bulk_add_reply_keyboard(chat_id))
        safe_next_step_handler(message, handle_bulk_words_input)
        return

    if len(words_input_list) > BULK_ADD_MAX_WORDS:
        words_input_list = words_input_list[:BULK_ADD_MAX_WORDS]
        bot.send_message(chat_id, get_text("bulk_add_word_limit_exceeded", chat_id, f"Прийнято перші {BULK_ADD_MAX_WORDS} слів. Інші проігноровано."))

    processing_msg = bot.send_message(chat_id, get_text("bulk_add_processing", chat_id, "Обробка слів..."))

    current_language = db_manager.get_user_language(chat_id)
    if not current_language:
        bot.send_message(chat_id, get_text("language_not_selected", chat_id, "Мова не вибрана. Будь ласка, почніть з /start"))
        try:
            bot.delete_message(chat_id, processing_msg.message_id)
        except Exception: pass
        finalize_bulk_add(chat_id, "language_error_on_input")
        return

    # Prepare data and batch translate
    words_to_translate = []
    words_data_pre_translation = []
    for word_text in words_input_list:
        article = None
        word_to_process = word_text
        parts = word_text.split(" ", 1)
        if len(parts) > 1 and parts[0].lower() in ["der", "die", "das"]:
            article = parts[0].lower()
            word_to_process = parts[1]
        words_to_translate.append(word_to_process)
        words_data_pre_translation.append({"original": word_text, "to_process": word_to_process, "article": article, "translation": ""})

    try:
        translated_objects = asyncio.run(translator.translate(words_to_translate, src='de', dest=current_language))
        for i, translated in enumerate(translated_objects):
            words_data_pre_translation[i]["translation"] = translated.text
    except Exception as e:
        print(f"Bulk add translation error: {e}")
        for info in words_data_pre_translation:
            info["translation"] = get_text("translation_failed_short", chat_id, "Помилка перекладу")

    # Process words one-by-one to get IDs for interactive editing
    bulk_add_data_list = []
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")

    for info in words_data_pre_translation:
        status = "error_adding"
        word_id = None
        
        # For shared dicts, we add to the main `words` table but don't link to a personal dict.
        add_word_dict_type = "personal" if dict_type == "personal" else "common"

        word_id = db_manager.add_word(
            chat_id, 
            info['to_process'], 
            info['translation'],
            dict_type=add_word_dict_type,
            article=info['article']
        )

        if word_id:
            if dict_type == "shared":
                if shared_dict_id:
                    # Link the word to the shared dictionary
                    success, _ = db_manager.add_word_to_shared_dictionary(chat_id, word_id, shared_dict_id)
                    if success:
                        status = "processed"
                # If it fails, status remains "error_adding"
            else:  # For personal or common dicts
                status = "processed"
        
        bulk_add_data_list.append({
            "original_word_text": info["original"],
            "word_for_db": info["to_process"],
            "article_for_db": info["article"],
            "translation": info["translation"],
            "status": status, 
            "id_in_db": word_id
        })

    user_state[chat_id]["bulk_add_words_data"] = bulk_add_data_list
    
    try:
        bot.delete_message(chat_id, processing_msg.message_id)
    except Exception:
        pass 
        
    user_state[chat_id]["step"] = "bulk_add_displaying_list"
    display_bulk_add_interactive_list(chat_id)


def display_bulk_add_interactive_list(chat_id, message_to_edit_id=None):
    if chat_id not in user_state or not user_state[chat_id].get("bulk_add_words_data"):
        # This might happen if input was empty and then "Готово" was pressed.
        # Or if an error occurred before data list was populated.
        finalize_bulk_add(chat_id, "no_data_to_display_in_list")
        return

    words_data_list = user_state[chat_id]["bulk_add_words_data"]
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for i, data_item in enumerate(words_data_list):
        text = ""
        callback = "bulk_add_noop" # Default for unclickable items
        
        if data_item["status"] == "processed":
            text = f"✅ {data_item['original_word_text']} - {data_item['translation']}"
            callback = f"bulk_edit_trans_prompt_{i}"
        elif data_item["status"] == "error_adding":
            text = f"❌ {data_item['original_word_text']} ({get_text('bulk_add_error_adding_short', chat_id, 'помилка додавання')})"
            # Make unclickable or allow retry? For now, unclickable.
        elif data_item["status"] == "error_updating": # New status for when edit fails
            text = f"⚠️ {data_item['original_word_text']} - {data_item['translation']} ({get_text('bulk_add_error_updating_short', chat_id, 'помилка оновлення')})"
            callback = f"bulk_edit_trans_prompt_{i}" # Allow to retry editing
        else: # Should not happen with new logic, but as a fallback
            text = f"❓ {data_item['original_word_text']}"

        if text:
             markup.add(telebot.types.InlineKeyboardButton(text, callback_data=callback))

    markup.add(telebot.types.InlineKeyboardButton(get_text("bulk_add_done_button_inline", chat_id, "Готово"), callback_data="bulk_add_finalize_now"))

    list_msg_text = get_text("bulk_add_list_prompt_edit", chat_id, "Слова додано. Натисніть на слово, щоб змінити переклад:")
    
    active_list_msg_id = user_state[chat_id].get("bulk_add_list_message_id")
    if active_list_msg_id:
        try:
            bot.edit_message_text(list_msg_text, chat_id, active_list_msg_id, reply_markup=markup, parse_mode="HTML")
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                # If modification failed for other reasons, send a new one
                sent_list_msg = bot.send_message(chat_id, list_msg_text, reply_markup=markup, parse_mode="HTML")
                user_state[chat_id]["bulk_add_list_message_id"] = sent_list_msg.message_id
                save_message_id(chat_id, sent_list_msg.message_id)
            # else: message not modified, do nothing
    else:
        sent_list_msg = bot.send_message(chat_id, list_msg_text, reply_markup=markup, parse_mode="HTML")
        user_state[chat_id]["bulk_add_list_message_id"] = sent_list_msg.message_id
        save_message_id(chat_id, sent_list_msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "bulk_add_noop")
def handle_bulk_add_noop(call):
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("bulk_edit_trans_prompt_"))
def handle_bulk_edit_translation_prompt(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or user_state[chat_id].get("step") not in ["bulk_add_displaying_list", "bulk_add_awaiting_manual_edit_translation"]:
        bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id))
        return

    idx = int(call.data.split("_")[-1])
    user_state[chat_id]["bulk_add_active_word_index"] = idx
    
    word_item_data = user_state[chat_id]["bulk_add_words_data"][idx]

    if word_item_data.get("id_in_db") is None and word_item_data["status"] != "error_updating": # Word wasn't added or no ID
        bot.answer_callback_query(call.id, get_text("bulk_add_word_not_added_cannot_edit", chat_id, "Це слово не було додано, редагування неможливе."), show_alert=True)
        return

    prompt_text = get_text("bulk_add_edit_translation_for_word_prompt", chat_id, 
                           "Введіть новий переклад для слова <b>{word}</b> (поточний: <b>{current_translation}</b>):"
                          ).format(word=word_item_data['original_word_text'], current_translation=word_item_data['translation'])
    
    cancel_mrkp = telebot.types.InlineKeyboardMarkup().add(
        telebot.types.InlineKeyboardButton(get_text("cancel", chat_id), callback_data=f"bulk_cancel_edit_trans_{idx}")
    )
    
    prev_confirm_msg_id = user_state[chat_id].get("bulk_add_confirm_message_id")
    if prev_confirm_msg_id:
        try:
            bot.delete_message(chat_id, prev_confirm_msg_id)
        except Exception: pass

    sent_confirm_msg = bot.send_message(chat_id, prompt_text, reply_markup=cancel_mrkp, parse_mode="HTML")
    user_state[chat_id]["bulk_add_confirm_message_id"] = sent_confirm_msg.message_id
    save_message_id(chat_id, sent_confirm_msg.message_id) # Save to allow clear_state to manage it if user navigates away

    user_state[chat_id]["step"] = "bulk_add_awaiting_manual_edit_translation"
    # Pass the sent_confirm_msg to safe_next_step_handler, as it's the one user replies to indirectly
    safe_next_step_handler(sent_confirm_msg, handle_bulk_manual_edit_translation_input) 
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("bulk_cancel_edit_trans_"))
def handle_bulk_cancel_edit_translation(call):
    chat_id = call.message.chat.id
    # idx = int(call.data.split("_")[-1]) # Not strictly needed if we just go back

    active_confirm_msg_id = user_state[chat_id].get("bulk_add_confirm_message_id")
    if active_confirm_msg_id:
        try:
            bot.delete_message(chat_id, active_confirm_msg_id)
            user_state[chat_id]["bulk_add_confirm_message_id"] = None
        except Exception: pass
    
    user_state[chat_id]["step"] = "bulk_add_displaying_list"
    display_bulk_add_interactive_list(chat_id) # Refresh the main list
    bot.answer_callback_query(call.id, get_text("cancelled", chat_id))


def handle_bulk_manual_edit_translation_input(message):
    chat_id = message.chat.id
    try:
        # Check for "Done" button or other commands
        if handle_exit_from_activity(message):
             # Clean up any pending confirmation messages
            active_confirm_msg_id = user_state.get(chat_id, {}).get("bulk_add_confirm_message_id")
            if active_confirm_msg_id:
                try:
                    bot.delete_message(chat_id, active_confirm_msg_id)
                except Exception:
                    pass
            finalize_bulk_add(chat_id, "exit_command_during_manual_edit")
            return

        # Validate state
        if chat_id not in user_state or user_state[chat_id].get("step") != "bulk_add_awaiting_manual_edit_translation":
            return

        idx = user_state[chat_id].get("bulk_add_active_word_index")
        if idx is None:
            finalize_bulk_add(chat_id, "error_no_active_idx_manual_edit")
            return

        new_translation = sanitize_user_input(message.text)
        if not new_translation:
            bot.send_message(chat_id, get_text("empty_translation_error", chat_id))
            # Re-register handler for the next message to allow user to try again
            safe_next_step_handler(message, handle_bulk_manual_edit_translation_input)
            return

        # Get the specific word data from state
        word_data = user_state[chat_id]["bulk_add_words_data"][idx]
        word_id = word_data.get("id_in_db")

        if not word_id:
            bot.send_message(chat_id, get_text("bulk_add_error_cannot_update_not_added", chat_id))
        else:
            # Update in DB
            dict_type = user_state[chat_id].get("dict_type", "personal")
            shared_dict_id = user_state[chat_id].get("shared_dict_id")
            success = False

            if dict_type == "shared":
                success = db_manager.update_word_translation_shared_dict(chat_id, word_id, new_translation, shared_dict_id)
            else:  # Handles "personal" and "common" (for admin)
                success = db_manager.update_word_translation_personal_dict(chat_id, word_id, new_translation)

            if success:
                # Update state and notify user
                user_state[chat_id]["bulk_add_words_data"][idx]["translation"] = new_translation
                user_state[chat_id]["bulk_add_words_data"][idx]["status"] = "processed"
                bot.send_message(chat_id, get_text("bulk_add_translation_updated", chat_id, "Переклад оновлено для <b>{word}</b>.").format(word=word_data["original_word_text"]), parse_mode="HTML")
            else:
                user_state[chat_id]["bulk_add_words_data"][idx]["status"] = "error_updating"
                bot.send_message(chat_id, get_text("bulk_add_error_updating_translation", chat_id, "Помилка оновлення перекладу для <b>{word}</b>.").format(word=word_data["original_word_text"]), parse_mode="HTML")

        # Clean up the prompt message for this specific edit
        active_confirm_msg_id = user_state.get(chat_id, {}).get("bulk_add_confirm_message_id")
        if active_confirm_msg_id:
            try:
                bot.delete_message(chat_id, active_confirm_msg_id)
                user_state[chat_id]["bulk_add_confirm_message_id"] = None
            except Exception:
                pass
        
        # Return to the interactive list view
        user_state[chat_id]["step"] = "bulk_add_displaying_list"
        display_bulk_add_interactive_list(chat_id)

    except Exception as e:
        print(f"Error in handle_bulk_manual_edit_translation_input for chat_id {chat_id}: {e}")
        bot.send_message(chat_id, get_text("error_occurred", chat_id))
        finalize_bulk_add(chat_id, "exception_in_manual_edit")


@bot.callback_query_handler(func=lambda call: call.data.startswith("bulk_add_start_confirm_"))
def handle_bulk_add_start_confirm(call): # This function is no longer used with the new logic, can be removed
    # Keeping it to prevent errors if old callbacks are somehow triggered.
    # Or, better, remove it and its sub-handlers.
    bot.answer_callback_query(call.id, "This action is outdated.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "bulk_add_finalize_now")
def handle_bulk_add_finalize_now(call):
    chat_id = call.message.chat.id
    active_confirm_msg_id = user_state[chat_id].get("bulk_add_confirm_message_id")
    if active_confirm_msg_id:
        try:
            bot.delete_message(chat_id, active_confirm_msg_id)
            user_state[chat_id]["bulk_add_confirm_message_id"] = None
        except Exception: pass
    
    finalize_bulk_add(chat_id, "finalize_button_from_list_callback")
    bot.answer_callback_query(call.id)

def finalize_bulk_add(chat_id, reason="unknown"):
    print(f"Finalizing bulk add for {chat_id}, reason: {reason}")
    added_count = 0
    skipped_count = 0
    error_count = 0
    
    words_data = user_state.get(chat_id, {}).get("bulk_add_words_data", [])
    for item_data in words_data:
        if item_data["status"] == "processed":
            added_count += 1
        elif item_data["status"] == "skipped":
            skipped_count += 1
        elif item_data["status"] == "error_adding":
            error_count +=1
    
    summary_text = get_text("bulk_add_summary", chat_id, 
                            f"Масове додавання завершено.\nДодано: {added_count}\nПропущено: {skipped_count}\nПомилки: {error_count}")
    bot.send_message(chat_id, summary_text, reply_markup=word_management_menu_keyboard(chat_id)) # Send with word management keyboard

    active_list_msg_id = user_state.get(chat_id, {}).get("bulk_add_list_message_id")
    if active_list_msg_id:
        try:
            bot.edit_message_reply_markup(chat_id, active_list_msg_id, reply_markup=None)
        except Exception: pass
    
    # Clear bulk_add specific keys from user_state
    if chat_id in user_state:
        keys_to_remove = [k for k in user_state[chat_id] if k.startswith("bulk_add_")]
        for key_to_remove in keys_to_remove:
            del user_state[chat_id][key_to_remove]
    
    user_state[chat_id]["step"] = "word_management_menu" 
    # The word_management_menu_keyboard is a reply keyboard, 
    # so next choice will be handled by handle_word_management_choice via message handler.
    # No explicit safe_next_step_handler needed here if we send the menu with reply keyboard.
    # However, to be consistent with other parts:
    # Re-send prompt for word management menu to attach next_step_handler
    sent_menu_msg = bot.send_message(chat_id, get_text("word_management_menu_prompt", chat_id), reply_markup=word_management_menu_keyboard(chat_id))
    safe_next_step_handler(sent_menu_msg, handle_word_management_choice)


# --- End Bulk Add Words Functions ---

@bot.callback_query_handler(func=lambda call: call.data == "edit_page_prev")
def handle_edit_prev_page(call):
    """Handle 'Previous Page' for word editing selection."""
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or "available_words_list" not in user_state[chat_id]:
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id, "Сесія застаріла, спробуйте знову."))
            return

        current_page = user_state[chat_id].get('edit_current_page', 0)
        if current_page > 0:
            user_state[chat_id]['edit_current_page'] = current_page - 1
            show_word_selection_page(chat_id, message_to_edit=call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_prev_page: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))

@bot.callback_query_handler(func=lambda call: call.data == "edit_page_next")
def handle_edit_next_page(call):
    """Handle 'Next Page' for word editing selection."""
    try:
        chat_id = call.message.chat.id
        if chat_id not in user_state or "available_words_list" not in user_state[chat_id]:
            bot.answer_callback_query(call.id, get_text("error_session_expired", chat_id, "Сесія застаріла, спробуйте знову."))
            return

        current_page = user_state[chat_id].get('edit_current_page', 0)
        all_words_list = user_state[chat_id]["available_words_list"]
        if (current_page + 1) * WORDS_PER_PAGE_EDIT < len(all_words_list):
            user_state[chat_id]['edit_current_page'] = current_page + 1
            show_word_selection_page(chat_id, message_to_edit=call.message)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error in handle_edit_next_page: {e}")
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_word_"))
def handle_word_selection_for_edit(call):
    """Handle word selection for editing"""
    chat_id = call.message.chat.id
    word_id = int(call.data.replace("edit_word_", ""))
    
    if chat_id not in user_state or user_state[chat_id].get("step") != "selecting_word_to_edit":
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    # Find selected word in available words
    available_words_list = user_state[chat_id].get("available_words_list", [])
    selected_word = next((word for word in available_words_list if word['id'] == word_id), None)
    
    if not selected_word:
        bot.answer_callback_query(call.id, get_text("error_occurred", chat_id))
        return
    
    # Update user state
    user_state[chat_id].update({
        "step": "editing_word",
        "selected_word": selected_word,
        "edit_mode": "choose_action"
    })
    
    # Show edit options
    show_edit_options(call.message, selected_word)
