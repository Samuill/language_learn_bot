# -*- coding: utf-8 -*-

"""
Основні функції для обробників телеграм-бота.
Цей модуль містить спільні функції, що використовуються в різних обробниках.
"""

import random
import telebot
import pandas as pd
from config import bot, user_state

def start_learning(chat_id, df):
    """Start learning new words activity"""
    # Перевірка структури DataFrame
    if df.empty:
        bot.send_message(chat_id, "📭 У вашому словнику поки немає слів для вивчення.")
        return False
    
    # Перевіряємо наявність потрібних колонок
    required_columns = ["word", "translation", "priority"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"ERROR: Missing required columns: {missing_columns}")
        print(f"Available columns: {df.columns.tolist()}")
        
        # Якщо бракує колонки перекладу, але є uk_tran або ru_tran, використовуємо їх
        if "translation" in missing_columns:
            if "uk_tran" in df.columns:
                df["translation"] = df["uk_tran"]
            elif "ru_tran" in df.columns:
                df["translation"] = df["ru_tran"]
        
        # Додаємо пріоритет, якщо його немає
        if "priority" in missing_columns:
            df["priority"] = 0.0
        
        # Перевіряємо ще раз після виправлень
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            bot.send_message(chat_id, "❌ Помилка структури словника. Спробуйте пізніше або зверніться до адміністратора.")
            return False
    
    # Сортуємо за пріоритетом для правильного вибору слів
    if "priority" in df.columns:
        df = df.sort_values(by="priority", ascending=False)
    
    # Вибираємо слова для вивчення
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
    # Спочатку завжди перевіряємо поточний тип словника в стані користувача
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    print(f"Debug: Starting article activity for user {chat_id} with dict_type={dict_type}, shared_dict_id={shared_dict_id}")
    
    # Для спільного словника, перевіряємо, чи є ID словника в БД, якщо немає в стані
    if dict_type == "shared" and not shared_dict_id:
        try:
            import db_manager
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                shared_dict_id = result[0]
                # Оновлюємо стан користувача
                if chat_id in user_state:
                    user_state[chat_id]["shared_dict_id"] = shared_dict_id
                print(f"Retrieved shared_dict_id={shared_dict_id} from database for user {chat_id}")
            else:
                # Якщо немає активного спільного словника, перемикаємо на персональний
                dict_type = "personal"
                if chat_id in user_state:
                    user_state[chat_id]["dict_type"] = "personal"
                print(f"No active shared dictionary found, switching to personal dictionary")
        except Exception as e:
            print(f"Error retrieving shared_dict_id: {e}")
            dict_type = "personal"  # Перемикаємо на персональний в разі помилки
            if chat_id in user_state:
                user_state[chat_id]["dict_type"] = "personal"
    
    try:
        # Отримуємо останнє слово, яке було показано, щоб не повторювати його
        last_word_id = user_state.get(chat_id, {}).get("last_article_word_id", None)
        
        import db_manager
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        language = db_manager.get_user_language(chat_id) or "uk"
        
        # Отримуємо всі слова з артиклями, виключаючи артикль з ID=4 (порожній) 
        # і останнє показане слово
        results = None
        
        if dict_type == "shared" and shared_dict_id:
            # Для спільного словника використовуємо відповідний запит
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
            # Переконуємось, що dict_type встановлено як "personal" для особистого словника
            dict_type = "personal"
            if chat_id in user_state:
                user_state[chat_id]["dict_type"] = "personal"
                
            # Персональний словник - фільтруємо слова з максимальним рейтингом (5.0) для не-складного рівня
            level = user_state.get(chat_id, {}).get("level", "easy")
            
            # Якщо це не складний рівень, обмежуємо показ слів з максимальним рейтингом
            exclude_max_rating_words = level != "hard"
            
            exclude_condition = f"AND w.id != {last_word_id}" if last_word_id else ""
            max_rating_filter = " AND u.rating < 4.9" if exclude_max_rating_words else ""
            
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation, u.rating
            FROM user_{chat_id} u
            JOIN words w ON u.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            {exclude_condition} {max_rating_filter}
            ORDER BY u.rating ASC
            LIMIT 15
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                # Якщо немає слів з урахуванням фільтру, спробуємо знову без фільтрації максимального рейтингу
                if exclude_max_rating_words:
                    query = query.replace(" AND u.rating < 4.9", "")
                    cursor.execute(query)
                    results = cursor.fetchall()
        
        conn.close()
        
        if not results:
            from dictionary import return_to_appropriate_menu
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
