# -*- coding: utf-8 -*-
import random
import telebot
import pandas as pd
import os
import sqlite3  # Додано цей рядок
from config import bot, translator, user_state, ADMIN_ID, DEBUG_MODE, scheduler
from utils import clear_state, track_activity, main_menu_keyboard, main_menu_cancel, language_selection_keyboard, easy_level_keyboard
from storage import get_dataframe, save_dataframe, get_user_file_path, get_common_file_path
from dictionary import save_word, toggle_dictionary, start_activity, return_to_appropriate_menu

# Import debug logger if debug mode is enabled
if DEBUG_MODE:
    from debug_logger import log_handler, log_message, log_response, log_error

def start_learning(chat_id, df):
    """Start learning new words activity"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    level = user_state.get(chat_id, {}).get("level", "easy")
    print(f"Debug: start_learning for user {chat_id}, dict_type={dict_type}, level={level}")
    
    # Сортуємо за рейтингом в порядку зростання, щоб менші рейтинги (важчі слова) йшли першими
    df = df.sort_values(by="priority", ascending=True)
    words = df.sample(min(10, len(df)))
    
    # Формуємо пари переклад-німецьке слово
    pairs = []
    for _, row in words.iterrows():
        translation = row['translation']
        german_word = row['word']
        
        # Формуємо німецьке слово з артиклем, якщо він є
        if pd.notna(row['article']) and row['article'] != '':
            german_display = f"{row['article']} {german_word}"
        else:
            german_display = german_word
            
        pairs.append((translation, german_display, row['id']))
    
    # Перемішуємо порядок пар
    random.shuffle(pairs)
    
    # Розділяємо пари на окремі списки для створення кнопок
    translations = [pair[0] for pair in pairs]
    de_words = [pair[1] for pair in pairs]
    
    # Перемішуємо окремо для відображення
    shuffled_translations = translations.copy()
    shuffled_de_words = de_words.copy()
    random.shuffle(shuffled_translations)
    random.shuffle(shuffled_de_words)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for tr, de in zip(shuffled_translations, shuffled_de_words):
        markup.add(
            telebot.types.InlineKeyboardButton(tr, callback_data=f'tr_{tr}'),
            telebot.types.InlineKeyboardButton(de, callback_data=f'de_{de}')
        )
    
    # Зберігаємо оригінальні пари та інформацію про слова
    user_state[chat_id] = {
        "pairs": [(tr, de) for tr, de, _ in pairs],  # Зберігаємо пари без ID
        "word_ids": {tr: wid for tr, _, wid in pairs},  # Зберігаємо зв'язок між перекладами та ID слів
        "selected_tr": None,
        "message_id": None,
        "dict_type": dict_type,
        "level": level,
        "original_words": words
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
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        word = df.sample(1).iloc[0]
        sample_size = min(3, len(df))
        translations = df['translation'].sample(sample_size).tolist()
        if word['translation'] not in translations:
            translations[0] = word['translation']
        random.shuffle(translations)
        
        # Формуємо слово з артиклем для відображення
        display_word = word['word']
        if pd.notna(word['article']) and word['article'] != '':
            display_word = f"{word['article']} {word['word']}"
        
        markup = telebot.types.InlineKeyboardMarkup()
        for tr in translations:
            markup.add(telebot.types.InlineKeyboardButton(
                tr, 
                callback_data=f"ans_{word['word']}_{tr}"
            ))
        
        sent_message = bot.send_message(chat_id, f"📖 Оберіть переклад для слова: {display_word}", reply_markup=markup)
        user_state[chat_id] = {
            "current_word": word,
            "message_id": sent_message.message_id,
            "dict_type": dict_type,
            "level": level
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
    
    # Використовуємо базу даних для перевірки мови користувача
    import db_manager
    language = db_manager.get_user_language(message.chat.id)
    
    track_activity(message.chat.id)
    
    if not language:
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
        
        # Встановлюємо мову користувача в базі даних
        import db_manager
        db_manager.set_user_language(chat_id, language)
        
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
    
    # Пошук артикля у базі данних німецьких слів
    from german_article_finder import find_german_article
    article, clean_word = find_german_article(word)
    if article:
        print(f"Found article '{article}' for word '{word}' -> '{clean_word}'")
        # Використовуємо original_word для збереження повного вводу користувача
        user_state[message.chat.id]["original_word"] = word
        # А word буде нормалізованим словом з артиклем
        word = f"{article} {clean_word}"
    
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
    
    # Отримуємо мову користувача з бази даних
    import db_manager
    language = db_manager.get_user_language(message.chat.id)
    
    if not language:
        bot.send_message(message.chat.id, "❌ Мову перекладу не обрано. Спробуйте /start.")
        return
    
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
        # Функція save_word вже відправляє повідомлення про успіх
        save_word(message.chat.id)
        # Прибираємо дублікат повідомлення
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
    
    # Функція save_word вже відправляє повідомлення про успіх
    save_word(message.chat.id, message.text.strip())
    # Прибираємо дублікат повідомлення

@bot.message_handler(func=lambda message: message.text == "📖 Вчити нові слова")
@log_handler
def learn_words(message):
    dict_type = user_state.get(message.chat.id, {}).get("dict_type", "personal")
    level = user_state.get(message.chat.id, {}).get("level", "easy")
    
    print(f"Debug: User {message.chat.id} learning with dictionary type: {dict_type}, level: {level}")
    
    if message.chat.id in user_state:
        # Зберігаємо і тип словника, і рівень
        user_state[message.chat.id].update({
            "dict_type": dict_type,
            "level": level
        })
    else:
        user_state[message.chat.id] = {"dict_type": dict_type, "level": level}
    
    start_activity(message.chat.id, 'learn')

@bot.message_handler(func=lambda message: message.text == "🔄 Повторити")
@log_handler
def repeat_words(message):
    dict_type = user_state.get(message.chat.id, {}).get("dict_type", "personal")
    level = user_state.get(message.chat.id, {}).get("level", "easy")
    
    print(f"Debug: User {message.chat.id} repeating with dictionary type: {dict_type}, level: {level}")
    
    if message.chat.id in user_state:
        # Зберігаємо і тип словника, і рівень
        user_state[message.chat.id].update({
            "dict_type": dict_type,
            "level": level
        })
    else:
        user_state[message.chat.id] = {"dict_type": dict_type, "level": level}
    
    start_activity(message.chat.id, 'repeat')

@bot.callback_query_handler(func=lambda call: call.data.startswith(('tr_', 'de_')))
def handle_pairs(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or "pairs" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вчити нові слова'")
        return
    
    state = user_state[chat_id]
    dict_type = state.get("dict_type", "personal")
    
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
        selected_tr = state['selected_tr']
        
        # Виправлення: чітке логування для відладки
        print(f"DEBUG: Selected tr='{selected_tr}', de='{selected_de}'")
        print(f"DEBUG: Available pairs to match: {state['pairs']}")
        
        # Шукаємо точну пару в збережених парах
        correct = (selected_tr, selected_de) in state["pairs"]
        
        print(f"DEBUG: Match {'found' if correct else 'not found'} for tr='{selected_tr}', de='{selected_de}'")
        
        if correct:
            bot.answer_callback_query(call.id, "✅ Правильно!")
            
            # Оновлення рейтингу через SQLite - при правильній відповіді рейтинг збільшується на 0.1
            try:
                import db_manager
                if "word_ids" in state and selected_tr in state["word_ids"]:
                    word_id = state["word_ids"][selected_tr]
                    db_manager.update_word_rating(chat_id, word_id, 0.1, dict_type)
                    print(f"Successfully increased rating for word_id={word_id}")
                else:
                    print("Error: word_id not found for translation")
            except Exception as e:
                print(f"Error updating word rating: {e}")
                import traceback
                traceback.print_exc()
            
            # Оновлення інтерфейсу
            markup = call.message.reply_markup
            for row in markup.keyboard:
                for btn in row:
                    if btn.callback_data in [f'tr_{selected_tr}', f'de_{selected_de}']:
                        btn.text += " ✅"
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
            
            # Відстежуємо знайдені пари
            if "found_pairs" not in state:
                state["found_pairs"] = []
            state["found_pairs"].append((selected_tr, selected_de))
            
            print(f"DEBUG: Found pairs: {len(state['found_pairs'])}/{len(state['pairs'])}")
            
            # Запускаємо нову гру, якщо всі пари знайдено
            if len(state["found_pairs"]) == len(state["pairs"]):
                bot.delete_message(chat_id, call.message.message_id)
                return_to_appropriate_menu(chat_id, True, "✅ Відмінно! Всі пари з'єднано!")
        else:
            bot.answer_callback_query(call.id, "❌ Неправильно!")
            
            try:
                import db_manager
                if "word_ids" in state and selected_tr in state["word_ids"]:
                    word_id = state["word_ids"][selected_tr]
                    db_manager.update_word_rating(chat_id, word_id, -0.1, dict_type)
                    print(f"Successfully decreased rating for word_id={word_id}")
                else:
                    print("Error: word_id not found for translation")
            except Exception as e:
                print(f"Error updating word rating: {e}")
                import traceback
                traceback.print_exc()
        
        # Зкидаємо вибір після обробки
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
        dict_type = user_state[chat_id].get("dict_type", "personal")
        
        if selected_tr == correct_tr:
            bot.answer_callback_query(call.id, "✅ Правильно!")
            
            try:
                import db_manager
                word_id = int(user_state[chat_id]["current_word"]['id'])
                db_manager.update_word_rating(chat_id, word_id, 0.1, dict_type)
                print(f"Successfully increased rating for word_id={word_id}")
            except Exception as e:
                print(f"Error updating word rating: {e}")
                
            bot.delete_message(chat_id, call.message.message_id)
            start_activity(chat_id, 'repeat')
        else:
            bot.answer_callback_query(call.id, f"❌ Неправильно! Правильно: {correct_tr}")
            
            try:
                import db_manager
                word_id = int(user_state[chat_id]["current_word"]['id'])
                db_manager.update_word_rating(chat_id, word_id, -0.1, dict_type)
                print(f"Successfully decreased rating for word_id={word_id}")
            except Exception as e:
                print(f"Error updating word rating: {e}")
            
            markup = call.message.reply_markup
            for row in markup.keyboard:
                if row[0].callback_data == call.data:
                    row[0].text += " ❌"
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
            
    except Exception as e:
        print(f"Error in handle_answer: {e}")
        bot.answer_callback_query(call.id, "❌ Помилка обробки відповіді")

@bot.message_handler(func=lambda message: message.text == "🟢 Легкий рівень")
@log_handler
def easy_level(message):
    """Show easy level menu with basic learning activities"""
    chat_id = message.chat.id
    
    # Збережемо поточний тип словника
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        user_state[chat_id]["level"] = "easy"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "easy"}
    
    bot.send_message(chat_id, "🟢 Легкий рівень - оберіть активність:", 
                    reply_markup=easy_level_keyboard())

@bot.message_handler(func=lambda message: message.text == "🟠 Середній рівень")
@log_handler
def medium_level(message):
    """Show medium level menu (placeholder)"""
    chat_id = message.chat.id
    
    # Зберігаємо поточний тип словника і рівень
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        user_state[chat_id]["level"] = "medium"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "medium"}
    
    bot.send_message(chat_id, "🟠 Середній рівень у розробці", 
                    reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "🔴 Складний рівень")
@log_handler
def hard_level(message):
    """Show hard level menu (placeholder)"""
    chat_id = message.chat.id
    
    # Зберігаємо поточний тип словника і рівень
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        user_state[chat_id]["level"] = "hard"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "hard"}
    
    bot.send_message(chat_id, "🔴 Складний рівень у розробці", 
                    reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "↩️ Повернутися до головного меню")
@log_handler
def return_to_main_menu(message):
    """Return to main menu"""
    chat_id = message.chat.id
    
    # Зберігаємо тип словника
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    if chat_id in user_state:
        # Видаляємо рівень, зберігаючи тип словника
        user_state[chat_id] = {"dict_type": dict_type}
    
    bot.send_message(chat_id, "Головне меню:", 
                    reply_markup=main_menu_keyboard(chat_id))
