# -*- coding: utf-8 -*-

"""
Обробники для активностей складного рівня.
"""

import traceback
import db_manager
from config import bot, user_state
from utils import clear_state, main_menu_keyboard, hard_level_keyboard
from utils.input_handlers import safe_next_step_handler, sanitize_user_input, is_menu_navigation_command, handle_exit_from_activity
from dictionary import return_to_appropriate_menu
from utils.language_utils import get_text
from utils.console_logger import log_menu_transition, log_displayed_buttons, MENU_MAIN, MENU_EASY, MENU_MEDIUM, MENU_HARD, MENU_SHARED
# Add import for grammar helpers
from utils.grammar_helpers import get_case_explanation, get_pronoun_translation, get_case_name_in_ukrainian

# Додаємо константи для зміни рейтингу на високому рівні
HARD_RATING_DECREASE = -0.1    # Зменшення рейтингу при правильній відповіді
HARD_RATING_INCREASE = 0.2     # Збільшення рейтингу при неправильній відповіді

@bot.message_handler(func=lambda message: message.text == "🧩 Складна гра" or message.text == get_text("advanced_game", message.chat.id))
def hard_game(message):
    """Placeholder for a complex game (to be developed)"""
    chat_id = message.chat.id
    
    # Store current state and menu
    prev_menu = user_state.get(chat_id, {}).get("current_menu", "UNKNOWN")
    log_menu_transition(chat_id, prev_menu, MENU_HARD, f"Button: {message.text}")
    
    # Preserve the dictionary type and level, reset other state
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Ensure the level is set to hard
    if chat_id in user_state:
        user_state[chat_id].update({
            "level": "hard",
            "current_menu": MENU_HARD
        })
    else:
        user_state[chat_id] = {
            "level": "hard", 
            "current_menu": MENU_HARD,
            "dict_type": "personal"  # Default if not already set
        }
    
    # Get user language - this ensures consistent language
    language = db_manager.get_user_language(chat_id) or "uk"
    user_state[chat_id]["language"] = language
    
    # Повідомляємо, що функціонал у розробці
    bot.send_message(
        chat_id, 
        get_text("hard_game_developing", chat_id),
        reply_markup=hard_level_keyboard(chat_id)
    )

@bot.message_handler(func=lambda message: message.text == "📝 Введення слів" or message.text == get_text("word_typing", message.chat.id))
def word_typing_game(message):
    """Game where user needs to type German translation of a Ukrainian word"""
    chat_id = message.chat.id
    
    # Видаляємо повідомлення активності, зберігаючи тип словника та рівень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Переконуємося, що рівень встановлено як "hard"
    if chat_id in user_state:
        user_state[chat_id].update({
            "level": "hard",
            "game": "word_typing",
            "attempts": 0,
            "current_menu": MENU_HARD
        })
    else:
        user_state[chat_id] = {
            "dict_type": "personal",
            "level": "hard",
            "game": "word_typing",
            "attempts": 0,
            "current_menu": MENU_HARD
        }
    
    # Отримуємо тип словника
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    try:
        # Отримуємо слова з відповідного словника
        df = None
        if dict_type == "shared" and shared_dict_id:
            df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        if df is None or df.empty:
            dict_name = get_text("shared_dictionary", chat_id) if dict_type == "shared" else get_text("personal_dictionary", chat_id)
            bot.send_message(chat_id, f"{get_text('in', chat_id)} {dict_name} {get_text('no_words', chat_id)}", reply_markup=hard_level_keyboard(chat_id))
            return
            
        # Вибираємо випадкове слово
        word = df.sample(1).iloc[0]
        
        # Зберігаємо інформацію про слово в стані користувача
        user_state[chat_id].update({
            "word_id": word['id'],
            "word": word['word'],
            "translation": word['translation']
        })
        
        # Відправляємо завдання ввести слово за перекладом
        bot.send_message(
            chat_id,
            get_text("enter_german_translation", chat_id).format(word=word['translation']),
            parse_mode="HTML"
        )
        
        # Реєструємо обробник для введення відповіді
        bot.register_next_step_handler_by_chat_id(chat_id, handle_word_typing_answer)
            
    except Exception as e:
        print(f"Error in word_typing_game: {e}")
        traceback.print_exc()
        bot.send_message(
            chat_id, 
            get_text("error_activity", chat_id), 
            reply_markup=hard_level_keyboard(chat_id)
        )

def handle_word_typing_answer(message):
    """Handle user's answer in word typing game"""
    chat_id = message.chat.id
    
    # Check for menu navigation commands first
    if is_menu_navigation_command(message):
        handle_exit_from_activity(message)
        return
    
    # Check if the game is still active
    if chat_id not in user_state or user_state[chat_id].get("game") != "word_typing":
        bot.send_message(chat_id, get_text("game_not_active", chat_id), reply_markup=hard_level_keyboard(chat_id))
        return
    
    # Get user's answer - sanitize it first
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
                get_text("correct_translation", chat_id).format(word=correct_word, translation=translation),
                parse_mode="HTML"
            )
            
            # Зменшуємо рейтинг для правильної відповіді
            rating_change = HARD_RATING_DECREASE
        else:
            # Збільшуємо кількість спроб
            user_state[chat_id]["attempts"] = user_state[chat_id].get("attempts", 0) + 1
            attempts = user_state[chat_id]["attempts"]
            
            if attempts >= 2:
                # Після двох невдалих спроб показуємо правильну відповідь
                bot.send_message(
                    chat_id,
                    get_text("incorrect_translation_final", chat_id).format(word=correct_word, translation=translation),
                    parse_mode="HTML"
                )
            else:
                # Даємо ще одну спробу
                bot.send_message(
                    chat_id,
                    get_text("incorrect_try_again", chat_id).format(translation=translation),
                    parse_mode="HTML"
                )
                
                # Реєструємо обробник для наступної спроби
                bot.register_next_step_handler_by_chat_id(chat_id, handle_word_typing_answer)
                return
            
            # Збільшуємо рейтинг для неправильної відповіді
            rating_change = HARD_RATING_INCREASE
        
        # Застосовуємо зміну рейтингу відповідно до типу словника
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, rating_change)
        
        # Продовжуємо з новим словом
        bot.send_message(chat_id, get_text("continue_game", chat_id))
        word_typing_game(message)
    except Exception as e:
        print(f"Error processing answer: {e}")
        traceback.print_exc()

