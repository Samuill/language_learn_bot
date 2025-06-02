# -*- coding: utf-8 -*-
import random
import telebot
import pandas as pd
import os
import sqlite3  # Додано цей рядок
from config import bot, translator, user_state, ADMIN_ID, DEBUG_MODE, scheduler
from utils import clear_state, track_activity, main_menu_keyboard, main_menu_cancel, language_selection_keyboard, easy_level_keyboard, shared_dictionary_keyboard
from storage import get_dataframe, save_dataframe, get_user_file_path, get_common_file_path
from dictionary import save_word, toggle_dictionary, start_activity, return_to_appropriate_menu, set_dictionary_type

# Import debug logger if debug mode is enabled
if DEBUG_MODE:
    from debug_logger import log_handler, log_message, log_response, log_error

def start_learning(chat_id, df):
    """Start learning new words activity"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    level = user_state.get(chat_id, {}).get("level", "easy")
    print(f"Debug: start_learning for user {chat_id}, dict_type={dict_type}, level={level}")
    
    # Сортуємо за рейтингом і поділяємо на групи для зваженого вибору
    df = df.sort_values(by="priority", ascending=True)
    
    # Ділимо слова на три групи за рейтингом (менший рейтинг = важче слово)
    total_words = len(df)
    if total_words >= 30:
        # Якщо достатньо слів, беремо більше слів з нижчим рейтингом
        group_low = df.iloc[:int(total_words * 0.5)]  # 50% слів з нижчим рейтингом
        group_mid = df.iloc[int(total_words * 0.5):int(total_words * 0.8)]  # 30% середніх
        group_high = df.iloc[int(total_words * 0.8):]  # 20% з високим рейтингом
        
        # Вибираємо більше слів з групи з нижчим рейтингом
        words_low = group_low.sample(min(6, len(group_low)))
        words_mid = group_mid.sample(min(3, len(group_mid)))
        words_high = group_high.sample(min(1, len(group_high)))
        
        # Об'єднуємо вибрані слова
        words = pd.concat([words_low, words_mid, words_high])
    else:
        # Для малої кількості слів просто зважуємо випадковий вибір
        # Інвертуємо рейтинг для створення ваг (нижчий рейтинг = вища вага)
        weights = 5.0 - df['priority']  # Припускаємо, що рейтинг від 0 до 5
        weights = weights.clip(0.1, 5.0)  # Запобігаємо нульовим або негативним вагам
        
        # Використовуємо зважений випадковий вибір
        words = df.sample(min(10, len(df)), weights=weights)
    
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
    for tr, de in zip(translations, de_words):
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
        
        # Зважений вибір слова за пріоритетом (нижчий пріоритет = вища вага)
        weights = 5.0 - df['priority']  # Припускаємо, що пріоритет від 0 до 5
        weights = weights.clip(0.1, 5.0)  # Запобігаємо нульовим або негативним вагам
        
        word = df.sample(1, weights=weights).iloc[0]
        
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
        
        # Отримуємо всі слова з артиклями, виключаючи артикль з ID=4 (порожній) 
        # і останнє показане слово
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
            
            # Вибираємо випадкове слово з результатів
            import random
            if results:
                result = random.choice(results)
                word_id, word, correct_article, article_id, translation = result
            else:
                result = None
                
        elif dict_type == "common":
            # Для загального словника використовуємо більше випадковості
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
                # Якщо не знайдено слів з виключенням, спробуємо без нього
                query = f"""
                SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
                FROM words w
                JOIN article a ON w.article_id = a.id
                WHERE w.article_id != 4 AND w.article_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 20
                """
                cursor.execute(query)
                results = cursor.fetchall()
            
            # Вибираємо випадкове слово з результатів
            import random
            if results:
                result = random.choice(results)
                word_id, word, correct_article, article_id, translation = result
            else:
                result = None
        else:
            # Для персонального словника беремо більше слів для різноманітності
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
                # Якщо не знайдено слів з виключенням, спробуємо без нього
                query = f"""
                SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation, u.rating
                FROM user_{chat_id} u
                JOIN words w ON u.word_id = w.id
                JOIN article a ON w.article_id = a.id
                WHERE w.article_id != 4 AND w.article_id IS NOT NULL
                ORDER BY u.rating ASC
                LIMIT 15
                """
                cursor.execute(query)
                results = cursor.fetchall()
            
            if not results:
                bot.send_message(chat_id, "📭 У словнику немає слів з артиклями для вивчення.")
                return_to_appropriate_menu(chat_id, False, "У словнику немає слів з артиклями для вивчення.")
                conn.close()
                return False
            
            # Додаємо випадковість при виборі, з перевагою для слів з низьким рейтингом
            # Використовуємо експоненційні ваги для більшої різноманітності
            import random
            import math
            
            # Створюємо ваги з використанням експоненційної функції для більшого розмаху
            weights = [math.exp(3 * (5.0 - min(result[5], 5.0)) / 5.0) for result in results]
            chosen_index = random.choices(range(len(results)), weights=weights, k=1)[0]
            result = results[chosen_index]
            
            word_id, word, correct_article, article_id, translation, _ = result
        
        conn.close()
        
        if not result:
            bot.send_message(chat_id, "📭 У словнику немає слів з артиклями для вивчення.")
            return_to_appropriate_menu(chat_id, False, "У словнику немає слів з артиклями для вивчення.")
            return False
        
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("art_"))
def handle_article_selection(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вивчати артиклі'")
        return
    
    try:
        state = user_state[chat_id]
        word_id = state.get("word_id")
        correct_article = state.get("correct_article")
        word = state.get("word")
        dict_type = state.get("dict_type", "personal")
        
        # Парсимо вибраний артикль
        _, selected_article, word_id_from_callback = call.data.split('_')
        
        # Перевіряємо правильність відповіді
        is_correct = selected_article == correct_article
        
        if is_correct:
            bot.answer_callback_query(call.id, "✅ Правильно!")
            
            # Оновлюємо рейтинг слова
            try:
                import db_manager
                if dict_type == "personal":
                    db_manager.update_word_rating(chat_id, word_id, 0.1, dict_type)
                    print(f"Successfully increased rating for word_id={word_id}")
            except Exception as e:
                print(f"Error updating word rating: {e}")
            
            # Показуємо правильну відповідь без кнопки "Далі"
            bot.edit_message_text(
                f"🏷️ <b>{correct_article} {word}</b>\n\n<i>✅ Правильно!</i>",
                chat_id,
                call.message.message_id,
                parse_mode="HTML"
            )
        else:
            bot.answer_callback_query(call.id, f"❌ Неправильно! Правильно: {correct_article}")
            
            # Оновлюємо рейтинг слова (знижуємо)
            try:
                import db_manager
                if dict_type == "personal":
                    db_manager.update_word_rating(chat_id, word_id, -0.1, dict_type)
                    print(f"Successfully decreased rating for word_id={word_id}")
            except Exception as e:
                print(f"Error updating word rating: {e}")
            
            # Показуємо правильну відповідь без кнопки "Далі"
            bot.edit_message_text(
                f"🏷️ <b>{correct_article} {word}</b>\n\n<i>❌ Запам'ятайте правильний артикль.</i>",
                chat_id,
                call.message.message_id,
                parse_mode="HTML"
            )
        
        # Додаємо кнопку для продовження
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("➡️ Наступне слово", callback_data="next_article"))
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
        
    except Exception as e:
        print(f"Error in handle_article_selection: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "❌ Помилка обробки відповіді")
        try:
            # Додаємо кнопку для продовження навіть у разі помилки
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("➡️ Спробувати інше слово", callback_data="next_article"))
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
        except:
            pass

# Нова функція для запуску наступної активності після таймауту
def continue_article_activity(chat_id, message_id):
    try:
        # Видаляємо попереднє повідомлення
        bot.delete_message(chat_id, message_id)
        # Запускаємо нову активність з артиклями
        start_article_activity(chat_id)
    except Exception as e:
        print(f"Error in continue_article_activity: {e}")
        try:
            bot.send_message(chat_id, "❌ Помилка при запуску наступного завдання.")
        except:
            pass

# Залишаємо старий handler для зворотної сумісності, 
# але він не буде активно використовуватися
@bot.callback_query_handler(func=lambda call: call.data == "next_article")
def handle_next_article(call):
    chat_id = call.message.chat.id
    bot.delete_message(chat_id, call.message.message_id)
    start_article_activity(chat_id)

@bot.message_handler(func=lambda message: message.text == "👥 Спільний словник" or 
                    message.text.startswith("👥 Спільний словник"))
@log_handler
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
        dict_name = cursor.fetchone()[0]
        
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

@bot.message_handler(func=lambda message: message.text == "👤 Персональний словник" or 
                    message.text.startswith("👤 Персональний словник"))
@log_handler
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

@bot.message_handler(func=lambda message: message.text == "🆕 Створити спільний словник")
@log_handler
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
@log_handler
def handle_shared_dict_name(message):
    """Handle shared dictionary name input"""
    chat_id = message.chat.id
    
    if message.text == "Відміна":
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
@log_handler
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
@log_handler
def handle_shared_dict_code(message):
    """Handle shared dictionary code input"""
    chat_id = message.chat.id
    
    if message.text == "Відміна":
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
@log_handler
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

@bot.message_handler(commands=["start"])
def main_menu(message):
    """Initial start command handler - simplified for reliability"""
    chat_id = message.chat.id
    clear_state(chat_id)
    
    # Використовуємо базу даних для перевірки мови користувача
    import db_manager
    language = db_manager.get_user_language(chat_id)
    
    track_activity(chat_id)
    
    if not language:
        bot.send_message(chat_id, "🌍 Виберіть мову, на якій бажаєте отримувати переклад слів:", 
                         reply_markup=language_selection_keyboard())
        user_state[chat_id] = {"step": "language_selection"}
    else:
        bot.send_message(chat_id, "Оберіть дію:", 
                         reply_markup=main_menu_keyboard(chat_id))

# Simplify level selection handlers to ensure they work reliably
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
    bot.send_message(chat_id, "🟢 Легкий рівень - оберіть активність:", 
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