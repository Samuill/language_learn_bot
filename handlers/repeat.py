# -*- coding: utf-8 -*-

"""
Обробники для повторення слів.
"""

from config import bot, user_state
from storage import get_dataframe, save_dataframe, get_user_file_path
from dictionary import start_activity

@bot.message_handler(func=lambda message: message.text == "🔄 Повторити")
def repeat_words(message):
    chat_id = message.chat.id
    
    # Зберігаємо поточний рівень
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    # Запускаємо активність з обмеженням на показ слів з максимальним рейтингом для не-складного рівня
    start_activity(message.chat.id, 'repeat', exclude_max_rating=(level != "hard"))

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_answer(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Повторити'")
        return
    
    _, word, selected_tr = call.data.split('_')
    correct_tr = user_state[chat_id]["current_word"]['translation']
    
    df = get_dataframe(chat_id)
    if selected_tr == correct_tr:
        bot.answer_callback_query(call.id, "✅ Правильно!")
        df.loc[df['word'] == word, 'priority'] -= 0.001
        bot.delete_message(chat_id, call.message.message_id)
        repeat_words(call.message)
    else:
        bot.answer_callback_query(call.id, f"❌ Неправильно! Правильно: {correct_tr}")
        df.loc[df['word'] == word, 'priority'] += 0.001
        markup = call.message.reply_markup
        for row in markup.keyboard:
            if row[0].callback_data == call.data:
                row[0].text += " ❌"
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
    
    file_path, lang = get_user_file_path(chat_id) if user_state[chat_id].get("dict_type") == "personal" else (None, None)
    save_dataframe(chat_id, df, lang if lang else "common")
