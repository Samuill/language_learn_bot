# -*- coding: utf-8 -*-
import random
import telebot
import pandas as pd
from config import bot, translator, user_state, ADMIN_ID, scheduler  # Додано scheduler
from utils import clear_state, track_activity, main_menu_keyboard, main_menu_cancel, language_selection_keyboard, easy_level_keyboard, shared_dictionary_keyboard
from storage import get_dataframe, save_dataframe, get_user_file_path
from dictionary import save_word, toggle_dictionary, start_activity, return_to_appropriate_menu, set_dictionary_type
from utils.language_utils import get_text, is_command

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
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal")
    }
    return True

def start_article_activity(chat_id):
    """Start learning articles activity"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    print(f"Debug: Starting article activity for user {chat_id} with dict_type={dict_type}, shared_dict_id={shared_dict_id}")
    
    try:
        # Отримуємо останнє слово, яке було показано, щоб не повторювати його
        last_word_id = user_state.get(chat_id, {}).get("last_article_word_id", None)
        
        import db_manager
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        language = db_manager.get_user_language(chat_id) or "uk"
        
        # Якщо тип словника "shared", але shared_dict_id не вказано, спробуємо отримати його з бази даних
        if dict_type == "shared" and not shared_dict_id:
            cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            if result and result[0]:
                shared_dict_id = result[0]
                print(f"Retrieved shared_dict_id={shared_dict_id} for user {chat_id}")
            else:
                bot.send_message(chat_id, "❌ Помилка: не вибрано спільний словник. Спершу виберіть словник.")
                return_to_appropriate_menu(chat_id, False, "Не вибрано спільний словник")
                conn.close()
                return False
        
        # Отримуємо всі слова з артиклями, виключаючи артикль з ID=4 (порожній) 
        # і останнє показане слово
        results = None
        
        if dict_type == "shared" and shared_dict_id:
            # Для спільного словника використовуємо відповідний запит
            print(f"Getting articles from shared dictionary {shared_dict_id}")
            exclude_condition = f"AND w.id != {last_word_id}" if last_word_id else ""
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
            FROM shared_dict_{shared_dict_id} sd
            JOIN words w ON sd.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            {exclude_condition}
            ORDER BY RANDOM()
            LIMIT 20
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                # Якщо не знайдено слів з виключенням, спробуємо без нього
                query = f"""
                SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
                FROM shared_dict_{shared_dict_id} sd
                JOIN words w ON sd.word_id = w.id
                JOIN article a ON w.article_id = a.id
                WHERE w.article_id != 4 AND w.article_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 20
                """
                cursor.execute(query)
                results = cursor.fetchall()
            
        elif dict_type == "common":
            # Для загального словника
            exclude_condition = f"AND w.id != {last_word_id}" if last_word_id else ""
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
            FROM words w
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            {exclude_condition}
            ORDER BY RANDOM()
            LIMIT 20
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                query = query.replace(exclude_condition, "")
                cursor.execute(query)
                results = cursor.fetchall()
        else:
            # Для персонального словника
            exclude_condition = f"AND w.id != {last_word_id}" if last_word_id else ""
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation, u.rating
            FROM user_{chat_id} u
            JOIN words w ON u.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            {exclude_condition}
            ORDER BY u.rating ASC
            LIMIT 15
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                query = query.replace(exclude_condition, "")
                cursor.execute(query)
                results = cursor.fetchall()
        
        conn.close()
        
        if not results:
            bot.send_message(chat_id, "📭 У словнику немає слів з артиклями для вивчення.")
            return_to_appropriate_menu(chat_id, False, "У словнику немає слів з артиклями для вивчення.")
            return False
            
        # Вибираємо випадкове слово з результатів
        import random
        result = random.choice(results)
        print(f"Debug: Selected result: {result}")
        
        # Отримуємо дані зі слова, враховуючи, що результат може мати різну кількість полів
        if dict_type == "personal":
            # Для персонального словника результат містить 6 полів (включно з рейтингом)
            if len(result) >= 6:
                word_id, word, correct_article, article_id, translation, _ = result
            else:
                # Захист від помилок, якщо запит повернув менше полів
                word_id, word, correct_article, article_id, translation = result[:5]
        else:
            # Для спільного або загального словника результат містить 5 полів
            if len(result) >= 5:
                word_id, word, correct_article, article_id, translation = result[:5]
            else:
                # Захист від помилок
                print(f"Warning: Unexpected result format: {result}")
                raise ValueError(f"Unexpected result format: got {len(result)} values, expected at least 5")
        
        # Зберігаємо ID слова, щоб не повторювати його наступного разу
        user_state[chat_id] = {
            "word_id": word_id,
            "word": word,
            "correct_article": correct_article,
            "dict_type": dict_type,
            "level": "easy",
            "translation": translation,
            "last_article_word_id": word_id  # Зберігаємо для наступного запуску
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
            
        # Створюємо інлайн клавіатуру з артиклями
        markup = telebot.types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            telebot.types.InlineKeyboardButton("der", callback_data=f"art_der_{word_id}"),
            telebot.types.InlineKeyboardButton("die", callback_data=f"art_die_{word_id}"),
            telebot.types.InlineKeyboardButton("das", callback_data=f"art_das_{word_id}")
        )
        
        sent_message = bot.send_message(
            chat_id,
            f"🏷️ Виберіть правильний артикль для слова:\n\n<b>{word}</b>\n\n<i>Переклад: {translation}</i>",
            reply_markup=markup,
            parse_mode="HTML"
        )
        
        user_state[chat_id]["message_id"] = sent_message.message_id
        return True
        
    except Exception as e:
        print(f"Error in start_article_activity: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Помилка при запуску активності вивчення артиклів.")
        return False

@bot.callback_query_handler(func=lambda call: call.data.startswith(('art_der_', 'art_die_', 'art_das_')))
def handle_article_selection(call):
    """Handle article selection"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_state or "correct_article" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вивчати артиклі'")
        return
    
    # Отримуємо обраний артикль та ID слова
    selected_article = None
    if call.data.startswith('art_der_'):
        selected_article = 'der'
    elif call.data.startswith('art_die_'):
        selected_article = 'die'
    elif call.data.startswith('art_das_'):
        selected_article = 'das'
    
    correct_article = user_state[chat_id]["correct_article"]
    word = user_state[chat_id]["word"]
    word_id = user_state[chat_id]["word_id"]
    
    # Перевіряємо правильність вибору
    is_correct = selected_article == correct_article
    
    # Оновлюємо рейтинг слова в залежності від типу словника
    dict_type = user_state[chat_id].get("dict_type", "personal")
    if dict_type == "shared":
        import db_manager
        shared_dict_id = user_state[chat_id].get("shared_dict_id")
        db_manager.update_word_rating_shared_dict(chat_id, word_id, -0.1 if is_correct else 0.1, shared_dict_id)
    elif dict_type == "personal":
        import db_manager
        db_manager.update_word_rating(chat_id, word_id, -0.1 if is_correct else 0.1)
    
    # Показуємо користувачу результат
    if is_correct:
        bot.answer_callback_query(call.id, "✅ Правильно!")
        bot.edit_message_text(
            f"✅ Правильно! Слово <b>{word}</b> має артикль <b>{correct_article}</b>.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    else:
        bot.answer_callback_query(call.id, f"❌ Неправильно! Правильний артикль: {correct_article}")
        bot.edit_message_text(
            f"❌ Неправильно! Слово <b>{word}</b> має артикль <b>{correct_article}</b>, а не {selected_article}.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    
    # Переходимо до наступного слова через 2 секунди
    import threading
    threading.Timer(2, lambda: start_article_activity(chat_id)).start()

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

@bot.message_handler(func=lambda message: message.text in ["✖️ Відміна", "Відміна"])
def cancel_action(message):
    """Cancel current action and return to main menu"""
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(chat_id))

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

# Додавання та виправлення обробників для кнопок рівнів та словників
@bot.message_handler(func=lambda message: message.text == "🟢 Легкий рівень")
def easy_level(message):
    """Show easy level menu with learning activities"""
    chat_id = message.chat.id
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Update user state
    if chat_id in user_state:
        user_state[chat_id]["level"] = "easy"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "easy"}
    
    from utils import easy_level_keyboard
    bot.send_message(chat_id,  get_text("easy_level_select_activity",chat_id), 
                   reply_markup=easy_level_keyboard())

