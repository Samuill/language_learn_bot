# -*- coding: utf-8 -*-
import random
import telebot
import pandas as pd
from config import bot, translator, user_state, ADMIN_ID
from utils import clear_state, track_activity, main_menu_keyboard, main_menu_cancel, language_selection_keyboard
from storage import get_dataframe, save_dataframe, get_user_file_path
from dictionary import save_word, toggle_dictionary, start_activity

def start_learning(chat_id, df):
    """Start learning new words activity"""
    df = df.sort_values(by="priority", ascending=False)
    words = df.sample(min(10, len(df)))
    
    translations = words['translation'].tolist()
    de_words = words['word'].tolist()
    random.shuffle(translations)
    random.shuffle(de_words)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for tr, de in zip(translations, de_words):
        markup.add(
            telebot.types.InlineKeyboardButton(tr, callback_data=f'tr_{tr}'),
            telebot.types.InlineKeyboardButton(de, callback_data=f'de_{de}')
        )
    
    user_state[chat_id] = {
        "pairs": list(zip(words['translation'], words['word'])),
        "selected_tr": None,
        "message_id": None,
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal")
    }
    
    sent_message = bot.send_message(chat_id, "🔍 Оберіть пару слів:", reply_markup=markup)
    user_state[chat_id]["message_id"] = sent_message.message_id
    return True

def start_repetition(chat_id, df):
    """Start repetition activity"""
    word = df.sample(1).iloc[0]
    sample_size = min(4, len(df))  # Changed from 3 to 4
    translations = df['translation'].sample(sample_size).tolist()
    if word['translation'] not in translations:
        translations[0] = word['translation']
    random.shuffle(translations)
    
    markup = telebot.types.InlineKeyboardMarkup()
    for tr in translations:
        markup.add(telebot.types.InlineKeyboardButton(
            tr, 
            callback_data=f"ans_{word['word']}_{tr}"
        ))
    
    sent_message = bot.send_message(chat_id, f"📖 Оберіть переклад для слова: {word['word']}", reply_markup=markup)
    user_state[chat_id] = {
        "current_word": word,
        "message_id": sent_message.message_id,
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal")
    }
    return True

# Command handlers
@bot.message_handler(commands=["start"])
def main_menu(message):
    clear_state(message.chat.id)
    file_path, language = get_user_file_path(message.chat.id)
    track_activity(message.chat.id)
    
    if not file_path:
        # If file doesn't exist, offer language selection
        bot.send_message(message.chat.id, "🌍 Виберіть мову, на якій бажаєте отримувати переклад слів:", 
                         reply_markup=language_selection_keyboard())
        user_state[message.chat.id] = {"step": "language_selection"}
    else:
        # If file exists, show main menu
        bot.send_message(message.chat.id, "Оберіть дію:", 
                         reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: message.text in ["🇺🇦 Українська", "🇷🇺 Російська"])
def handle_language_selection(message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("step") == "language_selection":
        language = "uk" if message.text == "🇺🇦 Українська" else "ru"
        
        # Create empty dictionary for user
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        save_dataframe(chat_id, df, language)
        
        bot.send_message(chat_id, f"✅ Мову перекладу обрано: {message.text}. Тепер ви можете додавати слова та вивчати їх.", 
                         reply_markup=main_menu_keyboard(chat_id))
        clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "➕ Додати нове слово")
def add_word(message):
    clear_state(message.chat.id)
    bot.send_message(message.chat.id, "Введіть слово, яке хочете додати:", reply_markup=main_menu_cancel())
    user_state[message.chat.id] = {
        "step": "adding_word",
        "dict_type": user_state.get(message.chat.id, {}).get("dict_type", "personal")
    }

@bot.message_handler(func=lambda message: message.text == "Відміна")
def cancel_action(message):
    clear_state(message.chat.id)
    bot.send_message(message.chat.id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "adding_word")
def handle_translation(message):
    if not message.text or message.text.startswith('/'):
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть слово текстом!")
        return
        
    # Check if the text is a command
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть нове слово, а не команду.")
        return
        
    word = message.text.strip()
    dict_type = user_state.get(message.chat.id, {}).get("dict_type", "personal")
    
    # Check permissions for common dictionary
    if dict_type == "common" and message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Тільки адміністратор може додавати слова до загального словника!", 
                        reply_markup=main_menu_keyboard(message.chat.id))
        clear_state(message.chat.id)
        return
    
    # Use a proper language code (default to Ukrainian for common dict)
    if dict_type == "personal":
        file_path, language = get_user_file_path(message.chat.id)
        if not file_path:
            bot.send_message(message.chat.id, "❌ Мову перекладу не обрано. Спробуйте /start.")
            return
    else:
        language = "uk"  # Default language for common dictionary
    
    translation = translator.translate(word, src="de", dest=language).text
    
    if translation:
        user_state[message.chat.id].update({
            "step": "confirm_translation",
            "word": word,
            "auto_translation": translation
        })
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("Так", "Ні","Відміна")
        bot.send_message(message.chat.id, f"Знайдено переклад: {translation}. Це правильно?", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Не вдалося перекласти слово. Спробуйте ще раз.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "confirm_translation")
