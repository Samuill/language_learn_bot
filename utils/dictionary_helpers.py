# -*- coding: utf-8 -*-

"""
Вспомогательные функции для работы со словарем.
"""

import re
from config import bot, user_state, ADMIN_ID
import db_manager
from utils.input_handlers import safe_next_step_handler, sanitize_user_input
from utils.language_utils import get_text

def add_word_to_dictionary(chat_id, word, translation, dict_type="personal", article=None):
    """
    Единая функция для добавления слова в словарь с валидацией.
    
    Args:
        chat_id: ID чата пользователя
        word: Немецкое слово для добавления
        translation: Перевод слова
        dict_type: Тип словаря (personal, common, shared)
        article: Артикль (опционально)
    
    Returns:
        tuple: (success, message)
    """
    # Валидация параметров
    if not word or not translation:
        return False, "Слово або переклад не можуть бути порожніми."
    
    # Очистка ввода от потенциально опасных символов
    word = sanitize_user_input(word, max_length=50)
    translation = sanitize_user_input(translation, max_length=100)
    
    # Проверка прав на добавление в общий словарь
    if dict_type == "common" and chat_id != ADMIN_ID:
        return False, "Тільки адміністратор може додавати слова до загального словника."
    
    # Проверка возможных артиклей в слове
    article_match = re.match(r'^(der|die|das)\s+(.+)$', word, re.IGNORECASE)
    if article_match:
        # Если нашли артикль в слове
        extracted_article = article_match.group(1).lower()
        word = article_match.group(2).strip()
        
        # Приоритет артикля из слова, если не указан явно
        if not article:
            article = extracted_article
    
    # Добавляем слово
    result = db_manager.add_word(chat_id, word, translation, dict_type, article)
    
    if result:
        return True, f"✅ Слово '{word}' успішно додано до словника."
    else:
        return False, "❌ Помилка при додаванні слова. Спробуйте ще раз."

def process_add_word_command(message):
    """
    Обрабатывает команду добавления слова.
    
    Args:
        message: Сообщение с командой добавления слова
    """
    chat_id = message.chat.id
    
    # Проверяем, установлен ли тип словаря
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    
    # Проверяем права на добавление в разные типы словарей
    can_add = True
    if dict_type == "common" and chat_id != ADMIN_ID:
        can_add = False
        bot.send_message(chat_id, "❌ Тільки адміністратор може додавати слова до загального словника.")
    elif dict_type == "shared":
        # Проверяем, является ли пользователь администратором общего словаря
        is_admin = db_manager.is_shared_dict_admin(chat_id, shared_dict_id)
        if not is_admin:
            can_add = False
            bot.send_message(chat_id, "❌ Тільки адміністратор може додавати слова до спільного словника.")
    
    if can_add:
        # Запрашиваем немецкое слово
        sent_message = bot.send_message(chat_id, "Введіть німецьке слово (можна з артиклем der/die/das):")
        safe_next_step_handler(sent_message, process_word_input)

def process_word_input(message):
    """Обрабатывает ввод немецкого слова"""
    chat_id = message.chat.id
    german_word = sanitize_user_input(message.text, max_length=50)
    
    # Сохраняем слово в состоянии
    if chat_id not in user_state:
        user_state[chat_id] = {}
    user_state[chat_id]["add_word_german"] = german_word
    
    # Запрашиваем перевод
    sent_message = bot.send_message(chat_id, f"Введіть переклад для слова '{german_word}':")
    safe_next_step_handler(sent_message, process_translation_input)

def process_translation_input(message):
    """Обрабатывает ввод перевода"""
    chat_id = message.chat.id
    
    # Проверяем наличие данных в состоянии
    if chat_id not in user_state or "add_word_german" not in user_state[chat_id]:
        bot.send_message(chat_id, "❌ Помилка: дані про слово втрачені. Спробуйте знову.")
        return
    
    translation = sanitize_user_input(message.text, max_length=100)
    german_word = user_state[chat_id]["add_word_german"]
    
    # Получаем параметры из состояния
    dict_type = user_state[chat_id].get("dict_type", "personal")
    shared_dict_id = user_state[chat_id].get("shared_dict_id")
    
    # Добавляем слово
    success, message = add_word_to_dictionary(chat_id, german_word, translation, dict_type)
    
    # Если успешно добавлено и это общий словарь, добавляем в общий словарь
    if success and dict_type == "shared" and shared_dict_id:
        # Получаем ID добавленного слова
        word_id = db_manager.get_word_id_by_german(german_word)
        if word_id:
            db_manager.add_word_to_shared_dictionary(chat_id, word_id, shared_dict_id)
    
    # Выводим сообщение о результате
    bot.send_message(chat_id, message)
    
    # Очищаем состояние
    if "add_word_german" in user_state[chat_id]:
        del user_state[chat_id]["add_word_german"]

