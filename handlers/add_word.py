# -*- coding: utf-8 -*-

"""
Обробники для додавання нових слів.
"""

import telebot
from config import bot, user_state, translator, ADMIN_ID
from utils import clear_state, main_menu_keyboard, main_menu_cancel
from storage import get_user_file_path
from dictionary import save_word

@bot.message_handler(func=lambda message: message.text == "➕ Додати нове слово")
def add_word(message):
    clear_state(message.chat.id)
    bot.send_message(message.chat.id, "Введіть слово, яке хочете додати:", reply_markup=main_menu_cancel())
    user_state[message.chat.id] = {
        "step": "adding_word",
        "dict_type": user_state.get(message.chat.id, {}).get("dict_type", "personal")
    }

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "adding_word")
def handle_translation(message):
    """Handle word input for translation"""
    chat_id = message.chat.id
    
    # Спеціальна обробка для команди "Відміна"
    if message.text == "Відміна" or message.text == "✖️ Відміна":
        clear_state(chat_id)
        bot.send_message(chat_id, "🚫 Дію скасовано.", 
                       reply_markup=main_menu_keyboard(chat_id))
        return
        
    if not message.text or message.text.startswith('/'):
        bot.send_message(chat_id, "❌ Будь ласка, введіть слово текстом!")
        return
        
    # Check if the text is a command
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(chat_id, "❌ Будь ласка, введіть нове слово, а не команду.")
        return
        
    word = message.text.strip()
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Check permissions for common dictionary
    if dict_type == "common" and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ Тільки адміністратор може додавати слова до загального словника!", 
                        reply_markup=main_menu_keyboard(chat_id))
        clear_state(chat_id)
        return
    
    if dict_type == "personal":
        file_path, language = get_user_file_path(chat_id)
        if not file_path:
            bot.send_message(chat_id, "❌ Мову перекладу не обрано. Спробуйте /start.")
            return
    else:
        from storage import get_common_file_path
        _, language = get_common_file_path()
    
    translation = translator.translate(word, src="de", dest=language).text
    
    if translation:
        # Update user state with translation data
        user_state[chat_id].update({
            "step": "confirm_translation",
            "word": word,
            "auto_translation": translation,
            "language": language
        })
        
        # Create confirmation keyboard with emojis
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("✅ Так", "❌ Ні", "✖️ Відміна")  # Додаємо емодзі для кращої візуалізації
        bot.send_message(chat_id, f"Знайдено переклад: {translation}. Це правильно?", reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "Не вдалося перекласти слово. Спробуйте ще раз.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "confirm_translation")
def handle_confirmation(message):
    """Handle translation confirmation"""
    chat_id = message.chat.id
    
    try:
        if message.text == "✅ Так" or message.text == "Так":
            save_word(chat_id)
            bot.send_message(chat_id, "✅ Слово успішно додано!", 
                            reply_markup=main_menu_keyboard(chat_id))
        elif message.text == "❌ Ні" or message.text == "Ні":
            bot.send_message(chat_id, "Введіть правильний переклад вручну:", 
                           reply_markup=main_menu_cancel())
            user_state[chat_id]["step"] = "manual_translation"
        elif message.text == "✖️ Відміна" or message.text == "Відміна":
            clear_state(chat_id)
            bot.send_message(chat_id, "🚫 Дію скасовано.", 
                           reply_markup=main_menu_keyboard(chat_id))
        else:
            bot.send_message(chat_id, "❌ Будь ласка, виберіть '✅ Так', '❌ Ні' або '✖️ Відміна'.")
    except Exception as e:
        print(f"Error in handle_confirmation: {e}")
        clear_state(chat_id)
        bot.send_message(chat_id, "❌ Помилка при обробці підтвердження.", 
                       reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "manual_translation")
def handle_manual_translation(message):
    """Handle manual translation input"""
    chat_id = message.chat.id
    
    try:
        # Обробка команди "Відміна"
        if message.text == "✖️ Відміна" or message.text == "Відміна":
            clear_state(chat_id)
            bot.send_message(chat_id, "🚫 Дію скасовано.", 
                           reply_markup=main_menu_keyboard(chat_id))
            return
        
        # Перевіряємо, чи не є введений текст системною командою
        if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", 
                          "✅ Так", "❌ Ні", "✖️ Відміна"]:
            bot.send_message(chat_id, "❌ Будь ласка, введіть правильний переклад, а не команду.")
            return
        
        save_word(chat_id, message.text.strip())
        bot.send_message(chat_id, "✅ Слово успішно додано з вашим перекладом!", 
                        reply_markup=main_menu_keyboard(chat_id))
    except Exception as e:
        print(f"Error in handle_manual_translation: {e}")
        clear_state(chat_id)
        bot.send_message(chat_id, "❌ Помилка при збереженні перекладу.", 
                       reply_markup=main_menu_keyboard(chat_id))
