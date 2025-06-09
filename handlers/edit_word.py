# -*- coding: utf-8 -*-

"""
Обробники для редагування слів у словнику.
"""

import telebot
from config import bot, user_state
from utils import clear_state, main_menu_keyboard, main_menu_cancel
from utils.state_helpers import save_message_id
from utils.language_utils import get_text
from utils.input_handlers import safe_next_step_handler, sanitize_user_input, is_system_command
import db_manager

@bot.message_handler(func=lambda message: message.text == get_text("edit_word", message.chat.id) or message.text == "✏️ Редагувати слово")
def edit_word_start(message):
    """Start word editing process"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Get current dictionary type
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    
    # Check if user has words to edit
    try:
        if dict_type == "shared" and shared_dict_id:
            df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        if df is None or df.empty:
            dict_name = get_text("shared_dictionary", chat_id) if dict_type == "shared" else get_text("personal_dictionary", chat_id)
            bot.send_message(
                chat_id, 
                get_text("in", chat_id) + dict_name + get_text("no_words", chat_id),
                reply_markup=main_menu_keyboard(chat_id)
            )
            return
        
        # Set user state for word editing
        user_state[chat_id] = {
            "step": "selecting_word_to_edit",
            "dict_type": dict_type,
            "available_words": df.to_dict('records')
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Show word selection
        show_word_selection(chat_id, df)
        
    except Exception as e:
        print(f"Error in edit_word_start: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )

def show_word_selection(chat_id, df):
    """Show available words for editing"""
    # Create inline keyboard with words (max 10 per page)
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    words_to_show = df.head(20)  # Show first 20 words
    
    for _, word_row in words_to_show.iterrows():
        word = word_row['word']
        translation = word_row['translation']
        button_text = f"{word} - {translation[:15]}{'...' if len(translation) > 15 else ''}"
        markup.add(telebot.types.InlineKeyboardButton(
            button_text,
            callback_data=f"edit_word_{word_row['id']}"
        ))
    
    sent_message = bot.send_message(
        chat_id,
        get_text("select_word_to_edit", chat_id, "Оберіть слово для редагування:"),
        reply_markup=markup
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_word_"))
def handle_word_selection_for_edit(call):
    """Handle word selection for editing"""
    chat_id = call.message.chat.id
    word_id = int(call.data.replace("edit_word_", ""))
    
    if chat_id not in user_state or user_state[chat_id].get("step") != "selecting_word_to_edit":
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    # Find selected word in available words
    available_words = user_state[chat_id]["available_words"]
    selected_word = next((word for word in available_words if word['id'] == word_id), None)
    
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
    chat_id = call.message.chat.id
    
    if chat_id not in user_state or user_state[chat_id].get("step") != "editing_word":
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    if call.data == "cancel_edit":
        clear_state(chat_id)
        bot.edit_message_text(
            get_text("cancelled", chat_id),
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        bot.send_message(chat_id, get_text("main_menu", chat_id), reply_markup=main_menu_keyboard(chat_id))
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

@bot.callback_query_handler(func=lambda call: call.data in ["confirm_delete", "cancel_delete"])
def handle_delete_confirmation(call):
    """Handle word deletion confirmation"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_state or user_state[chat_id].get("step") != "editing_word":
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    if call.data == "cancel_delete":
        # Go back to edit options
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
            
            clear_state(chat_id)
            bot.send_message(chat_id, get_text("main_menu", chat_id), reply_markup=main_menu_keyboard(chat_id))
            
        except Exception as e:
            print(f"Error deleting word: {e}")
            bot.edit_message_text(
                get_text("error_occurred", chat_id),
                chat_id=chat_id,
                message_id=call.message.message_id
            )

def handle_new_translation(message):
    """Handle new translation input"""
    chat_id = message.chat.id
    
    if is_system_command(message):
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
        
        clear_state(chat_id)
        
    except Exception as e:
        print(f"Error updating translation: {e}")
        bot.send_message(
            chat_id,
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)
