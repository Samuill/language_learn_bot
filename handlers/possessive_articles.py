# -*- coding: utf-8 -*-

"""
Handler for possessive article exercises.
"""

import random
import telebot
import sqlite3  # Add missing import for sqlite3
from config import bot, user_state
from utils import clear_state, easy_level_keyboard, main_menu_keyboard  # Import main_menu_keyboard
import db_manager

@bot.message_handler(func=lambda message: message.text in ["🧩 Вивчати присвійні займенники", "🧩 Вивчати присвійні займенники (середній)", "🧩 Вивчати присвійні займенники (складний)"])
def start_possessive_exercise_handler(message):
    """Handle possessive pronouns exercises at different difficulty levels"""
    # Визначаємо рівень складності за текстом кнопки
    if message.text == "🧩 Вивчати присвійні займенники":
        difficulty = "easy"
    elif message.text == "🧩 Вивчати присвійні займенники (середній)":
        difficulty = "medium" 
    else:
        difficulty = "hard"
        
    start_possessive_exercise(message.chat.id, difficulty)

def start_possessive_exercise(chat_id, difficulty="easy"):
    """Start an exercise for learning German possessive articles"""
    # Clear current state but preserve dictionary type
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Set the exercise type in user state
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    user_state[chat_id] = {
        "dict_type": dict_type,
        "level": difficulty,
        "exercise": "possessive",
        "difficulty": difficulty,
        "attempts": 0,
        "active_messages": []  # Додаємо список для відстеження активних повідомлень
    }
    
    if shared_dict_id:
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    # Start the first exercise
    generate_possessive_exercise(chat_id)

def get_case_name_in_ukrainian(case_name):
    """Convert German case names to Ukrainian"""
    case_translations = {
        "Nominativ": "Називний",
        "Akkusativ": "Знахідний",
        "Dativ": "Давальний",
        "Genitiv": "Родовий"
    }
    return case_translations.get(case_name, case_name)

def get_pronoun_translation(pronoun):
    """Get Ukrainian translation of German pronouns"""
    pronoun_translations = {
        "ich": "я",
        "du": "ти",
        "er": "він",
        "es": "воно",
        "sie (singular)": "вона",
        "wir": "ми",
        "ihr": "ви",
        "sie (plural)": "вони",
        "Sie": "Ви (ввічливе)"
    }
    return pronoun_translations.get(pronoun, pronoun)

def get_case_explanation(case, language="uk"):
    """Get explanation for grammatical cases"""
    explanations = {
        "Nominativ": {
            "uk": "Називний відмінок (Nominativ) використовується для підмета речення і відповідає на питання 'хто/що?'",
            "ru": "Именительный падеж (Nominativ) используется для подлежащего и отвечает на вопрос 'кто/что?'"
        },
        "Akkusativ": {
            "uk": "Знахідний відмінок (Akkusativ) використовується для прямого додатка і відповідає на питання 'кого/що?'",
            "ru": "Винительный падеж (Akkusativ) используется для прямого дополнения и отвечает на вопрос 'кого/что?'"
        },
        "Dativ": {
            "uk": "Давальний відмінок (Dativ) використовується для непрямого додатка і відповідає на питання 'кому/чому?'",
            "ru": "Дательный падеж (Dativ) используется для непрямого дополнения и отвечает на вопрос 'кому/чему?'"
        }
    }
    
    return explanations.get(case, {}).get(language, explanations[case]["uk"])