@bot.message_handler(func=lambda message: message.text == "🏷️ Введення артиклів" or message.text == get_text("article_typing", message.chat.id))
def article_typing_game(message):
    """Game where user needs to type correct article for a German word"""
    chat_id = message.chat.id
    
    # Видаляємо повідомлення активності, зберігаючи тип словника та рівень
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False, preserve_level=True)
    
    # Переконуємося, що рівень встановлено як "hard"
    if chat_id in user_state:
        user_state[chat_id].update({
            "level": "hard",
            "game": "article_typing",
            "attempts": 0,
            "current_menu": MENU_HARD
        })
    else:
        user_state[chat_id] = {
            "dict_type": "personal",
            "level": "hard",
            "game": "article_typing",
            "attempts": 0,
            "current_menu": MENU_HARD
        }
    
    # Отримуємо тип словника
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    try:
        # Отримуємо слова з артиклями
        df = None
        if dict_type == "shared" and shared_dict_id:
            df = db_manager.get_shared_dictionary_words_with_articles(chat_id, shared_dict_id)
        else:
            df = db_manager.get_user_words_with_articles(chat_id, dict_type)
        
        if df is None or df.empty:
            dict_name = get_text("shared_dictionary", chat_id) if dict_type == "shared" else get_text("personal_dictionary", chat_id)
            bot.send_message(chat_id, f"{get_text('no_words_with_articles', chat_id)}", reply_markup=hard_level_keyboard(chat_id))
            return
            
        # Вибираємо випадкове слово з артиклем
        word = df.sample(1).iloc[0]
        
        # Зберігаємо інформацію про слово в стані користувача
        user_state[chat_id].update({
            "word_id": word['id'],
            "word": word['word'],
            "correct_article": word['article'],
            "translation": word['translation']
        })
        
        # Відправляємо завдання ввести артикль
        bot.send_message(
            chat_id,
            get_text("enter_article", chat_id).format(
                word=word['word'],
                translation=word['translation'],
                case_explanation=""
            ),
            parse_mode="HTML"
        )
        
        # Реєструємо обробник для введення відповіді
        bot.register_next_step_handler_by_chat_id(chat_id, handle_article_typing_answer)
            
    except Exception as e:
        print(f"Error in article_typing_game: {e}")
        traceback.print_exc()
        bot.send_message(
            chat_id, 
            get_text("error_activity", chat_id), 
            reply_markup=hard_level_keyboard(chat_id)
        )

def handle_article_typing_answer(message):
    """Handle user's answer in article typing game"""
    chat_id = message.chat.id
    
    # Check for menu navigation commands first
    if is_menu_navigation_command(message):
        handle_exit_from_activity(message)
        return
    
    # Check if the game is still active
    if chat_id not in user_state or user_state[chat_id].get("game") != "article_typing":
        bot.send_message(chat_id, get_text("game_not_active", chat_id), reply_markup=hard_level_keyboard(chat_id))
        return
    
    # Get user's answer - sanitize and lowercase to handle "der", "Die", etc.
    user_answer = sanitize_user_input(message.text.strip().lower())
    
    # Отримуємо дані зі стану користувача
    correct_article = user_state[chat_id]["correct_article"]
    word = user_state[chat_id]["word"]
    word_id = user_state[chat_id]["word_id"]
    dict_type = user_state[chat_id]["dict_type"]
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
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
            db_manager.update_word_rating_shared_dict(chat_id, word_id, HARD_RATING_DECREASE, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, HARD_RATING_DECREASE)
        
        # Продовжуємо з новим словом
        bot.send_message(chat_id, get_text("continue_game", chat_id))
        article_typing_game(message)
    else:
        # Збільшуємо кількість спроб
        user_state[chat_id]["attempts"] = user_state[chat_id].get("attempts", 0) + 1
        attempts = user_state[chat_id]["attempts"]
        
        # Оновлюємо рейтинг слова - для складного рівня менший штраф за помилку
        if dict_type == "shared" and shared_dict_id:
            db_manager.update_word_rating_shared_dict(chat_id, word_id, HARD_RATING_INCREASE, shared_dict_id)
        else:
            db_manager.update_word_rating(chat_id, word_id, HARD_RATING_INCREASE)
        
        # Якщо це вже друга спроба, показуємо правильну відповідь і продовжуємо
        if attempts >= 2:  # Змінено з 3 на 2 спроби
            bot.send_message(
                chat_id,
                get_text("incorrect_article_final", chat_id).format(word=word, article=correct_article),
                parse_mode="HTML"
            )
            # Продовжуємо з новим словом
            bot.send_message(chat_id, get_text("continue_game", chat_id))
            article_typing_game(message)
        else:
            # Даємо ще одну спробу
            sent_message = bot.send_message(
                chat_id, 
                get_text("incorrect_article_retry", chat_id).format(word=word),
                parse_mode="HTML"
            )
            bot.register_next_step_handler(sent_message, handle_article_typing_answer)