@bot.message_handler(func=lambda message: message.text == "🟠 Середній рівень")
def medium_level(message):
    """Show medium level menu (placeholder)"""
    chat_id = message.chat.id
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Update user state
    if chat_id in user_state:
        user_state[chat_id]["level"] = "medium"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "medium"}
    
    # Show "under development" message
    bot.send_message(chat_id, "🟠 Середній рівень у розробці. Будь ласка, оберіть інший рівень.", 
                   reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "🔴 Складний рівень")
def hard_level(message):
    """Show hard level menu (placeholder)"""
    chat_id = message.chat.id
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Update user state
    if chat_id in user_state:
        user_state[chat_id]["level"] = "hard"
    else:
        user_state[chat_id] = {"dict_type": dict_type, "level": "hard"}
    
    # Show "under development" message
    bot.send_message(chat_id, "🔴 Складний рівень у розробці. Будь ласка, оберіть інший рівень.", 
                   reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "↩️ Повернутися до головного меню")
def return_to_main_menu(message):
    """Return to main menu"""
    chat_id = message.chat.id
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    
    # Preserve dictionary type but remove level information
    if chat_id in user_state:
        user_state[chat_id] = {"dict_type": dict_type}
    
    # Send main menu
    bot.send_message(chat_id, "Головне меню:", 
                   reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text == "🏷️ Вивчати артиклі")