def generate_possessive_exercise(chat_id):
    """Generate a new possessive article exercise"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Get user language
    language = db_manager.get_user_language(chat_id) or "uk"
    
    # Get difficulty level
    difficulty = user_state[chat_id].get("difficulty", "easy")
    
    # Filter available cases based on difficulty level
    allowed_cases = []
    if difficulty == "easy":
        allowed_cases = ["Nominativ"]
    elif difficulty == "medium":
        allowed_cases = ["Nominativ", "Akkusativ"]
    else:  # hard
        allowed_cases = ["Akkusativ", "Dativ"]
    
    # Step 1: Get a random noun with gender info
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    # Перевіряємо наявність таблиці користувача для персонального словника
    if dict_type == "personal":
        table_created, has_words = db_manager.ensure_user_table_exists(chat_id)
        if not has_words:
            bot.send_message(
                chat_id, 
                "📭 У персональному словнику ще немає доданих слів. Спочатку додайте слова.",
                reply_markup=easy_level_keyboard()
            )
            clear_state(chat_id)
            conn.close()
            return
    
    # Query depends on dictionary type
    try:
        if dict_type == "shared" and shared_dict_id:
            # Check if shared dictionary table exists
            cursor.execute(f"""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='shared_dict_{shared_dict_id}'
            """)
            if not cursor.fetchone():
                bot.send_message(
                    chat_id, 
                    "❌ Помилка: спільний словник не знайдено.",
                    reply_markup=easy_level_keyboard()
                )
                clear_state(chat_id)
                conn.close()
                return
                
            cursor.execute(f'''
            SELECT w.id, w.word, a.article, w.{language}_tran 
            FROM shared_dict_{shared_dict_id} sd
            JOIN words w ON sd.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE a.article IN ('der', 'die', 'das') AND w.{language}_tran IS NOT NULL
            ORDER BY RANDOM() LIMIT 1
            ''')
            
        elif dict_type == "common":
            cursor.execute(f'''
            SELECT w.id, w.word, a.article, w.{language}_tran 
            FROM words w
            JOIN article a ON w.article_id = a.id
            WHERE a.article IN ('der', 'die', 'das') AND w.{language}_tran IS NOT NULL
            ORDER BY RANDOM() LIMIT 1
            ''')
            
        else:  # personal
            cursor.execute(f'''
            SELECT w.id, w.word, a.article, w.{language}_tran 
            FROM user_{chat_id} u
            JOIN words w ON u.word_id = w.id
            JOIN article a ON w.article_id = a.id
            WHERE a.article IN ('der', 'die', 'das') AND w.{language}_tran IS NOT NULL
            ORDER BY RANDOM() LIMIT 1
            ''')
        
        results = cursor.fetchall()
        
        # If no words found with articles, show message
        if not results:
            bot.send_message(
                chat_id, 
                "📭 Недостатньо слів з артиклями у вашому словнику для цієї вправи.",
                reply_markup=easy_level_keyboard()
            )
            clear_state(chat_id)
            conn.close()
            return
        
        word_id, word, article, translation = results[0]
        
    except sqlite3.OperationalError as e:
        # Handle specific SQL errors for tables not existing
        print(f"Database error in generate_possessive_exercise: {e}")
        if "no such table" in str(e):
            bot.send_message(
                chat_id, 
                "📭 Спочатку додайте слова до свого словника, щоб почати виконувати вправи.",
                reply_markup=easy_level_keyboard()
            )
        else:
            bot.send_message(
                chat_id, 
                "❌ Помилка при отриманні даних з бази. Спробуйте пізніше.",
                reply_markup=easy_level_keyboard()
            )
        clear_state(chat_id)
        conn.close()
        return
    except Exception as e:
        print(f"Error in generate_possessive_exercise: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(
            chat_id,
            "❌ Помилка при генерації вправи. Спробуйте пізніше.",
            reply_markup=easy_level_keyboard()
        )
        clear_state(chat_id)
        conn.close()
        return
    
    # Determine gender from article
    gender = None
    if article == "der":
        gender = "maskulin"
    elif article == "die":
        gender = "feminin"
    elif article == "das":
        gender = "neutrum"
    
    # Step 2: Select a random pronoun
    pronouns = ["ich", "du", "er", "es", "sie (singular)", "wir", "ihr", "sie (plural)", "Sie"]
    pronoun = random.choice(pronouns)
    
    # Step 3: Select a random case from allowed cases
    case = random.choice(allowed_cases)
    
    # Step 4: Determine if singular or plural
    # For this exercise, we'll stick with singular for simplicity
    number = "singular"
    
    # Step 5: Get the correct possessive form
    cursor.execute('''
    SELECT form FROM possessive_articles
    WHERE pronoun = ? AND case_name = ? AND gender = ? AND number = ?
    ''', (pronoun, case, gender, number))
    
    correct_form_result = cursor.fetchone()
    if not correct_form_result:
        # Fallback if form not found
        bot.send_message(
            chat_id,
            "❌ Помилка: не вдалося знайти правильну форму присвійного займенника.",
            reply_markup=easy_level_keyboard()
        )
        clear_state(chat_id)
        conn.close()
        return
    
    correct_form = correct_form_result[0]
    
    # Step 6: Get distractors (valid forms but incorrect for this case)
    cursor.execute('''
    SELECT form FROM possessive_articles
    WHERE form != ? AND pronoun = ?
    ORDER BY RANDOM() LIMIT 3
    ''', (correct_form, pronoun))
    
    distractors = [row[0] for row in cursor.fetchall()]
    
    # If we don't have enough distractors, add some from other pronouns
    if len(distractors) < 3:
        cursor.execute('''
        SELECT form FROM possessive_articles
        WHERE form != ? AND pronoun != ?
        ORDER BY RANDOM() LIMIT ?
        ''', (correct_form, pronoun, 3 - len(distractors)))
        
        distractors.extend([row[0] for row in cursor.fetchall()])
    
    # Step 7: Create the options for the user
    options = distractors + [correct_form]
    random.shuffle(options)
    
    # Save exercise data to user state
    user_state[chat_id].update({
        "word": word,
        "pronoun": pronoun,
        "case": case,
        "gender": gender,
        "number": number,
        "correct_form": correct_form,
        "options": options,
        "translation": translation,
        "attempts": 0  # Reset attempts for new exercise
    })
    
    # Step 8: Create the inline keyboard with options
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    button_data = []
    
    for i, option in enumerate(options):
        button_data.append(telebot.types.InlineKeyboardButton(
            option,
            callback_data=f"poss_{i}"
        ))
    
    markup.add(*button_data)
    
    # Step 9: Send the question to the user
    pronoun_display = get_pronoun_translation(pronoun)
    case_display = get_case_name_in_ukrainian(case)
    case_explanation = get_case_explanation(case, language)
    
    message_text = (
        f"🧩 Виберіть правильний присвійний займенник:\n\n"
        f"[{pronoun_display} - <b>{pronoun}</b>] ____ <b>{word}</b> (<b>{case}</b> - {case_display})\n\n"
        f"<i>Переклад: {translation}</i>"
    )
    
    # Add case explanation for all levels
    message_text += f"\n\n<i>{case_explanation}</i>"
    
    sent_message = bot.send_message(
        chat_id,
        message_text,
        parse_mode="HTML",
        reply_markup=markup
    )
    
    # Зберігаємо ID повідомлення для можливості видалення
    if "active_messages" not in user_state[chat_id]:
        user_state[chat_id]["active_messages"] = []
    user_state[chat_id]["active_messages"].append(sent_message.message_id)
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("poss_"))
def handle_possessive_answer(call):
    """Handle user's answer to the possessive article exercise"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_state or user_state[chat_id].get("exercise") != "possessive":
        bot.answer_callback_query(call.id, "❌ Помилка: вправа не активна")
        return
    
    # Get the selected option
    selected_index = int(call.data.split("_")[1])
    selected_form = user_state[chat_id]["options"][selected_index]
    
    # Get the correct answer
    correct_form = user_state[chat_id]["correct_form"]
    
    # Check if the answer is correct
    is_correct = selected_form == correct_form
    
    # Get exercise data
    word = user_state[chat_id]["word"]
    word_id = user_state[chat_id].get("word_id")
    pronoun = user_state[chat_id]["pronoun"]
    case = user_state[chat_id]["case"]
    pronoun_display = get_pronoun_translation(pronoun)
    case_display = get_case_name_in_ukrainian(case)
    
    # Update attempts
    user_state[chat_id]["attempts"] += 1
    attempts = user_state[chat_id]["attempts"]
    
    # Для середнього рівня не оновлюємо рейтинг
    difficulty = user_state[chat_id].get("difficulty", "easy")
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    # Оновлення рейтингу, але тільки якщо це не середній рівень
    if difficulty != "medium" and word_id:
        try:
            import db_manager
            rating_change = -0.1 if is_correct else 0.1
            
            print(f"DEBUG: Updating rating for {dict_type} dictionary, word_id={word_id}, change={rating_change}")
            
            if dict_type == "shared" and shared_dict_id:
                db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
            elif dict_type == "personal":
                db_manager.update_word_rating(chat_id, word_id, rating_change)
        except Exception as e:
            print(f"ERROR updating word rating in possessive exercise: {e}")
    elif difficulty == "medium":
        print(f"DEBUG: Skipping rating update for medium difficulty exercise")
    
    if is_correct:
        # Show success message
        bot.answer_callback_query(call.id, "✅ Правильно!")
        
        # Edit message with correct answer
        bot.edit_message_text(
            f"✅ Правильно!\n\n"
            f"[{pronoun_display} - <b>{pronoun}</b>] <b>{correct_form}</b> <b>{word}</b> ({case_display})",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
        
        # Generate new exercise after a short delay
        import threading
        threading.Timer(1.5, lambda: generate_possessive_exercise(chat_id)).start()
    else:
        # Show failure message
        bot.answer_callback_query(call.id, "❌ Неправильно!")
        
        if attempts >= 2:  # Змінено з 3 на 2 спроби
            # After two wrong attempts, show correct answer
            bot.edit_message_text(
                f"❌ Неправильно!\n\n"
                f"Правильна відповідь: <b>{correct_form}</b>\n\n"
                f"[{pronoun_display} - <b>{pronoun}</b>] <b>{correct_form}</b> <b>{word}</b> ({case_display})",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
            
            # Generate new exercise after a short delay
            import threading
            threading.Timer(2.5, lambda: generate_possessive_exercise(chat_id)).start()
        else:
            # Let the user try again, highlight the wrong answer
            markup = call.message.reply_markup
            for i, btn in enumerate(markup.keyboard[0]):
                if btn.callback_data == call.data:
                    markup.keyboard[0][i].text += " ❌"
            
            bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup
            )

# Додаємо обробник загальних команд меню для виходу з гри
@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("exercise") == "possessive" and 
                    message.text in ["↩️ Повернутися до головного меню", "🟢 Легкий рівень", "🟠 Середній рівень", "🔴 Складний рівень"])
