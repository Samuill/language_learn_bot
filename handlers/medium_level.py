# -*- coding: utf-8 -*-

"""
Обробники для активностей середнього рівня складності.
"""

import random
import string
import telebot
import pandas as pd
from config import bot, user_state
from utils import clear_state, medium_level_keyboard, main_menu_keyboard
import db_manager
from utils.input_handlers import safe_next_step_handler, sanitize_user_input, is_menu_navigation_command, handle_exit_from_activity
from utils.language_utils import get_text
# Константи для зміни рейтингу
MEDIUM_RATING_DECREASE = -0.1  # Зменшення рейтингу при правильній відповіді
MEDIUM_RATING_INCREASE = 0.1   # Збільшення рейтингу при неправильній відповіді

# Функція для створення неправильних версій слова
def create_misspelled_versions(word, num_versions=3):
    """Create believable misspelled versions of a German word"""
    misspelled = []
    original = word
    word = word.lower()
    
    # Список можливих перетворень для створення помилок написання
    transforms = [
        # Подвійні/одинарні приголосні
        lambda w: w.replace('mm', 'm') if 'mm' in w else w.replace('m', 'mm', 1),
        lambda w: w.replace('nn', 'n') if 'nn' in w else w.replace('n', 'nn', 1),
        lambda w: w.replace('ss', 's') if 'ss' in w else w.replace('s', 'ss', 1),
        lambda w: w.replace('ll', 'l') if 'll' in w else w.replace('l', 'll', 1),
        lambda w: w.replace('tt', 't') if 'tt' in w else w.replace('t', 'tt', 1),
        
        # Заміна умлаутів або додавання/видалення e після голосної
        lambda w: w.replace('ä', 'a') if 'ä' in w else w.replace('a', 'ä', 1),
        lambda w: w.replace('ö', 'o') if 'ö' in w else w.replace('o', 'ö', 1),
        lambda w: w.replace('ü', 'u') if 'ü' in w else w.replace('u', 'ü', 1),
        lambda w: w.replace('ä', 'ae') if 'ä' in w else w.replace('ae', 'ä'),
        lambda w: w.replace('ö', 'oe') if 'ö' in w else w.replace('oe', 'ö'),
        lambda w: w.replace('ü', 'ue') if 'ü' in w else w.replace('ue', 'ü'),
        
        # Помилки з великою буквою
        lambda w: w.capitalize() if not w[0].isupper() else w[0].lower() + w[1:],
        
        # Заміна v/f, z/tz, s/ss
        lambda w: w.replace('v', 'f') if 'v' in w else w.replace('f', 'v', 1),
        lambda w: w.replace('tz', 'z') if 'tz' in w else w.replace('z', 'tz', 1),
        lambda w: w.replace('ss', 'ß') if 'ss' in w else w.replace('ß', 'ss'),
        
        # Вилучення чи додавання букв
        lambda w: w[:-1] if len(w) > 3 else w,
        lambda w: w[1:] if len(w) > 3 else w,
        lambda w: w + random.choice('aeiou') if len(w) > 2 else w,
        lambda w: w[:int(len(w)/2)] + random.choice('aeiou') + w[int(len(w)/2):] if len(w) > 2 else w
    ]
    
    # Зберігаємо оригінальний регістр
    is_capitalized = original[0].isupper() if len(original) > 0 else False
    
    # Створюємо неправильні варіанти
    attempts = 0
    while len(misspelled) < num_versions and attempts < 20:
        attempts += 1
        
        # Вибираємо випадкову трансформацію
        transform = random.choice(transforms)
        misspelled_word = transform(word)
        
        # При необхідності відновлюємо оригінальну капіталізацію
        if is_capitalized and not misspelled_word[0].isupper():
            misspelled_word = misspelled_word.capitalize()
        
        # Якщо створений варіант відрізняється від оригіналу та унікальний
        if misspelled_word != original and misspelled_word not in misspelled:
            misspelled.append(misspelled_word)
    
    # Якщо не вдалося згенерувати достатньо варіантів, додаємо прості заміни
    while len(misspelled) < num_versions:
        # Заміна випадкової літери
        if len(original) > 2:
            pos = random.randint(1, len(original)-1)
            new_char = random.choice(string.ascii_lowercase)
            misspelled_word = original[:pos] + new_char + original[pos+1:]
            if misspelled_word != original and misspelled_word not in misspelled:
                misspelled.append(misspelled_word)
    
    return misspelled[:num_versions]

