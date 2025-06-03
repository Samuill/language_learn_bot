# -*- coding: utf-8 -*-

"""
Обробники для активностей складного рівня.
"""

import random
import telebot
import pandas as pd
from config import bot, user_state
from utils import clear_state, main_menu_keyboard, hard_level_keyboard
import db_manager
from dictionary import return_to_appropriate_menu

@bot.message_handler(func=lambda message: message.text == "🧩 Складна гра")
def hard_game(message):
    """Placeholder for a complex game (to be developed)"""
    chat_id = message.chat.id
    
    # Видаляємо повідомлення активності, зберігаючи тип словника та рівень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Повідомляємо, що функціонал у розробці
    bot.send_message(
        chat_id, 
        "🚧 Складна гра знаходиться у розробці.\nСпробуйте інші активності складного рівня.",
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
        # Отримуємо випадкове слово з словника користувача
        df = None
        if dict_type == "shared":
            if shared_dict_id:
                df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
            else:
                bot.send_message(chat_id, "❌ Не вказано спільний словник", reply_markup=hard_level_keyboard())
                return
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        # Перевіряємо наявність слів
        if df is None or df.empty:
            dict_name = "спільному словнику" if dict_type == "shared" else "загальному словнику" if dict_type == "common" else "персональному словнику"
            bot.send_message(chat_id, f"📭 У {dict_name} ще немає доданих слів.", reply_markup=hard_level_keyboard())
            return
        
        # Вибираємо випадкове слово
        word_row = df.sample(1).iloc[0]
        
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
        
        # Відправляємо запит на переклад
        sent_message = bot.send_message(
            chat_id,
            f"📝 Введіть німецький переклад слова:\n\n<b>{word_row['translation']}</b>",
            parse_mode="HTML"
        )
        
        # Реєструємо обробник для наступного повідомлення
        bot.register_next_step_handler(sent_message, handle_word_typing_answer)
        
    except Exception as e:
        print(f"Error in word_typing_game: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Помилка при запуску гри.", reply_markup=hard_level_keyboard())

def handle_word_typing_answer(message):
    """Handle user's answer in word typing game"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є дані гри у стані користувача
    if chat_id not in user_state or user_state[chat_id].get("game") != "word_typing":
        bot.send_message(chat_id, "❌ Помилка: сесія гри закінчилась.", reply_markup=hard_level_keyboard())
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
            msg_text = "🚫 Гра перервана. Переходимо до іншої активності..."
        else:
            reply_markup = main_menu_keyboard(chat_id)
            msg_text = "🚫 Гра перервана. Виконую команду..."
            
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
    correct_word = user_state[chat_id]["word"]
    translation = user_state[chat_id]["translation"]
    word_id = user_state[chat_id]["word_id"]
    dict_type = user_state[chat_id]["dict_type"]
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    # Обробляємо введену відповідь (видаляємо пробіли та переводимо в нижній регістр)
    user_answer = message.text.strip().lower()
    correct_answer = correct_word.strip().lower()
    
    # Перевіряємо відповідь
    if user_answer == correct_answer:
        # Правильна відповідь
        bot.send_message(
            chat_id,
            f"✅ Правильно!\n\n<b>{translation}</b> = <b>{correct_word}</b>",
            parse_mode="HTML"
        )
        
        # Оновлюємо рейтинг слова
        if dict_type == "shared":
            if shared_dict_id:
                db_manager.update_word_rating_shared_dict(chat_id, word_id, -0.1, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, -0.1)
        
        # Продовжуємо з новим словом
        bot.send_message(chat_id, "Продовжуємо...")
        word_typing_game(message)
    else:
        # Неправильна відповідь
        attempts = user_state[chat_id]["attempts"] + 1
        user_state[chat_id]["attempts"] = attempts
        
        # Оновлюємо рейтинг слова
        if dict_type == "shared":
            if shared_dict_id:
                db_manager.update_word_rating_shared_dict(chat_id, word_id, 0.1, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, 0.1)
        
        # Якщо це вже третя спроба, показуємо правильну відповідь і продовжуємо
        if attempts >= 2:
            bot.send_message(
                chat_id,
                f"❌ Неправильно!\n\nПравильна відповідь: <b>{correct_word}</b>\n\n<b>{translation}</b> = <b>{correct_word}</b>",
                parse_mode="HTML"
            )
            # Продовжуємо з новим словом
            bot.send_message(chat_id, "Продовжуємо...")
            word_typing_game(message)
        else:
            # Даємо ще одну спробу
            sent_message = bot.send_message(
                chat_id, 
                f"❌ Неправильно! Спробуйте ще раз.\n\n<b>{translation}</b>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(sent_message, handle_word_typing_answer)

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
        
        # Отримання слів залежно від типу словника
        if dict_type == "shared" and shared_dict_id:
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
            FROM shared_dict_{shared_dict_id} sd
            JOIN words w ON sd.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 20
            """
        elif dict_type == "common":
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
            FROM words w
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 20
            """
        else:
            # Для персонального словника
            query = f"""
            SELECT w.id, w.word, a.article, a.id as article_id, w.{language}_tran as translation
            FROM user_{chat_id} u
            JOIN words w ON u.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE w.article_id != 4 AND w.article_id IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 15
            """
            
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            bot.send_message(chat_id, "📭 У словнику немає слів з артиклями для вивчення.", 
                           reply_markup=hard_level_keyboard())
            return
        
        # Вибираємо випадкове слово
        import random
        result = random.choice(results)
        
        if dict_type == "personal":
            word_id, word, correct_article, article_id, translation = result[:5]
        else:
            word_id, word, correct_article, article_id, translation = result[:5]
        
        # Зберігаємо стан
        user_state[chat_id] = {
            "word_id": word_id,
            "word": word,
            "correct_article": correct_article,
            "dict_type": dict_type,
            "level": "hard",
            "game": "article_typing",
            "translation": translation,
            "attempts": 0
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Відправляємо запит на введення артикля
        sent_message = bot.send_message(
            chat_id,
            f"🏷️ Введіть артикль (der, die, das) для слова:\n\n<b>{word}</b>\n\n<i>Переклад: {translation}</i>",
            parse_mode="HTML"
        )
        
        # Реєструємо обробник для наступного повідомлення
        bot.register_next_step_handler(sent_message, handle_article_typing_answer)
        
    except Exception as e:
        print(f"Error in article_typing_game: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Помилка при запуску гри.", reply_markup=hard_level_keyboard())

def handle_article_typing_answer(message):
    """Handle user's answer in article typing game"""
    chat_id = message.chat.id
    
    # Перевіряємо, чи є дані гри у стані користувача
    if chat_id not in user_state or user_state[chat_id].get("game") != "article_typing":
        bot.send_message(chat_id, "❌ Помилка: сесія гри закінчилась.", reply_markup=hard_level_keyboard())
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
            msg_text = "🚫 Гра перервана. Переходимо до іншої активності..."
        else:
            reply_markup = main_menu_keyboard(chat_id)
            msg_text = "🚫 Гра перервана. Виконую команду..."
            
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
            f"✅ Правильно! Слово <b>{word}</b> має артикль <b>{correct_article}</b>.",
            parse_mode="HTML"
        )
        
        # Оновлюємо рейтинг слова
        if dict_type == "shared":
            if shared_dict_id:
                db_manager.update_word_rating_shared_dict(chat_id, word_id, -0.1, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, -0.1)
        
        # Продовжуємо з новим словом
        bot.send_message(chat_id, "Продовжуємо...")
        article_typing_game(message)
    else:
        # Неправильна відповідь
        attempts = user_state[chat_id]["attempts"] + 1
        user_state[chat_id]["attempts"] = attempts
        
        # Оновлюємо рейтинг слова
        if dict_type == "shared":
            if shared_dict_id:
                db_manager.update_word_rating_shared_dict(chat_id, word_id, 0.1, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, 0.1)
        
        # Якщо це вже третя спроба, показуємо правильну відповідь і продовжуємо
        if attempts >= 2:
            bot.send_message(
                chat_id,
                f"❌ Неправильно!\n\nПравильна відповідь: <b>{correct_article}</b>\n\nСлово <b>{word}</b> має артикль <b>{correct_article}</b>.",
                parse_mode="HTML"
            )
            # Продовжуємо з новим словом
            bot.send_message(chat_id, "Продовжуємо...")
            article_typing_game(message)
        else:
            # Даємо ще одну спробу
            sent_message = bot.send_message(
                chat_id, 
                f"❌ Неправильно! Спробуйте ще раз.\n\nВведіть артикль для слова <b>{word}</b>",
                parse_mode="HTML"
            )
            bot.register_next_step_handler(sent_message, handle_article_typing_answer)
