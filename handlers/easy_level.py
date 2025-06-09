# -*- coding: utf-8 -*-

"""
Обробники для активностей легкого рівня.
"""

import random
import telebot
import pandas as pd
import traceback
import db_manager  # Add explicit import of db_manager
from config import bot, user_state
from dictionary import return_to_appropriate_menu
from utils.language_utils import get_text, is_command
from utils import clear_state
from utils import clear_state, main_menu_keyboard, easy_level_keyboard
from utils.input_handlers import safe_next_step_handler, sanitize_user_input, is_menu_navigation_command, handle_exit_from_activity

@bot.message_handler(func=lambda message: is_command(message, "learning_new_words"))
def learn_words(message):
    """Handler for learning new words activity"""
    chat_id = message.chat.id
    
    # Load dictionary with our unified helper
    from utils.dictionary_helpers import load_user_dictionary, handle_empty_dictionary
    df, dict_type, dict_name, shared_dict_id, success = load_user_dictionary(chat_id)
    
    if not success:
        bot.send_message(chat_id, get_text("error_occurred", chat_id), reply_markup=easy_level_keyboard(chat_id))
        return
    
    # Update state with dictionary info to ensure consistency
    if chat_id in user_state:
        user_state[chat_id].update({
            "dict_type": dict_type,
            "level": "easy"
        })
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
    else:
        user_state[chat_id] = {
            "dict_type": dict_type,
            "level": "easy"
        }
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    # Check if we have words
    if df is None or df.empty:
        return handle_empty_dictionary(chat_id, easy_level_keyboard(chat_id), dict_name)
    
    # Start learning activity
    try:
        success = start_learning(chat_id, df)
        if not success:
            bot.send_message(chat_id, get_text("error_activity", chat_id), reply_markup=easy_level_keyboard(chat_id))
    except Exception as e:
        print(f"Error in learn_words: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, get_text("error_learning_activity", chat_id), reply_markup=easy_level_keyboard(chat_id))

def start_learning(chat_id, df):
    """Start learning new words activity"""
    # Перевірка структури DataFrame
    if df.empty:
        bot.send_message(chat_id, get_text("no_words_in_dictionary", chat_id))
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
    
    sent_message = bot.send_message(
        chat_id,
        get_text("select_pair", chat_id),  # was "🔍 Оберіть пару слів:"
        reply_markup=markup
    )
    user_state[chat_id]["message_id"] = sent_message.message_id
    return True

@bot.callback_query_handler(func=lambda call: call.data.startswith(('tr_', 'de_')))
def handle_pairs(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or "pairs" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    state = user_state[chat_id]
    
    if call.data.startswith('tr_'):
        if state.get('selected_tr'):
            bot.answer_callback_query(call.id, get_text("wait_for_selection", chat_id))  # was "⏳ Спочатку завершіть поточний вибір"
            return
        state['selected_tr'] = call.data[3:]
        bot.answer_callback_query(call.id,get_text("selected",chat_id) + f"{state['selected_tr']}")
    
    elif call.data.startswith('de_'):
        if not state.get('selected_tr'):
            bot.answer_callback_query(call.id, get_text("select_translation_first", chat_id))  # was "❗ Спочатку оберіть переклад"
            return
        
        selected_de = call.data[3:]
        correct = any(tr == state['selected_tr'] and de == selected_de for tr, de in state["pairs"])
        
        try:
            # Получаем DataFrame для обновления рейтинга
            dict_type = state.get("dict_type", "personal")
            shared_dict_id = state.get("shared_dict_id")
            
            if dict_type == "shared" and shared_dict_id:
                # Для общего словаря используем API для обновления рейтинга
                for tr, de in state["pairs"]:
                    if tr == state['selected_tr']:
                        # Получаем ID слова и обновляем рейтинг
                        word_id = db_manager.get_word_id_by_german(de)
                        if word_id:
                            rating_change = -0.1 if correct else 0.1
                            db_manager.update_word_rating_shared_dict(
                                chat_id, word_id, rating_change, shared_dict_id)
                            break
            else:
                # Для личного словаря используем DataFrame
                from storage import get_dataframe, save_dataframe, get_user_file_path
                df = get_dataframe(chat_id)
                
                if 'translation' in df.columns and 'priority' in df.columns:
                    mask = df['translation'] == state['selected_tr']
                    if mask.any():
                        df.loc[mask, 'priority'] += -0.1 if correct else 0.1
                        
                # Сохраняем DataFrame
                file_path, lang = get_user_file_path(chat_id) if dict_type == "personal" else (None, None)
                save_dataframe(chat_id, df, lang if lang else "common")
            
            if correct:
                bot.answer_callback_query(call.id, get_text("correct",chat_id))
                
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
                bot.answer_callback_query(call.id, get_text("correct",chat_id))
            
            state['selected_tr'] = None
        except Exception as e:
            print(f"ERROR in handle_pairs: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, get_text("error_activity",chat_id))
            state['selected_tr'] = None

@bot.message_handler(func=lambda message: is_command(message, "repetition"))
def repeat_words(message):
    """Handler for the repeat words command"""
    chat_id = message.chat.id
    
    # Get the current dictionary type and shared dictionary ID
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    try:
        # Get dataframe from the appropriate dictionary - FIX THE DICTIONARY ACCESS
        if dict_type == "shared" and shared_dict_id:
            df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
        elif dict_type == "common":
            # For common dictionary - direct database access
            df = db_manager.get_user_words(chat_id, "common")
            print(f"Got common dictionary for repetition: {len(df)} words")
        else:
            # For personal dictionary - direct database access
            df = db_manager.get_user_words(chat_id, "personal")
            print(f"Got personal dictionary for repetition: {len(df)} words")
        
        if df is None or df.empty:
            # Use localized message with dictionary name
            if dict_type == "shared" and shared_dict_id:
                # Get shared dictionary name
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
                result = cursor.fetchone()
                dict_name = f"«{result[0] if result else ''}»" if result else get_text("shared_dictionary", chat_id)
                conn.close()
            else:
                dict_name = get_text(f"{dict_type}_dictionary", chat_id)
                
            bot.send_message(chat_id, f"{get_text('in', chat_id)} {dict_name} {get_text('no_words', chat_id)}", 
                             reply_markup=easy_level_keyboard(chat_id))
            return
            
        # Use the centralized start_repetition function
        success = start_repetition(chat_id, df)
        
        if not success:
            # Ensure we stay in the easy level menu
            bot.send_message(chat_id, get_text("error_activity", chat_id),
                             reply_markup=easy_level_keyboard(chat_id))
            
    except Exception as e:
        print(f"Error in repeat_words: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, get_text("error_activity", chat_id), 
                         reply_markup=easy_level_keyboard(chat_id))

def start_repetition(chat_id, df):
    """Start repetition activity"""
    if df.empty:
        return False
        
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
    
    # Localize the message
    message_text = get_text("select_translation", chat_id).format(word=word['word'])
    sent_message = bot.send_message(chat_id, message_text, reply_markup=markup)
    
    user_state[chat_id] = {
        "current_word": word,
        "message_id": sent_message.message_id,
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal")
    }
    return True

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_answer(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    # Разбираем данные из callback
    _, word, selected_tr = call.data.split('_')
    correct_tr = user_state[chat_id]["current_word"]['translation']
    
    # Проверяем ответ
    is_correct = selected_tr == correct_tr
    
    # Обновляем рейтинг слова
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    try:
        # Обновляем рейтинг в зависимости от типа словаря
        if dict_type == "shared" and shared_dict_id:
            # Для общего словаря
            try:
                word_id = db_manager.get_word_id_by_german(word)
                if word_id:
                    # Единый підхід до рейтингів для легкого рівня
                    rating_change = -0.1 if is_correct else 0.1
                    db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
                    print(f"Updated rating for shared dict word {word_id}: {rating_change}")
            except Exception as e:
                print(f"Error updating shared dict rating: {e}")
        else:
            # Для особистого словника
            from storage import get_dataframe, save_dataframe, get_user_file_path
            df = get_dataframe(chat_id)
            
            # Перевіряємо наявність потрібних колонок
            if 'word' in df.columns and 'priority' in df.columns:
                mask = df['word'] == word
                if mask.any():
                    rating_change = -0.1 if is_correct else 0.1
                    df.loc[mask, 'priority'] += rating_change
                    print(f"Updated rating for personal dict word {word}: {rating_change}")
                
                # Сохраняем DataFrame
                file_path, lang = get_user_file_path(chat_id) if dict_type == "personal" else (None, None)
                save_dataframe(chat_id, df, lang if lang else "common")
        
        if is_correct:
            from utils.language_utils import get_text
            bot.answer_callback_query(call.id, get_text("correct", chat_id))
        else:
            from utils.language_utils import get_text
            incorrect_msg = get_text("incorrect", chat_id) + f" {correct_tr}"
            bot.answer_callback_query(call.id, incorrect_msg)
            
        # Удаляем сообщение и продолжаем игру
        bot.delete_message(chat_id, call.message.message_id)
        repeat_words(call.message)
    except Exception as e:
        print(f"Error in handle_answer: {e}")
        import traceback
        traceback.print_exc()

@bot.message_handler(func=lambda message: is_command(message, "learn_articles"))
def learn_articles(message):
    """Handler for learning articles activity"""
    chat_id = message.chat.id
    start_article_activity(chat_id)

def start_article_activity(chat_id):
    """Start learning articles activity"""
    # Always check database for current dictionary type
    dict_type, shared_dict_id, _ = db_manager.get_user_dictionary_info(chat_id)
    
    # Get user language directly from database to ensure accuracy
    language = db_manager.get_user_language(chat_id) or "uk"
    
    # Update in-memory state to match database
    if chat_id in user_state:
        user_state[chat_id]["dict_type"] = dict_type
        user_state[chat_id]["language"] = language  # Always set language in state
        
        if dict_type == "shared" and shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        elif "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
    else:
        user_state[chat_id] = {
            "dict_type": dict_type,
            "language": language  # Always set language when creating new state
        }
        if dict_type == "shared" and shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    print(f"Debug: Starting article activity for user {chat_id} with dict_type={dict_type}, shared_dict_id={shared_dict_id}")
    
    try:
        # Отримуємо останнє слово, яке було показано, щоб не повторювати його
        last_word_id = user_state.get(chat_id, {}).get("last_article_word_id", None)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        language = db_manager.get_user_language(chat_id) or "uk"
        
        # Для персонального словника перевіряємо наявність таблиці користувача
        if dict_type == "personal":
            table_created, has_words = db_manager.ensure_user_table_exists(chat_id)
            if not has_words:
                # Якщо таблиця порожня або тільки створена
                from dictionary import return_to_appropriate_menu
                # DON'T send message here - let return_to_appropriate_menu do it
                return_to_appropriate_menu(chat_id, False, get_text("no_words_in_dictionary", chat_id))
                return False
        
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
            # IMPORTANT: Preserve shared_dict_id when sending error message
            preserved_dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
            preserved_shared_id = user_state.get(chat_id, {}).get("shared_dict_id")
            preserved_level = user_state.get(chat_id, {}).get("level", "easy")
            preserved_language = language  # Always preserve language
            
            from dictionary import return_to_appropriate_menu
            
            # Use clear_state with proper preservation
            clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
            
            # Manually restore shared_dict_id if it existed
            if chat_id in user_state:
                user_state[chat_id]["shared_dict_id"] = preserved_shared_id if preserved_shared_id else None
                user_state[chat_id]["dict_type"] = preserved_dict_type
                user_state[chat_id]["level"] = preserved_level
                user_state[chat_id]["language"] = preserved_language  # Restore language
                print(f"Debug: Preserved data for user {chat_id}: dict_type={preserved_dict_type}, shared_dict_id={preserved_shared_id}, language={preserved_language}")
            
            # Only send the message once through return_to_appropriate_menu
            return_to_appropriate_menu(chat_id, False, get_text("no_words_with_articles", chat_id, "У словнику немає слів з артиклями для вивчення."))
            return False
            
        # Вибираємо випадкове слово з результатів
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
        traceback.print_exc()
        bot.send_message(chat_id, get_text("error_occupated", chat_id))
        return False

@bot.callback_query_handler(func=lambda call: call.data.startswith("art_"))
def handle_article_answer(call):
    """Handle user's answer to article selection"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, get_text("error_exception", chat_id))
        return
    
    # Получаем данные из callback і стану
    user_article = call.data.split("_")[1]
    correct_article = user_state[chat_id].get("correct_article")
    word = user_state[chat_id].get("word")
    word_id = user_state[chat_id].get("word_id")
    
    # Проверяем ответ
    is_correct = user_article.lower() == correct_article.lower()
    
    # Обновляем рейтинг слова
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    try:
        if is_correct:
            bot.answer_callback_query(call.id, get_text("correct", chat_id))
            rating_change = -0.1  # Уменьшаем рейтинг для правильных ответов
        else:
            incorrect_msg = get_text("incorrect", chat_id) + f" {correct_article}"
            bot.answer_callback_query(call.id, incorrect_msg)
            rating_change = 0.1   # Увеличиваем рейтинг для неправильних відповідей
            
        # Обновляем рейтинг в зависимости от типа словаря
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
            print(f"Updated rating for shared dict word {word_id}: {rating_change}")
        else:
            db_manager.update_word_rating(chat_id, word_id, rating_change)
            print(f"Updated rating for personal dict word {word_id}: {rating_change}")
        
        # Удаляем сообщение і продовжуємо гру
        bot.delete_message(chat_id, call.message.message_id)
        start_article_activity(chat_id)
    except Exception as e:
        print(f"Error in handle_article_answer: {e}")
        import traceback
        traceback.print_exc()