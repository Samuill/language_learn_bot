# -*- coding: utf-8 -*-

"""
Обробники для активностей складного рівня.
"""

import random
import telebot
import pandas as pd
from config import bot, user_state
from utils import clear_state, main_menu_keyboard, hard_level_keyboard
from utils.input_handlers import safe_next_step_handler, sanitize_user_input  # Импорт новых утилит
import db_manager
from dictionary import return_to_appropriate_menu
from utils.language_utils import get_text, is_command 

# Додаємо константи для зміни рейтингу на високому рівні
HARD_RATING_DECREASE = -0.1    # Зменшення рейтингу при правильній відповіді
HARD_RATING_INCREASE = 0.2     # Збільшення рейтингу при неправильній відповіді

@bot.message_handler(func=lambda message: message.text == "🧩 Складна гра")
def hard_game(message):
    """Placeholder for a complex game (to be developed)"""
    chat_id = message.chat.id
    
    # Видаляємо повідомлення активності, зберігаючи тип словника та рівень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Повідомляємо, що функціонал у розробці
    bot.send_message(
        chat_id, 
        get_text("hard_game_developing", chat_id),
        reply_markup=hard_level_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📝 Введення слів")
def word_typing_game(message):
    """Game where user needs to type German translation of a Ukrainian word"""
    chat_id = message.chat.id
    
    # Видаляємо повідомлення активності, зберігаючи тип словника та рівень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Переконуємося, що рівень встановлено як "hard"
    if chat_id in user_state:
        user_state[chat_id]["level"] = "hard"
    else:
        dict_type = "personal"  # За замовчуванням
        user_state[chat_id] = {"dict_type": dict_type, "level": "hard"}
    
    # Отримуємо тип словника
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    try:
        # Отримуємо слова з словника користувача
        df = None
        if dict_type == "shared":
            if shared_dict_id:
                df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
            else:
                bot.send_message(chat_id, get_text("no_dictionary",chat_id), reply_markup=hard_level_keyboard())
                return
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        # Перевіряємо наявність слів
        if df is None or df.empty:
            dict_name = "спільному словнику" if dict_type == "shared" else "загальному словнику" if dict_type == "common" else "персональному словнику"
            bot.send_message(chat_id,get_text("in",chat_id) + f"{dict_name}"+ get_text("no_words",chat_id), reply_markup=hard_level_keyboard())
            return
            
        # Для складного рівня вибираємо слова з найвищим рейтингом
        # Сортуємо за рейтингом у спадаючому порядку (спочатку найважчі слова)
        df = df.sort_values(by="priority", ascending=False)
        
        # Беремо верхні 30% слів для складного рівня
        top_word_count = max(1, int(len(df) * 0.3))
        top_words_df = df.head(top_word_count)
        
        # Вибираємо випадкове слово з отриманих найтяжчих слів
        word_row = top_words_df.sample(1).iloc[0]
        
        # Зберігаємо стан
        user_state[chat_id] = {
            "dict_type": dict_type,
            "level": "hard",
            "game": "word_typing",
            "word_id": word_row['id'],
            "word": word_row['word'],
            "translation": word_row['translation'],
            "attempts": 0
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Відправляємо запит на переклад с использованием безопасного обработчика
        sent_message = bot.send_message(
            chat_id,
            get_text("enter_german_translation", chat_id).format(word=word_row['translation']),
            parse_mode="HTML"
        )
        
        # Используем безопасный обработчик вместо обычного
        safe_next_step_handler(sent_message, handle_word_typing_answer)

    except Exception as e:
        print(f"Error in word_typing_game: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id,get_text("error_occurred",chat_id), reply_markup=hard_level_keyboard())

def handle_word_typing_answer(message):
    """Handle user's answer in word typing game"""
    chat_id = message.chat.id
    
    # Проверка активности игры
    if chat_id not in user_state or user_state[chat_id].get("game") != "word_typing":
        bot.send_message(chat_id, get_text("game_not_stop",chat_id), reply_markup=hard_level_keyboard())
        return
    
    # Очищаем і безпечнo обробляємо ввід користувача
    user_answer = sanitize_user_input(message.text.strip().lower())
    
    # Получаем данные из состояния
    correct_word = user_state[chat_id]["word"]
    translation = user_state[chat_id]["translation"]
    word_id = user_state[chat_id]["word_id"]
    dict_type = user_state[chat_id]["dict_type"]
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    correct_answer = correct_word.strip().lower()
    
    # Проверяем ответ
    is_correct = user_answer == correct_answer
    
    try:
        # Правильна відповідь
        if is_correct:
            bot.send_message(
                chat_id,
                get_text("correct_translation", chat_id).format(translation=translation, word=correct_word),
                parse_mode="HTML"
            )
            
            # Оновлюємо рейтинг слова - для складного рівня зменшення рейтингу
            rating_change = HARD_RATING_DECREASE
        else:
            # Неправильна відповідь
            attempts = user_state[chat_id]["attempts"] + 1
            user_state[chat_id]["attempts"] = attempts
            
            # Оновлюємо рейтинг слова - для складного рівня збільшення рейтингу
            rating_change = HARD_RATING_INCREASE
            
            # Якщо це вже третя спроба, показуємо правильну відповідь і продовжуємо
            if attempts >= 2:
                bot.send_message(
                    chat_id,
                    get_text("incorrect_translation_final", chat_id).format(translation=translation, word=correct_word),
                    parse_mode="HTML"
                )
                # Продовжуємо з новим словом
                bot.send_message(chat_id, get_text("continue_game",chat_id))
                word_typing_game(message)
                return
            else:
                # Даємо ще одну спробу
                sent_message = bot.send_message(
                    chat_id, 
                    get_text("incorrect_try_again", chat_id).format(translation=translation),
                    parse_mode="HTML"
                )
                bot.register_next_step_handler(sent_message, handle_word_typing_answer)
                return
        
        # Застосовуємо зміну рейтингу відповідно до типу словника
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
            print(f"Updated shared dict rating for word {word_id}: {rating_change}")
        else:
            db_manager.update_word_rating(chat_id, word_id, rating_change)
            print(f"Updated personal dict rating for word {word_id}: {rating_change}")
        
        # Продовжуємо з новим словом
        bot.send_message(chat_id, get_text("continue_game",chat_id))
        word_typing_game(message)
    except Exception as e:
        print(f"Error processing answer: {e}")
        import traceback
        traceback.print_exc()

@bot.message_handler(func=lambda message: message.text == "🏷️ Введення артиклів")
def article_typing_game(message):
    """Game where user needs to type correct article for a German word"""
    chat_id = message.chat.id
    
    # Видаляємо повідомлення активності, зберігаючи тип словника та рівень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Переконуємося, що рівень встановлено як "hard"
    if chat_id in user_state:
        user_state[chat_id]["level"] = "hard"
    else:
        dict_type = "personal"  # За замовчуванням
        user_state[chat_id] = {"dict_type": dict_type, "level": "hard"}
    
    # Отримуємо тип словника
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    try:
        # Отримуємо випадкове слово з артиклем з словника користувача
        import db_manager
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        language = db_manager.get_user_language(chat_id) or "uk"
        results = None
        
        # Отримання слів залежно від типу словника, з фокусом на слова з високим рейтингом
        if dict_type == "shared" and shared_dict_id:
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation, 
                   COALESCE(sd.user_{chat_id}, 0.0) as rating
            FROM shared_dict_{shared_dict_id} sd
            JOIN words w ON sd.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            ORDER BY sd.user_{chat_id} DESC
            LIMIT 30
            """
            print(f"DEBUG query for shared dictionary: {query}")
        
        elif dict_type == "common":
            # Для загального словника рейтинг імітуємо випадковий
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation, 
                   RANDOM() as rating
            FROM words w
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            ORDER BY rating DESC
            LIMIT 30
            """
        else:
            # Для персонального словника, беремо слова з найвищим рейтингом
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation, 
                   u.rating
            FROM user_{chat_id} u
            JOIN words w ON u.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            ORDER BY u.rating DESC
            LIMIT 30
            """
            
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Вибираємо випадкове слово з топ-слів (перші 30%)
        if results:
            top_results_count = max(1, int(len(results) * 0.3))
            top_results = results[:top_results_count]
            result = random.choice(top_results)
        else:
            # Якщо результатів немає, повідомляємо про це
            bot.send_message(chat_id, get_text("in"+"dictionary"+"", chat_id),
                           reply_markup=hard_level_keyboard())
            conn.close()
            return
        
        # Розбираємо результат
        word_id, word, correct_article, article_id, translation, rating = result
        
        # Зберігаємо стан
        user_state[chat_id] = {
            "word_id": word_id,
            "word": word,
            "correct_article": correct_article,
            "dict_type": dict_type,
            "level": "hard",
            "game": "article_typing",
            "translation": translation,
            "attempts": 0,
            "rating": rating  # Зберігаємо рейтинг для відстеження
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Отримуємо пояснення падежу
        case_explanation = db_manager.get_case_explanation("Dativ" if random.random() < 0.5 else "Akkusativ", language)
        
        # Відправляємо запит на введення артикля з поясненням падежу
        message_text = get_text("enter_article", chat_id).format(
            word=word, 
            translation=translation, 
            case_explanation=case_explanation
        )
        
        sent_message = bot.send_message(
            chat_id,
            message_text,
            parse_mode="HTML"
        )
        
        # Реєструємо обробник для наступного повідомлення
        bot.register_next_step_handler(sent_message, handle_article_typing_answer)
        
        conn.close()
        
    except Exception as e:
        print(f"Error in article_typing_game: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, get_text("error_occurred",chat_id), reply_markup=hard_level_keyboard())

def handle_article_typing_answer(message):
    """Handle user's answer in article typing game"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є дані гри у стані користувача
    if chat_id not in user_state or user_state[chat_id].get("game") != "article_typing":
        bot.send_message(chat_id, get_text("game_not_stop",chat_id), reply_markup=hard_level_keyboard())
        return
    
    # Список команд меню, які потрібно обробляти як команди, а не відповіді
    menu_commands = [
        "🧩 Складна гра", "📝 Введення слів", "🏷️ Введення артиклів", 
        "↩️ Повернутися до головного меню", "🟢 Легкий рівень", "🟠 Середній рівень", 
        "🔴 Складний рівень", "👤 Персональний словник", "👥 Спільний словник", 
        "➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити"
    ]
    
    # Якщо користувач ввів команду меню, завершити гру і обробити команду
    if message.text in menu_commands:
        # Якщо це команда в межах меню складного рівня, зберігаємо рівень
        preserve_level = message.text in ["🧩 Складна гра", "📝 Введення слів", "🏷️ Введення артиклів"]
        
        # Визначаємо, яке повідомлення показати
        if preserve_level:
            reply_markup = hard_level_keyboard()
            msg_text = get_text("game_cancelled", chat_id) 
        else:
            reply_markup = main_menu_keyboard(chat_id)
            msg_text = get_text("game_cancelled", chat_id)
            
        # Повідомлення про завершення гри
        bot.send_message(
            chat_id,
            msg_text,
            reply_markup=reply_markup
        )
        
        # Очищаємо стан користувача, зберігаючи тип словника та можливо рівень
        clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=preserve_level)
        
        # Створюємо новий об'єкт повідомлення для передачі іншому обробнику
        from telebot.types import Message
        
        new_message = Message(
            message_id=message.message_id,
            from_user=message.from_user,
            date=message.date,
            chat=message.chat,
            content_type='text',
            options={},
            json_string=None
        )
        new_message.text = message.text
        
        # Запускаємо бота для обробки команди
        bot.process_new_messages([new_message])
        return
    
    # Отримуємо дані гри
    correct_article = user_state[chat_id]["correct_article"]
    word = user_state[chat_id]["word"]
    word_id = user_state[chat_id]["word_id"]
    dict_type = user_state[chat_id]["dict_type"]
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    # Обробляємо введену відповідь (видаляємо пробіли та переводимо в нижній регістр)
    user_answer = message.text.strip().lower()
    
    # Перевіряємо відповідь
    if user_answer == correct_article.lower():
        # Правильна відповідь
        bot.send_message(
            chat_id,
            get_text("correct_article_answer", chat_id).format(word=word, article=correct_article),
            parse_mode="HTML"
        )
        
        # Оновлюємо рейтинг слова - для складного рівня більше зниження рейтингу
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, +0.2, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, -0.1)
        
        # Продовжуємо з новим словом
        bot.send_message(chat_id, get_text("continue_game",chat_id))
        article_typing_game(message)
    else:
        # Неправильна відповідь
        attempts = user_state[chat_id]["attempts"] + 1
        user_state[chat_id]["attempts"] = attempts
        
        # Оновлюємо рейтинг слова - для складного рівня менший штраф за помилку
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, 0.2, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, 0.2)
        
        # Якщо це вже друга спроба, показуємо правильну відповідь і продовжуємо
        if attempts >= 2:  # Змінено з 3 на 2 спроби
            bot.send_message(
                chat_id,
                get_text("incorrect_article_final", chat_id).format(word=word, article=correct_article),
                parse_mode="HTML"
            )
            # Продовжуємо з новим словом
            bot.send_message(chat_id, get_text("continue_game",chat_id))
            article_typing_game(message)
        else:
            # Даємо ще одну спробу
            sent_message = bot.send_message(
                chat_id, 
                get_text("incorrect_article_retry", chat_id).format(word=word),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(sent_message, handle_article_typing_answer)
