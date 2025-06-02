# -*- coding: utf-8 -*-

"""
Обробники для вивчення артиклів.
"""

import threading
from config import bot, user_state
import db_manager
from .core import start_article_activity

@bot.message_handler(func=lambda message: message.text == "🏷️ Вивчати артиклі")
def learn_articles(message):
    """Start learning articles activity"""
    chat_id = message.chat.id
    # Отримуємо поточний тип словника - за замовчуванням ЗАВЖДИ персональний
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    print(f"Debug: Initial state in learn_articles: dict_type={dict_type}, shared_dict_id={shared_dict_id}")
    
    # Якщо вибраний спільний словник але немає ID, перевіряємо в базі даних
    if dict_type == "shared" and not shared_dict_id:
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                shared_dict_id = result[0]
                print(f"Retrieved shared_dict_id={shared_dict_id} from database")
            else:
                # Якщо немає активного спільного словника, перемикаємо на персональний
                dict_type = "personal"
                print(f"No shared_dict_id found, switching to personal dictionary")
                bot.send_message(
                    chat_id, 
                    "⚠️ Немає вибраного спільного словника. Використовується персональний словник."
                )
        except Exception as e:
            print(f"Error retrieving shared_dict_id: {e}")
            dict_type = "personal"  # Перемикаємо на персональний в разі помилки
            
    # Налаштовуємо стан користувача
    state_data = {"dict_type": dict_type, "level": "easy"}
    if shared_dict_id and dict_type == "shared":
        state_data["shared_dict_id"] = shared_dict_id
    
    print(f"Debug: Setting user state to {state_data}")
    
    # Оновлюємо або створюємо стан користувача
    if chat_id in user_state:
        user_state[chat_id].update(state_data)
    else:
        user_state[chat_id] = state_data
    
    # Запускаємо активність вивчення артиклів
    start_article_activity(chat_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith(('art_der_', 'art_die_', 'art_das_')))
def handle_article_selection(call):
    """Handle article selection"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_state or "correct_article" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вивчати артиклі'")
        return
    
    # Отримуємо обраний артикль та ID слова
    selected_article = None
    if call.data.startswith('art_der_'):
        selected_article = 'der'
    elif call.data.startswith('art_die_'):
        selected_article = 'die'
    elif call.data.startswith('art_das_'):
        selected_article = 'das'
    
    correct_article = user_state[chat_id]["correct_article"]
    word = user_state[chat_id]["word"]
    word_id = user_state[chat_id]["word_id"]
    
    # Перевіряємо правильність вибору
    is_correct = selected_article == correct_article
    
    # Оновлюємо рейтинг слова в залежності від типу словника
    dict_type = user_state[chat_id].get("dict_type", "personal")
    if dict_type == "shared":
        shared_dict_id = user_state[chat_id].get("shared_dict_id")
        db_manager.update_word_rating_shared_dict(chat_id, word_id, -0.1 if is_correct else 0.1, shared_dict_id)
    elif dict_type == "personal":
        db_manager.update_word_rating(chat_id, word_id, -0.1 if is_correct else 0.1)
    
    # Показуємо користувачу результат
    if is_correct:
        bot.answer_callback_query(call.id, "✅ Правильно!")
        bot.edit_message_text(
            f"✅ Правильно! Слово <b>{word}</b> має артикль <b>{correct_article}</b>.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    else:
        bot.answer_callback_query(call.id, f"❌ Неправильно! Правильний артикль: {correct_article}")
        bot.edit_message_text(
            f"❌ Неправильно! Слово <b>{word}</b> має артикль <b>{correct_article}</b>, а не {selected_article}.",
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    
    # Переходимо до наступного слова через 2 секунди
    threading.Timer(2, lambda: start_article_activity(chat_id)).start()
