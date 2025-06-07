# -*- coding: utf-8 -*-

"""
Обробники для вивчення слів.
"""

from config import bot, user_state
from storage import get_dataframe, save_dataframe, get_user_file_path
from handlers.core import start_learning  # Import from core instead of duplicating code
import db_manager
from handlers.easy_level import learn_words  # Import learn_words at the top level

@bot.message_handler(func=lambda message: message.text == "📖 Вчити нові слова")
def learn_words_handler(message):
    """Handler for learning new words - redirect to easy_level.py"""
    learn_words(message)  # Use the imported function

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
        
        try:
            df = get_dataframe(chat_id)
            
            # Зробимо деякі перевірки для налагодження
            print(f"DEBUG: DataFrame columns for user {chat_id}: {df.columns.tolist()}")
            
            # Перевіряємо наявність потрібних колонок
            if 'translation' not in df.columns:
                print(f"WARNING: Missing 'translation' column for user {chat_id}")
                # Знаходимо колонку перекладу на основі мови користувача
                tran_column = None
                
                # Шукаємо можливі варіанти колонок перекладу
                if 'uk_tran' in df.columns:
                    tran_column = 'uk_tran'
                elif 'ru_tran' in df.columns:
                    tran_column = 'ru_tran'
                elif len(df.columns) >= 2:
                    # Якщо є хоча б дві колонки, використовуємо другу як переклад
                    tran_column = df.columns[1]
                
                if tran_column:
                    print(f"Using column '{tran_column}' as translation")
                    # Додаємо колонку translation
                    df['translation'] = df[tran_column]
                else:
                    # Якщо не можемо знайти колонку перекладу, додаємо порожню
                    print(f"Adding empty 'translation' column")
                    df['translation'] = ''
                    
            if 'priority' not in df.columns:
                print(f"WARNING: Missing 'priority' column for user {chat_id}")
                # Додаємо колонку пріоритету зі значенням за замовчуванням 0.0
                df['priority'] = 0.0
            
            # Продовжуємо виконання з оновленим DataFrame
            if correct:
                bot.answer_callback_query(call.id, "✅ Правильно!")
                # Безпечне оновлення рейтингу з перевіркою наявності значення у state
                if 'selected_tr' in state and state['selected_tr'] and 'translation' in df.columns:
                    try:
                        # Знаходимо рядки, де переклад збігається з обраним
                        mask = df['translation'] == state['selected_tr']
                        if mask.any():
                            # Оновлюємо рейтинг тільки для знайдених рядків
                            df.loc[mask, 'priority'] = df.loc[mask, 'priority'] - 0.1
                    except Exception as e:
                        print(f"Error updating priority: {e}")
                
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
                    learn_words(call.message)  # Now this will work correctly
            else:
                bot.answer_callback_query(call.id, "❌ Неправильно!")
                # Безпечне оновлення рейтингу з перевіркою наявності значення
                if 'selected_tr' in state and state['selected_tr'] and 'translation' in df.columns:
                    try:
                        # Знаходимо рядки, де переклад збігається з обраним
                        mask = df['translation'] == state['selected_tr']
                        if mask.any():
                            # Оновлюємо рейтинг тільки для знайдених рядків
                            df.loc[mask, 'priority'] = df.loc[mask, 'priority'] + 0.1
                    except Exception as e:
                        print(f"Error updating priority: {e}")
            
            # Збережемо оновлений DataFrame
            file_path, lang = get_user_file_path(chat_id) if state["dict_type"] == "personal" else (None, None)
            save_dataframe(chat_id, df, lang if lang else "common")
            state['selected_tr'] = None
            
            dict_type = state.get("dict_type")
            shared_dict_id = state.get("shared_dict_id")
            
            # Для спільних словників також оновлюємо рейтинг
            if dict_type == "shared" and shared_dict_id:
                try:
                    # Знаходимо ID слова за перекладом
                    for row in df.itertuples():
                        if getattr(row, 'translation') == state['selected_tr']:
                            word_id = getattr(row, 'id')
                            
                            # Оновлюємо рейтинг залежно від правильності відповіді
                            if correct:
                                db_manager.update_word_rating_shared_dict(chat_id, word_id, -0.1, shared_dict_id)
                            else:
                                db_manager.update_word_rating_shared_dict(chat_id, word_id, 0.1, shared_dict_id)
                            break
                except Exception as e:
                    print(f"Error updating shared dict rating: {e}")
        except Exception as e:
            print(f"Error in handle_pairs: {e}")
            import traceback
            traceback.print_exc()
            state['selected_tr'] = None
