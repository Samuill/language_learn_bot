# -*- coding: utf-8 -*-

"""
Обробники для вивчення слів.
"""

from config import bot, user_state
from storage import get_dataframe, save_dataframe, get_user_file_path
from dictionary import start_activity

@bot.message_handler(func=lambda message: message.text == "📖 Вчити нові слова")
def learn_words(message):
    start_activity(message.chat.id, 'learn')

@bot.callback_query_handler(func=lambda call: call.data.startswith(('tr_', 'de_')))
def handle_pairs(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or "pairs" not in user_state[chat_id]:
        bot.answer_callback_query(call.id, "❗ Спочатку оберіть розділ 'Вчити нові слова'")
        return
    
    state = user_state[chat_id]
    
    if call.data.startswith('tr_'):
        if state.get('selected_tr'):
            bot.answer_callback_query(call.id, "⏳ Спочатку завершіть поточний вибір")
            return
        state['selected_tr'] = call.data[3:]
        bot.answer_callback_query(call.id, f"Обрано: {state['selected_tr']}")
    
    elif call.data.startswith('de_'):
        if not state.get('selected_tr'):
            bot.answer_callback_query(call.id, "❗ Спочатку оберіть переклад")
            return
        
        selected_de = call.data[3:]
        correct = any(tr == state['selected_tr'] and de == selected_de for tr, de in state["pairs"])
        
        df = get_dataframe(chat_id)
        if correct:
            bot.answer_callback_query(call.id, "✅ Правильно!")
            df.loc[df['translation'] == state['selected_tr'], 'priority'] -= 0.001
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
            bot.answer_callback_query(call.id, "❌ Неправильно!")
            df.loc[df['translation'] == state['selected_tr'], 'priority'] += 0.001
        
        file_path, lang = get_user_file_path(chat_id) if state["dict_type"] == "personal" else (None, None)
        save_dataframe(chat_id, df, lang if lang else "common")
        state['selected_tr'] = None