@bot.message_handler(func=lambda message: message.text == "🔤 Вибір правильного написання" or message.text == get_text("choose_correct_spelling", message.chat.id))
def spelling_choice_game(message):
    """Game where user selects the correct spelling from 4 options"""
    chat_id = message.chat.id
    
    # Очищаємо попередній стан, зберігаючи тип словника
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Встановлюємо рівень як "medium"
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    user_state[chat_id] = {
        "dict_type": dict_type,
        "level": "medium",
        "game": "spelling_choice",
        "attempts": 0
    }
    
    if shared_dict_id:
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    try:
        # Отримуємо слова для гри
        df = None
        if dict_type == "shared":
            if shared_dict_id:
                df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
            else:
                bot.send_message(chat_id, "❌ Не вказано спільний словник", reply_markup=medium_level_keyboard())
                return
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        # Перевіряємо наявність слів
        if df is None or df.empty:
            dict_name = get_text("shared_dictionary", chat_id) if dict_type == "shared" else get_text("common_dictionary", chat_id, "загальному словнику") if dict_type == "common" else get_text("personal_dictionary", chat_id)
            bot.send_message(chat_id, f"{get_text('in', chat_id)} {dict_name} {get_text('no_words', chat_id)}", reply_markup=medium_level_keyboard(chat_id))
            return
            
        # Вибираємо випадкове слово
        word_row = df.sample(1).iloc[0]
        
        # Створюємо неправильні варіанти написання
        misspelled_versions = create_misspelled_versions(word_row['word'])
        
        # Всі варіанти для вибору
        all_options = [word_row['word']] + misspelled_versions
        random.shuffle(all_options)
        
        # Зберігаємо стан
        user_state[chat_id].update({
            "word_id": word_row['id'],
            "word": word_row['word'],
            "translation": word_row['translation'],
            "options": all_options
        })
        
        # Створюємо інлайн-клавіатуру з варіантами
        markup = telebot.types.InlineKeyboardMarkup(row_width=2)
        buttons = [
            telebot.types.InlineKeyboardButton(option, callback_data=f"spell_{i}")
            for i, option in enumerate(all_options)
        ]
        markup.add(*buttons)
        
        # Відправляємо завдання
        bot.send_message(
            chat_id,
            f"🔤 Виберіть правильний варіант написання слова:\n\n"
            f"<b>Переклад: {word_row['translation']}</b>",
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error in spelling_choice_game: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Сталася помилка при запуску гри.", reply_markup=medium_level_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("spell_"))
def handle_spelling_choice(call):
    """Handle user's selection in the spelling choice game"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_state or user_state[chat_id].get("game") != "spelling_choice":
        bot.answer_callback_query(call.id, "❌ Помилка: гра не активна")
        return
    
    # Отримуємо індекс обраного варіанта
    selected_index = int(call.data.split("_")[1])
    selected_option = user_state[chat_id]["options"][selected_index]
    
    # Отримуємо правильну відповідь
    correct_option = user_state[chat_id]["word"]
    
    # Перевіряємо відповідь
    is_correct = selected_option == correct_option
    
    # Оновлюємо рейтинг слова
    word_id = user_state[chat_id]["word_id"]
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    try:
        # Змінюємо рейтинг в залежності від правильності відповіді
        rating_change = MEDIUM_RATING_DECREASE if is_correct else MEDIUM_RATING_INCREASE
        
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
            print(f"Updated shared dict rating for word {word_id}: {rating_change}")
        else:
            db_manager.update_word_rating(chat_id, word_id, rating_change)
            print(f"Updated personal dict rating for word {word_id}: {rating_change}")
                
        if is_correct:
            bot.answer_callback_query(call.id, "✅ Правильно!")
            
            # Оновлюємо повідомлення
            bot.edit_message_text(
                f"✅ Правильно!\n\n"
                f"<b>{correct_option}</b> = <b>{user_state[chat_id]['translation']}</b>",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
        else:
            bot.answer_callback_query(call.id, "❌ Неправильно!")
            
            # Оновлюємо повідомлення
            bot.edit_message_text(
                f"❌ Неправильно!\n\n"
                f"Ви обрали: <b>{selected_option}</b>\n"
                f"Правильно: <b>{correct_option}</b> = <b>{user_state[chat_id]['translation']}</b>",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"Error updating rating: {e}")
        import traceback
        traceback.print_exc()
    
    # Запускаємо нову гру після паузи
    import threading
    threading.Timer(2.0, lambda: spelling_choice_game_new_word(chat_id)).start()

def spelling_choice_game_new_word(chat_id):
    """Start a new round of the spelling choice game"""
    try:
        # Запускаємо нову гру з тими самими налаштуваннями
        if chat_id in user_state and user_state[chat_id].get("game") == "spelling_choice":
            bot.send_message(chat_id, "Наступне слово...")
            
            # Створюємо фіктивне повідомлення для передачі в функцію
            class FakeMessage:
                def __init__(self, chat_id):
                    self.chat = telebot.types.Chat(chat_id, "private")
                    self.from_user = telebot.types.User(chat_id, False, "user")
                    self.text = "🔤 Вибір правильного написання"
            
            spelling_choice_game(FakeMessage(chat_id))
    except Exception as e:
        print(f"Error starting new spelling game: {e}")

@bot.message_handler(func=lambda message: message.text == "📝 Заповніть пропуски" or message.text == get_text("fill_in_gaps", message.chat.id))
def missing_letters_game(message):
    """Game where user needs to fill in missing letters"""
    chat_id = message.chat.id
    
    # Очищаємо попередній стан, зберігаючи тип словника
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Встановлюємо рівень як "medium"
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    user_state[chat_id] = {
        "dict_type": dict_type,
        "level": "medium",
        "game": "missing_letters",
        "attempts": 0
    }
    
    if shared_dict_id:
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    generate_missing_letters_exercise(chat_id)

def generate_missing_letters_exercise(chat_id):
    """Generate a new exercise with missing letters"""
    try:
        # Отримуємо слова для гри
        dict_type = user_state[chat_id].get("dict_type", "personal")
        shared_dict_id = user_state[chat_id].get("shared_dict_id")
        
        df = None
        if dict_type == "shared":
            if shared_dict_id:
                df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
            else:
                bot.send_message(chat_id, "❌ Не вказано спільний словник", reply_markup=medium_level_keyboard())
                return
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        # Перевіряємо наявність слів
        if df is None or df.empty:
            # Use localization instead of hard-coded Ukrainian
            # get_text('in') = "📭 В " or localized prefix
            # get_text('no_words') = " ще немає доданих слів." or localized suffix
            # get_text('{dict_type}_dictionary') gives the dictionary name
            dict_name = get_text(f"{dict_type}_dictionary", chat_id)
            message = f"{get_text('in', chat_id)} {dict_name} {get_text('no_words', chat_id)}"
            bot.send_message(chat_id, message, reply_markup=medium_level_keyboard(chat_id))
            return
        
        # Вибираємо слово, яке має більше 3 букв
        filtered_df = df[df['word'].str.len() > 3]
        if filtered_df.empty:
            filtered_df = df  # Якщо нема довгих слів, беремо будь-які
            
        word_row = filtered_df.sample(1).iloc[0]
        word = word_row['word']
        
        # Визначаємо кількість букв, які треба пропустити (25-35% довжини слова)
        num_missing = max(1, min(3, int(len(word) * random.uniform(0.25, 0.35))))
        
        # Вибираємо позиції букв для пропуску (не першу і не останню)
        valid_positions = list(range(1, len(word) - 1))
        if len(valid_positions) < num_missing:
            valid_positions = list(range(len(word)))  # Для дуже коротких слів
            
        missing_positions = sorted(random.sample(valid_positions, num_missing))
        
        # Створюємо слово з пропущеними буквами
        word_with_blanks = list(word)
        missing_letters = ""
        for pos in missing_positions:
            missing_letters += word[pos]
            word_with_blanks[pos] = '_'
        
        word_with_blanks = ''.join(word_with_blanks)
        
        # Зберігаємо стан
        user_state[chat_id].update({
            "word_id": word_row['id'],
            "word": word,
            "translation": word_row['translation'],
            "word_with_blanks": word_with_blanks,
            "missing_letters": missing_letters,
            "missing_positions": missing_positions
        })
        
        # Відправляємо завдання
        bot.send_message(
            chat_id,
            f"📝 Введіть пропущені літери у слові:\n\n"
            f"<b>{word_with_blanks}</b>\n\n"
            f"Переклад: <b>{word_row['translation']}</b>\n\n"
            f"Введіть <b>{num_missing}</b> пропущених літер підряд, без пробілів:",
            parse_mode="HTML"
        )
        
        # Реєструємо обробник для наступного повідомлення
        bot.register_next_step_handler_by_chat_id(chat_id, handle_missing_letters_answer)
        
    except Exception as e:
        print(f"Error in missing_letters_game: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Сталася помилка при створенні завдання.", reply_markup=medium_level_keyboard())

def handle_missing_letters_answer(message):
    """Handle user's answer in the missing letters game"""
    chat_id = message.chat.id
    
    # Check for menu navigation commands first
    if is_menu_navigation_command(message):
        handle_exit_from_activity(message)
        return
    
    # Check if the game is still active
    if chat_id not in user_state or user_state[chat_id].get("game") != "missing_letters":
        bot.send_message(chat_id, get_text("game_not_active", chat_id), reply_markup=medium_level_keyboard(chat_id))
        return
    
    # Get user's answer - sanitize it first
    user_answer = sanitize_user_input(message.text.strip())
    correct_letters = user_state[chat_id]["missing_letters"]
    
    # Перевіряємо відповідь
    is_correct = user_answer.lower() == correct_letters.lower()
    
    word = user_state[chat_id]["word"]
    translation = user_state[chat_id]["translation"]
    word_with_blanks = user_state[chat_id]["word_with_blanks"]
    
    # Оновлюємо рейтинг слова
    word_id = user_state[chat_id]["word_id"]
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    try:
        if is_correct:
            # Зменшуємо рейтинг слова (воно стає легшим)
            rating_change = MEDIUM_RATING_DECREASE
            
            # Відправляємо повідомлення про успіх
            bot.send_message(
                chat_id,
                f"✅ Правильно!\n\n"
                f"<b>{word}</b> = <b>{translation}</b>",
                parse_mode="HTML"
            )
            
            # Запускаємо нову гру після паузи
            bot.send_message(chat_id, "Наступне слово...")
            generate_missing_letters_exercise(chat_id)
        else:
            # Збільшуємо рейтинг слова (воно стає важчим)
            rating_change = MEDIUM_RATING_INCREASE
            
            # Збільшуємо кількість спроб
            user_state[chat_id]["attempts"] = user_state[chat_id].get("attempts", 0) + 1
            attempts = user_state[chat_id]["attempts"]
            
            if attempts >= 2:
                # Після двох спроб показуємо правильну відповідь
                bot.send_message(
                    chat_id,
                    f"❌ Неправильно!\n\n"
                    f"Правильна відповідь: <b>{correct_letters}</b>\n"
                    f"Повне слово: <b>{word}</b> = <b>{translation}</b>",
                    parse_mode="HTML"
                )
                
                # Запускаємо нову гру після паузи
                bot.send_message(chat_id, "Наступне слово...")
                generate_missing_letters_exercise(chat_id)
            else:
                # Даємо ще одну спробу
                bot.send_message(
                    chat_id,
                    f"❌ Неправильно! Спробуйте ще раз.\n\n"
                    f"<b>{word_with_blanks}</b>\n\n"
                    f"Переклад: <b>{translation}</b>",
                    parse_mode="HTML"
                )
                
                # Реєструємо обробник для наступної спроби
                bot.register_next_step_handler_by_chat_id(chat_id, handle_missing_letters_answer)
        
        # Оновлюємо рейтинг слова
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
            print(f"Updated shared dict rating for word {word_id}: {rating_change}")
        else:
            db_manager.update_word_rating(chat_id, word_id, rating_change)
            print(f"Updated personal dict rating for word {word_id}: {rating_change}")
            
    except Exception as e:
        print(f"Error in handle_missing_letters_answer: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Сталася помилка при обробці відповіді.", reply_markup=medium_level_keyboard())