def learn_articles(message):
    """Start learning articles activity"""
    chat_id = message.chat.id
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    # Setup user state
    state_data = {"dict_type": dict_type, "level": "easy"}
    if shared_dict_id:
        state_data["shared_dict_id"] = shared_dict_id
    
    # Update or create user state
    if chat_id in user_state:
        user_state[chat_id].update(state_data)
    else:
        user_state[chat_id] = state_data
    
    # Start the article learning activity
    start_article_activity(chat_id)

@bot.message_handler(func=lambda message: message.text.startswith("👤 Персональний словник"))
def personal_dictionary_button(message):
    """Switch to personal dictionary"""
    chat_id = message.chat.id
    
    # Оновлюємо БД для очищення shared_dict_id
    import db_manager
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET shared_dict_id = NULL WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
    
    # Оновлюємо стан в пам'яті
    if chat_id in user_state:
        user_state[chat_id].update({"dict_type": "personal"})
        if "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
    else:
        user_state[chat_id] = {"dict_type": "personal"}
    
    bot.send_message(chat_id, "📚 Обрано персональний словник.",
                    reply_markup=main_menu_keyboard(chat_id))

@bot.message_handler(func=lambda message: message.text.startswith("👥 Спільний словник"))
def shared_dictionary_menu(message):
    """Show shared dictionary menu"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є вже активний словник
    import db_manager
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        # Якщо вже є вибраний словник, переходимо до нього
        shared_dict_id = result[0]
        
        # Оновлюємо стан користувача
        if chat_id in user_state:
            user_state[chat_id].update({"dict_type": "shared", "shared_dict_id": shared_dict_id})
        else:
            user_state[chat_id] = {"dict_type": "shared", "shared_dict_id": shared_dict_id}
        
        # Отримуємо інформацію про словник
        cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
        dict_info = cursor.fetchone()
        dict_name = dict_info[0] if dict_info else "Невідомий словник"
        
        # Повідомляємо про активний словник
        bot.send_message(
            chat_id,
            f"📚 Обрано спільний словник: <b>{dict_name}</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(chat_id)
        )
    else:
        # Ініціалізуємо таблиці для спільних словників, якщо вони не існують
        db_manager.create_shared_dictionary_tables()
        
        # Показуємо меню спільних словників
        bot.send_message(chat_id, "👥 Спільні словники - оберіть опцію:",
                        reply_markup=shared_dictionary_keyboard())
        
        # Оновлюємо тип словника у стані користувача
        if chat_id in user_state:
            user_state[chat_id].update({"dict_type": "shared"})
        else:
            user_state[chat_id] = {"dict_type": "shared"}
    
    conn.close()

# Додаємо обробники для кнопок меню спільних словників
@bot.message_handler(func=lambda message: message.text == "🆕 Створити спільний словник")
def create_shared_dictionary(message):
    """Create a new shared dictionary"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Зберігаємо стан користувача
    user_state[chat_id] = {
        "step": "creating_shared_dict",
    }
    
    bot.send_message(chat_id, "Введіть назву для спільного словника:",
                    reply_markup=main_menu_cancel())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "creating_shared_dict")
def handle_shared_dict_name(message):
    """Handle shared dictionary name input"""
    chat_id = message.chat.id
    
    if message.text == "Відміна" or message.text == "✖️ Відміна":
        clear_state(chat_id)
        bot.send_message(chat_id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(chat_id))
        return
    
    dict_name = message.text.strip()
    
    if len(dict_name) < 3 or len(dict_name) > 30:
        bot.send_message(chat_id, "❌ Назва словника повинна містити від 3 до 30 символів.")
        return
    
    # Створюємо спільний словник
    import db_manager
    code, shared_dict_id = db_manager.create_shared_dictionary(chat_id, dict_name)
    
    # Повідомляємо про успішне створення та показуємо код доступу
    bot.send_message(
        chat_id,
        f"✅ Спільний словник '{dict_name}' успішно створено!\n\n"
        f"Код доступу: <code>{code}</code>\n\n"
        f"Поділіться цим кодом з друзями, щоб вони могли приєднатися до вашого словника.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(chat_id)
    )
    
    clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "🔑 Вступити до спільного словника")