def handle_confirmation(message):
    if message.text == "Так":
        save_word(message.chat.id)
        bot.send_message(message.chat.id, "✅ Слово успішно додано!", 
                        reply_markup=main_menu_keyboard(message.chat.id))
    elif message.text == "Ні":
        bot.send_message(message.chat.id, "Введіть правильний переклад вручну:", 
                        reply_markup=telebot.types.ReplyKeyboardRemove())
        user_state[message.chat.id]["step"] = "manual_translation"
    elif message.text == "Відміна":
        clear_state(message.chat.id)
        bot.send_message(message.chat.id, "🚫 Дію скасовано.", 
                        reply_markup=main_menu_keyboard(message.chat.id))
    else:
        bot.send_message(message.chat.id, "❌ Будь ласка, виберіть 'Так', 'Ні' або 'Відміна'.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "manual_translation")
def handle_manual_translation(message):
    # Check if input is a command
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть правильний переклад, а не команду.")
        return
    
    save_word(message.chat.id, message.text.strip())
    bot.send_message(message.chat.id, "✅ Слово успішно додано з вашим перекладом!", 
                    reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: message.text == "📖 Вчити нові слова")
def learn_words(message):
    start_activity(message.chat.id, 'learn')

@bot.message_handler(func=lambda message: message.text == "🔄 Повторити")
def repeat_words(message):
    start_activity(message.chat.id, 'repeat')

@bot.message_handler(func=lambda message: message.text in ["🌐 Загальний словник", "👤 Персональний словник"])
def switch_dictionary(message):
    toggle_dictionary(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('tr_', 'de_')))
def handle_pairs(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or "pairs" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вчити нові слова'")
        return
    
    state = user_state[chat_id]
    
    # Immediate response for better UX
    if call.data.startswith('tr_'):
        selected_tr = call.data[3:]
        if state.get('selected_tr'):
            bot.answer_callback_query(call.id, "⏳ Спочатку завершіть поточний вибір")
            return
        state['selected_tr'] = selected_tr
        bot.answer_callback_query(call.id, f"Обрано: {selected_tr}", cache_time=1)
        return
    
    elif call.data.startswith('de_'):
        if not state.get('selected_tr'):
            bot.answer_callback_query(call.id, "❗ Спочатку оберіть переклад")
            return
        
        selected_de = call.data[3:]
        correct = any(tr == state['selected_tr'] and de == selected_de for tr, de in state["pairs"])
        
        # Process result
        if correct:
            bot.answer_callback_query(call.id, "✅ Правильно!", cache_time=1)
            
            # Update UI first for responsiveness
            markup = call.message.reply_markup
            for row in markup.keyboard:
                for btn in row:
                    if btn.callback_data in [f'tr_{state["selected_tr"]}', f'de_{selected_de}']:
                        btn.text += " ✅"
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
            
            # Track progress
            if "found_pairs" not in state:
                state["found_pairs"] = []
            state["found_pairs"].append((state['selected_tr'], selected_de))
            
            # Get dataframe and update priority (defer intensive operations)
            df = get_dataframe(chat_id)
            df.loc[df['translation'] == state['selected_tr'], 'priority'] -= 0.001
            
            # Check if finished all pairs
            if len(state["found_pairs"]) == len(state["pairs"]):
                bot.delete_message(chat_id, call.message.message_id)
                learn_words(call.message)
            else:
                # Save dataframe and reset selection state
                file_path, lang = get_user_file_path(chat_id) if state["dict_type"] == "personal" else (None, None)
                save_dataframe(chat_id, df, lang if lang else "common")
                state['selected_tr'] = None
        else:
            bot.answer_callback_query(call.id, "❌ Неправильно!", cache_time=1)
            df = get_dataframe(chat_id)
            df.loc[df['translation'] == state['selected_tr'], 'priority'] += 0.001
            file_path, lang = get_user_file_path(chat_id) if state["dict_type"] == "personal" else (None, None)
            save_dataframe(chat_id, df, lang if lang else "common")
            state['selected_tr'] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_answer(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Повторити'")
        return
    
    _, word, selected_tr = call.data.split('_')
    correct_tr = user_state[chat_id]["current_word"]['translation']
    
    df = get_dataframe(chat_id)
    if selected_tr == correct_tr:
        bot.answer_callback_query(call.id, "✅ Правильно!")
        df.loc[df['word'] == word, 'priority'] -= 0.001
        bot.delete_message(chat_id, call.message.message_id)
        repeat_words(call.message)
    else:
        bot.answer_callback_query(call.id, f"❌ Неправильно! Правильно: {correct_tr}")
        df.loc[df['word'] == word, 'priority'] += 0.001
        markup = call.message.reply_markup
        for row in markup.keyboard:
            if row[0].callback_data == call.data:
                row[0].text += " ❌"
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
    
    file_path, lang = get_user_file_path(chat_id) if user_state[chat_id].get("dict_type") == "personal" else (None, None)
    save_dataframe(chat_id, df, lang if lang else "common")

@bot.message_handler(commands=['fire'])
def test_fire(message):
    if message.from_user.id == ADMIN_ID:
        try:
            from scheduler import send_reminder
            send_reminder()
            bot.reply_to(message, "Нагадування відправлено!")
        except Exception as e:
            print(f"Помилка в /fire: {e}")
            bot.reply_to(message, f"Помилка: {str(e)}")

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    if message.from_user.id == ADMIN_ID:
        bot.stop_polling()
        scheduler.shutdown(wait=False)
        print("Бот зупинено!")
        exit(0)
