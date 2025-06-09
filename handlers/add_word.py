# -*- coding: utf-8 -*-

"""
Обробники для додавання нових слів.
"""

import telebot
from config import bot, user_state, translator, ADMIN_ID
from utils import clear_state, main_menu_keyboard, main_menu_cancel
from utils.state_helpers import save_message_id
from storage import get_user_file_path
from dictionary import save_word
from utils.language_utils import get_text
from utils.input_handlers import is_system_command, safe_next_step_handler, sanitize_user_input
from utils.logger import log_handler, log_action, extract_user_info
from utils.bot_utils import send_message_with_logging

@bot.message_handler(func=lambda message: message.text == get_text("add_new_word", message.chat.id) or message.text == "➕ Додати нове слово")
@log_handler
def add_word(message):
    """Start process of adding a new word"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Використовуємо логування з функцією з модуля logger
    log_action("add_word_started", {"chat_id": chat_id}, extract_user_info(message))
    
    # Використовуємо функцію з логуванням
    sent_message = send_message_with_logging(
        chat_id, 
        get_text("add_word_prompt", chat_id, "Введіть слово, яке хочете додати:"), 
        reply_markup=main_menu_cancel(chat_id)
    )
    save_message_id(chat_id, sent_message.message_id)
    
    user_state[chat_id] = {
        "step": "adding_word",
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal")
    }
    
    safe_next_step_handler(sent_message, handle_translation)

# Оновлення інших обробників аналогічним чином
@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "adding_word")
def handle_translation(message):
    """Handle word input for translation"""
    chat_id = message.chat.id

    # Заборона на введення команд
    if is_system_command(message):
        bot.send_message(chat_id, get_text("enter_word_error", chat_id, "❌ Будь ласка, введіть слово текстом!"))
        safe_next_step_handler(message, handle_translation)
        return

    # Очищення та перевірка вводу користувача
    word = sanitize_user_input(message.text.strip(), max_length=50)
    if not word:
        bot.send_message(chat_id, get_text("empty_word_error", chat_id, "❌ Будь ласка, введіть непорожнє слово!"))
        safe_next_step_handler(message, handle_translation)
        return
        
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")

    # Check permissions for common dictionary
    if dict_type == "common" and chat_id != ADMIN_ID:
        bot.send_message(
            chat_id, 
            get_text("admin_only_error", chat_id, "❌ Тільки адміністратор може додавати слова до загального словника!"), 
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)
        return

    try:
        # Отримання мови перекладу
        language = "uk"  # Default
        if dict_type == "personal":
            file_path, language = get_user_file_path(chat_id)
            if not file_path:
                bot.send_message(chat_id, get_text("language_not_selected", chat_id, "❌ Мову перекладу не обрано. Спробуйте /start."))
                return
        else:
            from storage import get_common_file_path
            _, language = get_common_file_path()

        # Отримання перекладу
        translation = translator.translate(word, src="de", dest=language).text

        if translation:
            user_state[chat_id].update({
                "step": "confirm_translation",
                "word": word,
                "auto_translation": translation,
                "language": language
            })
            keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            # Використовуємо локалізовані кнопки
            yes_text = "✅ " + get_text("yes", chat_id, "Так")
            no_text = "❌ " + get_text("no", chat_id, "Ні")
            cancel_text = get_text("cancel", chat_id, "✖️ Відміна")
            keyboard.add(yes_text, no_text)
            keyboard.row(cancel_text)
            
            message = bot.send_message(
                chat_id, 
                get_text("found_translation_confirm", chat_id) + 
                f"{translation}" + 
                get_text("translation_confirm", chat_id), 
                reply_markup=keyboard
            )
            save_message_id(chat_id, message.message_id)
        else:
            bot.send_message(chat_id, get_text("translation_failed", chat_id))
            safe_next_step_handler(message, handle_translation)
            
    except Exception as e:
        print(f"Error in handle_translation: {e}")
        bot.send_message(
            chat_id, 
            get_text("error_occurred", chat_id),
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "confirm_translation")
def handle_confirmation(message):
    """Handle translation confirmation"""
    chat_id = message.chat.id

    try:
        if message.text in ["✅ Так", "Так"]:
            save_word(chat_id)
            bot.send_message(
                chat_id, 
                get_text("word_added_simple", chat_id), 
                reply_markup=main_menu_keyboard(chat_id)
            )
            clear_state(chat_id, preserve_dict_type=True)
            
        elif message.text in ["❌ Ні", "Ні"]:
            sent_message = bot.send_message(
                chat_id, 
                get_text("enter_translation_manually", chat_id), 
                reply_markup=main_menu_cancel()
            )
            save_message_id(chat_id, sent_message.message_id)
            user_state[chat_id]["step"] = "manual_translation"
            
            # Використовуємо безпечний обробник для наступного кроку
            safe_next_step_handler(sent_message, handle_manual_translation)
            
        elif message.text in ["✖️ Відміна", "Відміна"]:
            clear_state(chat_id)
            bot.send_message(
                chat_id, 
                get_text("cancelled", chat_id), 
                reply_markup=main_menu_keyboard(chat_id)
            )
        else:
            bot.send_message(chat_id, get_text("choose_yes_no_cancel", chat_id))
            
    except Exception as e:
        print(f"Error in handle_confirmation: {e}")
        clear_state(chat_id)
        bot.send_message(
            chat_id, 
            get_text("confirmation_processing_error", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "manual_translation")
def handle_manual_translation(message):
    """Handle manual translation input"""
    chat_id = message.chat.id

    # Заборона на введення команд
    if is_system_command(message):
        bot.send_message(chat_id, get_text("invalid_translation_input", chat_id))
        # Повторно реєструємо обробник
        safe_next_step_handler(message, handle_manual_translation)
        return

    try:
        # Очищення вводу
        translation = sanitize_user_input(message.text.strip())
        
        # Збереження слова з вказаним користувачем перекладом
        save_word(chat_id, translation)
        
        # Повідомлення про успіх
        bot.send_message(
            chat_id, 
            get_text("word_added_success", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id, preserve_dict_type=True)
        
    except Exception as e:
        print(f"Error in handle_manual_translation: {e}")
        clear_state(chat_id)
        bot.send_message(
            chat_id, 
            get_text("translation_save_error", chat_id), 
            reply_markup=main_menu_keyboard(chat_id)
        )