def join_shared_dictionary(message):
    """Join an existing shared dictionary"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Зберігаємо стан користувача
    user_state[chat_id] = {
        "step": "joining_shared_dict",
    }
    
    bot.send_message(chat_id, "Введіть код доступу до спільного словника:",
                    reply_markup=main_menu_cancel())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "joining_shared_dict")
def handle_shared_dict_code(message):
    """Handle shared dictionary code input"""
    chat_id = message.chat.id
    
    if message.text == "Відміна" or message.text == "✖️ Відміна":
        clear_state(chat_id)
        bot.send_message(chat_id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard(chat_id))
        return
    
    code = message.text.strip().upper()
    
    if len(code) != 6:
        bot.send_message(chat_id, "❌ Код доступу повинен містити 6 символів.")
        return
    
    # Приєднуємось до спільного словника
    import db_manager
    success, result = db_manager.join_shared_dictionary(chat_id, code)
    
    if success:
        # Повідомляємо про успішне приєднання
        bot.send_message(
            chat_id,
            f"✅ Ви успішно приєднались до спільного словника '{result}'!",
            reply_markup=main_menu_keyboard(chat_id)
        )
    else:
        # Повідомляємо про помилку
        bot.send_message(chat_id, f"❌ {result}")
    
    clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "📋 Мої спільні словники")
def my_shared_dictionaries(message):
    """Show user's shared dictionaries"""
    chat_id = message.chat.id
    
    # Отримуємо список спільних словників користувача
    import db_manager
    shared_dicts = db_manager.get_user_shared_dictionaries(chat_id)
    
    if not shared_dicts:
        bot.send_message(
            chat_id,
            "📭 Ви не є учасником жодного спільного словника.",
            reply_markup=shared_dictionary_keyboard()
        )
        return
    
    # Показуємо список словників
    response = "📋 Ваші спільні словники:\n\n"
    
    for dict_info in shared_dicts:
        admin_status = "👑 Адміністратор" if dict_info['is_admin'] else "👤 Учасник"
        response += f"• <b>{dict_info['name']}</b> ({admin_status})\n"
        response += f"  Код доступу: <code>{dict_info['code']}</code>\n\n"
    
    response += "Оберіть словник, який бажаєте використовувати:"
    
    # Створюємо інлайн клавіатуру для вибору словника
    markup = telebot.types.InlineKeyboardMarkup()
    
    for dict_info in shared_dicts:
        admin_icon = "👑" if dict_info['is_admin'] else "👤"
        button_text = f"{admin_icon} {dict_info['name']}"
        markup.add(telebot.types.InlineKeyboardButton(
            button_text, 
            callback_data=f"use_shared_dict_{dict_info['id']}"
        ))
    
    bot.send_message(
        chat_id,
        response,
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("use_shared_dict_"))
def use_shared_dictionary(call):
    """Switch to a specific shared dictionary"""
    chat_id = call.message.chat.id
    shared_dict_id = int(call.data.replace("use_shared_dict_", ""))
    
    # Оновлюємо статус користувача для використання цього словника
    import db_manager
    
    # Оновлюємо запис у базі даних
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET shared_dict_id = ? WHERE chat_id = ?', 
                 (shared_dict_id, chat_id))
    conn.commit()
    
    # Отримуємо назву словника для повідомлення
    cursor.execute('SELECT name FROM shared_dictionaries WHERE id = ?', (shared_dict_id,))
    dict_name = cursor.fetchone()[0]
    conn.close()
    
    # Оновлюємо стан користувача в пам'яті
    if chat_id in user_state:
        user_state[chat_id].update({"dict_type": "shared", "shared_dict_id": shared_dict_id})
    else:
        user_state[chat_id] = {"dict_type": "shared", "shared_dict_id": shared_dict_id}
    
    bot.answer_callback_query(call.id, f"Обрано спільний словник: {dict_name}")
    bot.delete_message(chat_id, call.message.message_id)
    
    bot.send_message(
        chat_id,
        f"📚 Обрано спільний словник: <b>{dict_name}</b>\n"
        f"Тепер всі дії будуть виконуватись у цьому словнику.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(chat_id)
    )