def load_user_dictionary(chat_id):
    """
    Load the appropriate dictionary for a user with validation
    
    Args:
        chat_id (int): User's chat ID
        
    Returns:
        tuple: (dataframe, dict_type, dict_name, shared_dict_id, success)
    """
    import db_manager
    from utils.state_management import ensure_dict_state
    
    # Get dictionary type from state/database (with validation)
    dict_type, shared_dict_id = ensure_dict_state(chat_id)
    
    # Get dictionary name
    dict_name = get_text(f"{dict_type}_dictionary", chat_id)
    
    # Load the appropriate dictionary
    try:
        if dict_type == "shared" and shared_dict_id:
            # Ensure dictionary exists before attempting to load
            if not db_manager.shared_dictionary_exists(shared_dict_id):
                print(f"Shared dictionary {shared_dict_id} doesn't exist for user {chat_id}, falling back to personal")
                dict_type = "personal"
                shared_dict_id = None
                db_manager.reset_user_dictionary(chat_id)
                df = db_manager.get_user_words(chat_id, "personal")
                dict_name = get_text("personal_dictionary", chat_id)
            else:
                # Load shared dictionary
                df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
                
                # Get actual dictionary name from database
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
                result = cursor.fetchone()
                if result:
                    dict_name = result[0]
                conn.close()
        else:
            # Load personal dictionary
            df = db_manager.get_user_words(chat_id, dict_type)
        
        return df, dict_type, dict_name, shared_dict_id, True
    
    except Exception as e:
        print(f"Error loading dictionary: {e}")
        import traceback
        traceback.print_exc()
        return None, dict_type, dict_name, shared_dict_id, False

def handle_empty_dictionary(chat_id, level_keyboard=None, dict_name=None):
    """
    Show an appropriate "no words" message for empty dictionary and keep user in the current menu.
    """
    from utils import easy_level_keyboard, medium_level_keyboard, hard_level_keyboard
    from config import user_state
    
    # Get the appropriate keyboard based on level if not provided
    if level_keyboard is None:
        level = user_state.get(chat_id, {}).get("level", "easy")
        if level == "hard":
            level_keyboard = hard_level_keyboard(chat_id)
        elif level == "medium":
            level_keyboard = medium_level_keyboard(chat_id)
        else:
            level_keyboard = easy_level_keyboard(chat_id)
    
    # Get dict_name if not provided
    if dict_name is None:
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        
        if dict_type == "shared" and shared_dict_id:
            # Get shared dictionary name
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
            result = cursor.fetchone()
            dict_name = f"«{result[0]}»" if result else get_text("shared_dictionary", chat_id)
            conn.close()
        else:
            dict_name = get_text(f"{dict_type}_dictionary", chat_id)
    
    # Send the message with appropriate keyboard
    bot.send_message(
        chat_id,
        f"{get_text('in', chat_id)} {dict_name} {get_text('no_words', chat_id)}",
        reply_markup=level_keyboard
    )
    
    return False  # Indicate no words found

def update_word_rating(chat_id, word_id, is_correct, level="easy"):
    """
    Update word rating based on game performance with dictionary state preservation
    
    Args:
        chat_id (int): User's chat ID
        word_id (int): Word ID
        is_correct (bool): Whether user answered correctly
        level (str): Difficulty level
    """
    import db_manager
    from config import user_state
    
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    
    # Calculate rating change based on correctness and level
    if is_correct:
        if level == "easy":
            rating_change = -0.1
        elif level == "medium":
            rating_change = -0.1
        elif level == "hard":
            rating_change = -0.1
    else:
        if level == "easy":
            rating_change = 0.1
        elif level == "medium":
            rating_change = 0.1
        elif level == "hard":
            rating_change = 0.2
    
    # Update rating in the appropriate dictionary
    if dict_type == "shared" and shared_dict_id:
        # Validate shared dictionary exists before updating
        if db_manager.shared_dictionary_exists(shared_dict_id):
            db_manager.update_word_rating_shared_dict(chat_id, word_id, rating_change, shared_dict_id)
        else:
            print(f"Cannot update rating: shared dictionary {shared_dict_id} not found for user {chat_id}")
            # Reset to personal dictionary
            db_manager.reset_user_dictionary(chat_id)
            if chat_id in user_state:
                user_state[chat_id]["dict_type"] = "personal"
                if "shared_dict_id" in user_state[chat_id]:
                    del user_state[chat_id]["shared_dict_id"]
    else:
        db_manager.update_word_rating(chat_id, word_id, rating_change)
