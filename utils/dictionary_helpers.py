# -*- coding: utf-8 -*-

"""
Вспомогательные функции для работы со словарем.
"""

import re
from config import bot, user_state, ADMIN_ID
import db_manager
from utils.input_handlers import safe_next_step_handler, sanitize_user_input

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
