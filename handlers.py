# -*- coding: utf-8 -*-
import random
import telebot
import pandas as pd
import os
from config import bot, translator, user_state, ADMIN_ID, DEBUG_MODE
from utils import clear_state, track_activity, main_menu_keyboard, main_menu_cancel, language_selection_keyboard
from storage import get_dataframe, save_dataframe, get_user_file_path, get_common_file_path
from dictionary import save_word, toggle_dictionary, start_activity

# Import debug logger if debug mode is enabled
if DEBUG_MODE:
    from debug_logger import log_handler, log_message, log_response, log_error

def start_learning(chat_id, df):
    """Start learning new words activity"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: start_learning for user {chat_id}, dict_type={dict_type}")
    
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
        "dict_type": dict_type
    }
    
    sent_message = bot.send_message(chat_id, "🔍 Оберіть пару слів:", reply_markup=markup)
    user_state[chat_id]["message_id"] = sent_message.message_id
    return True

def start_repetition(chat_id, df):
    """Start repetition activity"""
    if df is None or len(df) < 1:
        bot.send_message(chat_id, "📭 У словнику немає слів для повторення.")
        return False
        
    try:
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        
        word = df.sample(1).iloc[0]
        sample_size = min(3, len(df))
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
            "dict_type": dict_type
        }
        return True
    except Exception as e:
        print(f"Error in start_repetition: {e}")
        bot.send_message(chat_id, "❌ Помилка при запуску повторення.")
        return False

@bot.message_handler(commands=["start"])
@log_handler
def main_menu(message):
    clear_state(message.chat.id)
    file_path, language = get_user_file_path(message.chat.id)
    track_activity(message.chat.id)
    
    if not file_path:
        bot.send_message(message.chat.id, "🌍 Виберіть мову, на якій бажаєте отримувати переклад слів:", 
                         reply_markup=language_selection_keyboard())
        user_state[message.chat.id] = {"step": "language_selection"}
    else:
        bot.send_message(message.chat.id, "Оберіть дію:", 
                         reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: message.text in ["🇺🇦 Українська", "🇷🇺 Російська"])
@log_handler
def handle_language_selection(message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("step") == "language_selection":
        language = "uk" if message.text == "🇺🇦 Українська" else "ru"
        
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        save_dataframe(chat_id, df, language)
        
        bot.send_message(chat_id, f"✅ Мову перекладу обрано: {message.text}. Тепер ви можете додавати слова та вивчати їх.", 
                         reply_markup=main_menu_keyboard(chat_id))
        clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "➕ Додати нове слово")
@log_handler
def add_word(message):
    chat_id = message.chat.id
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: Add word request from user {chat_id}, dict_type={dict_type}")
    
    # Для звичайних користувачів перевіряємо право на додавання в загальний словник
    if dict_type == "common" and chat_id != ADMIN_ID:
        bot.send_message(
            chat_id, 
            "❌ Додати слово неможливо, змініть свій словник на персональний.",
            reply_markup=main_menu_keyboard(chat_id)
        )
        return
    
    # Для адміна чи персонального словника дозволяємо продовжити
    clear_state(chat_id)
    
    # Зберігаємо тип словника у стані користувача
    user_state[chat_id] = {
        "step": "adding_word",
        "dict_type": dict_type  # Важливо зберегти обраний тип словника
    }
    
    bot.send_message(
        chat_id, 
        "Введіть слово, яке хочете додати:", 
        reply_markup=main_menu_cancel()
    )

@bot.message_handler(func=lambda message: message.text == "Відміна")
@log_handler
def cancel_action(message):
    clear_state(message.chat.id)
    bot.send_message(message.chat.id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "adding_word")
@log_handler
def handle_translation(message):
    if not message.text or message.text.startswith('/'):
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть слово текстом!")
        return
        
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть нове слово, а не команду.")
        return
        
    word = message.text.strip()
    dict_type = user_state.get(message.chat.id, {}).get("dict_type", "personal")
    print(f"Debug: User {message.chat.id} adding word to dictionary type: {dict_type}")
    
    # Збережемо dict_type для всіх наступних кроків
    user_state[message.chat.id]["dict_type"] = dict_type
    
    if dict_type == "common" and message.chat.id != ADMIN_ID:
        bot.send_message(
            message.chat.id, 
            "❌ Додати слово неможливо, змініть свій словник на персональний.",
            reply_markup=main_menu_keyboard(message.chat.id)
        )
        clear_state(message.chat.id)
        return
    
    # Отримання мови для перекладу
    if dict_type == "personal":
        file_path, language = get_user_file_path(message.chat.id)
        if not file_path:
            bot.send_message(message.chat.id, "❌ Мову перекладу не обрано. Спробуйте /start.")
            return
    else:
        # Для загального словника потрібно використовувати дійсний код мови
        # Перевіряємо, чи є у користувача персональний словник для визначення мови
        file_path, language = get_user_file_path(message.chat.id)
        
        if not file_path or language not in ["uk", "ru"]:
            # Якщо немає персонального словника або мова не визначена, використовуємо українську за замовчуванням
            language = "uk"
            print(f"Debug: Using default language '{language}' for common dictionary addition")
    
    print(f"Debug: Translating word '{word}' using language code '{language}'")
    translation = translator.translate(word, src="de", dest=language).text
    
    if translation:
        user_state[message.chat.id].update({
            "step": "confirm_translation",
            "word": word,
            "auto_translation": translation,
            "language": language  # Зберігаємо мову для подальшого використання
        })
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("Так", "Ні", "Відміна")
        bot.send_message(message.chat.id, f"Знайдено переклад: {translation}. Це правильно?", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Не вдалося перекласти слово. Спробуйте ще раз.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "confirm_translation")
@log_handler
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
@log_handler
def handle_manual_translation(message):
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть правильний переклад, а не команду.")
        return
    
    save_word(message.chat.id, message.text.strip())
    bot.send_message(message.chat.id, "✅ Слово успішно додано з вашим перекладом!", 
                    reply_markup=main_menu_keyboard(message.chat.id))

@bot.message_handler(func=lambda message: message.text == "📖 Вчити нові слова")
@log_handler
def learn_words(message):
    dict_type = user_state.get(message.chat.id, {}).get("dict_type", "personal")
    print(f"Debug: User {message.chat.id} learning with dictionary type: {dict_type}")
    
    if message.chat.id in user_state:
        user_state[message.chat.id]["dict_type"] = dict_type
    else:
        user_state[message.chat.id] = {"dict_type": dict_type}
    
    start_activity(message.chat.id, 'learn')

@bot.message_handler(func=lambda message: message.text == "🔄 Повторити")
@log_handler
def repeat_words(message):
    dict_type = user_state.get(message.chat.id, {}).get("dict_type", "personal")
    print(f"Debug: User {message.chat.id} repeating with dictionary type: {dict_type}")
    
    if message.chat.id in user_state:
        user_state[message.chat.id]["dict_type"] = dict_type
    else:
        user_state[message.chat.id] = {"dict_type": dict_type}
    
    start_activity(message.chat.id, 'repeat')

@bot.message_handler(func=lambda message: "🌐 Загальний словник" in message.text)
@log_handler
def select_common_dictionary(message):
    try:
        from dictionary import set_dictionary_type
        print(f"Switching user {message.chat.id} to common dictionary")
        common_file = os.path.join("user_dictionaries", "common_dictionary.csv")
        if not os.path.exists(common_file):
            print(f"Common dictionary does not exist: {common_file}")
            os.makedirs(os.path.dirname(common_file), exist_ok=True)
            df = pd.DataFrame(columns=["word", "translation", "priority", "article"])
            df.to_csv(common_file, index=False, encoding='utf-8-sig')
            print(f"Created common dictionary: {common_file}")
        
        set_dictionary_type(message.chat.id, "common")
    except Exception as e:
        print(f"Error switching to common dictionary: {e}")
        bot.send_message(message.chat.id, "❌ Виникла помилка при зміні словника.")

@bot.message_handler(func=lambda message: "👤 Персональний словник" in message.text)
@log_handler
def select_personal_dictionary(message):
    try:
        from dictionary import set_dictionary_type
        print(f"Switching user {message.chat.id} to personal dictionary")
        set_dictionary_type(message.chat.id, "personal")
    except Exception as e:
        print(f"Error switching to personal dictionary: {e}")
        bot.send_message(message.chat.id, "❌ Виникла помилка при зміні словника.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('tr_', 'de_')))
def handle_pairs(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or "pairs" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вчити нові слова'")
        return
    
    state = user_state[chat_id]
    
    if call.data.startswith('tr_'):
        if state.get('selected_tr'):
            bot.answer_callback_query(call.id, "⏳ Спочатку завершіть поточний вибір")
            return
        state['selected_tr'] = call.data[3:]
        bot.answer_callback_query(call.id, f"Обрано: {state['selected_tr']}")
    
    elif call.data.startswith('de_'):
        if not state.get('selected_tr'):
            bot.answer_callback_query(call.id, "❗ Спочатку оберіть переклад")
            return
        
        selected_de = call.data[3:]
        correct = any(tr == state['selected_tr'] and de == selected_de for tr, de in state["pairs"])
        
        df = get_dataframe(chat_id)
        if correct:
            bot.answer_callback_query(call.id, "✅ Правильно!")
            df.loc[df['translation'] == state['selected_tr'], 'priority'] -= 0.001
            markup = call.message.reply_markup
            for row in markup.keyboard:
                for btn in row:
                    if btn.callback_data in [f'tr_{state["selected_tr"]}', f'de_{selected_de}']:
                        btn.text += " ✅"
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
            
            if "found_pairs" not in state:
                state["found_pairs"] = []
            state["found_pairs"].append((state['selected_tr'], selected_de))
            
            if len(state["found_pairs"]) == len(state["pairs"]):
                bot.delete_message(chat_id, call.message.message_id)
                learn_words(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Неправильно!")
            df.loc[df['translation'] == state['selected_tr'], 'priority'] += 0.001
        
        dict_type = state.get("dict_type", "personal")
        print(f"Debug: handle_pairs saving for user {chat_id}, dict_type={dict_type}")
        
        if dict_type == "common":
            file_path, lang = get_common_file_path()
            save_dataframe(chat_id, df, "common")
        else:
            file_path, lang = get_user_file_path(chat_id)
            save_dataframe(chat_id, df, lang if lang else "uk")
        
        state['selected_tr'] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_answer(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Повторити'")
        return
    
    try:
        _, word, selected_tr = call.data.split('_')
        correct_tr = user_state[chat_id]["current_word"]['translation']
        
        df = get_dataframe(chat_id)
        if df is None:
            bot.answer_callback_query(call.id, "❌ Помилка доступу до словника")
            return
            
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
        
        dict_type = user_state[chat_id].get("dict_type", "personal")
        if dict_type == "common":
            file_path, lang = get_common_file_path()
        else:
            file_path, lang = get_user_file_path(chat_id)
            
        save_dataframe(chat_id, df, lang)
    except Exception as e:
        print(f"Error in handle_answer: {e}")
        bot.answer_callback_query(call.id, "❌ Помилка обробки відповіді")

@bot.message_handler(commands=['fire'])
@log_handler
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
@log_handler
def stop_bot(message):
    if message.from_user.id == ADMIN_ID:
        bot.stop_polling()
        scheduler.shutdown(wait=False)
        print("Бот зупинено!")
        exit(0)

@bot.message_handler(commands=['debug'])
@log_handler
def debug_command(message):
    """Show debug information for admin"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Ця команда доступна тільки для адміністратора.")
        return
        
    try:
        num_users = len([f for f in os.listdir('user_dictionaries') if f.endswith('.csv') and not f == 'common_dictionary.csv'])
        active_states = len(user_state)

        user_dict_types = {}
        for uid, state in user_state.items():
            user_dict_types[uid] = state.get('dict_type', 'personal')
        
        bot.reply_to(message, 
            f"📊 Debug Info:\n"
            f"- Active users: {active_states}\n"
            f"- Total users: {num_users}\n"
            f"- User dictionary types: {user_dict_types}\n"
            f"- Bot uptime: {get_uptime()}\n"
        )
        
        from debug_tools import debug_dictionaries
        debug_dictionaries()
        
    except Exception as e:
        if DEBUG_MODE:
            log_error(e, f"Error in debug command: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

def get_uptime():
    """Get bot uptime"""
    from main import START_TIME
    import time
    
    uptime_seconds = int(time.time() - START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days: parts.append(f"{days} days")
    if hours: parts.append(f"{hours} hours")
    if minutes: parts.append(f"{minutes} minutes")
    if seconds or not parts: parts.append(f"{seconds} seconds")
    
    return ", ".join(parts)