def exit_possessive_exercise(message):
    """Handle exit from possessive exercise"""
    chat_id = message.chat.id
    
    # Видаляємо всі активні повідомлення гри
    if "active_messages" in user_state[chat_id]:
        for msg_id in user_state[chat_id]["active_messages"]:
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception as e:
                print(f"Error deleting message {msg_id}: {e}")
    
    # Визначаємо, куди повертатися
    if message.text == "↩️ Повернутися до головного меню":
        clear_state(chat_id, preserve_dict_type=True)
        bot.send_message(chat_id, "Головне меню:", reply_markup=main_menu_keyboard(chat_id))
    elif message.text == "🟢 Легкий рівень":
        clear_state(chat_id, preserve_dict_type=True)
        from utils import easy_level_keyboard
        bot.send_message(chat_id, "🟢 Легкий рівень - оберіть активність:", reply_markup=easy_level_keyboard())
    elif message.text == "🟠 Середній рівень":
        clear_state(chat_id, preserve_dict_type=True)
        from utils import medium_level_keyboard
        bot.send_message(chat_id, "🟠 Середній рівень - оберіть активність:", reply_markup=medium_level_keyboard())
    elif message.text == "🔴 Складний рівень":
        clear_state(chat_id, preserve_dict_type=True)
        from utils import hard_level_keyboard
        bot.send_message(chat_id, "🔴 Складний рівень - оберіть активність:", reply_markup=hard_level_keyboard())
