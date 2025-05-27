# -*- coding: utf-8 -*-
import telebot
import pandas as pd
import random
import os
import time
import requests
from googletrans import Translator
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from telebot.types import Message

TOKEN = "7616425414:AAFaZCuYss9UyNSXm_MJCd42rLjAKNWy0Mc"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
scheduler = BackgroundScheduler()
user_state = {}


def start_activity(chat_id, mode):
    """Загальна функція для запуску активності"""
    clear_state(chat_id)
    track_activity(chat_id)
    
    df = get_dataframe(chat_id)
    if df is None or df.empty:
        bot.send_message(chat_id, "📭 У вас ще немає доданих слів.")
        return False
    
    if mode == 'repeat':
        return start_repetition(chat_id, df)
    elif mode == 'learn':
        return start_learning(chat_id, df)
    return False

def clear_state(chat_id):
    if chat_id in user_state:
        if "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except:
                pass
        del user_state[chat_id]

def get_user_params_path(chat_id):
    return f"params_{chat_id}.json"

def update_streak(chat_id):
    params_path = get_user_params_path(chat_id)
    
    try:
        with open(params_path, 'r') as f:
            params = json.load(f)
    except FileNotFoundError:
        params = {'streak': 0, 'last_active': None}
        
    today = datetime.now().date().isoformat()
    last_active = datetime.fromisoformat(params['last_active']).date() if params['last_active'] else None
    
    if last_active:
        delta = (datetime.now().date() - last_active).days
        if delta == 1:
            params['streak'] += 1
        elif delta > 1:
            params['streak'] = 1
    else:
        params['streak'] = 1
        
    params['last_active'] = today
    with open(params_path, 'w') as f:
        json.dump(params, f)
    return params['streak']

# Додаємо функціонал для відображення статистики
def send_streak_info(chat_id):
    params_path = get_user_params_path(chat_id)
    try:
        with open(params_path, 'r') as f:
            params = json.load(f)
        streak = params.get('streak', 0)
        last_active = params.get('last_active', 'ніколи')
        
        # Відправляємо інформацію про streak
        bot.send_message(
            chat_id,
            f"Не забудьте сьогодні потренуватись!"
        )
        
        # Відправляємо стікер
        try:
            with open(f'fires/{streak}.webp', 'rb') as sticker_file:
                bot.send_sticker(chat_id, sticker_file)
        except FileNotFoundError:
            print(f"Стікер для streak {streak} не знайдено")

        # Створюємо "фейковий" об'єкт повідомлення для виклику repeat_words
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat = FakeChat(chat_id)
        
        class FakeChat:
            def __init__(self, chat_id):
                self.id = chat_id
        
        fake_msg = FakeMessage(chat_id)
        
        try:
            repeat_words(fake_msg)  # Викликаємо з імітованим повідомленням
        except Exception as e:
            print(f"Помилка при відправці завдання: {e}")
        
    except FileNotFoundError:
        update_streak(chat_id)
        send_streak_info(chat_id)


def send_reminder():
    for filename in os.listdir():
        if filename.startswith("params_") and filename.endswith(".json"):
            chat_id = filename.split('_')[1].split('.')[0]
            try:
                send_streak_info(chat_id)  # Використовуємо нову функцію
            except Exception as e:
                print(f"Помилка для {chat_id}: {e}")

# Планувальник з випадковим часом
scheduler.add_job(send_reminder, 'cron', hour=random.randint(10,22), minute=random.randint(0,59))
scheduler.start()

# Додаємо оновлення streak при будь-якій активності
def track_activity(chat_id):
    params_path = get_user_params_path(chat_id)
    
    # Створюємо файл якщо не існує
    if not os.path.exists(params_path):
        update_streak(chat_id)
        
    return update_streak(chat_id)

def update_streak(chat_id):
    params_path = get_user_params_path(chat_id)
    
    try:
        with open(params_path, 'r') as f:
            params = json.load(f)
    except FileNotFoundError:
        params = {'streak': 0, 'last_active': None}
        
    today = datetime.now().date().isoformat()
    last_active = datetime.fromisoformat(params['last_active']).date() if params['last_active'] else None
    
    if last_active:
        delta = (datetime.now().date() - last_active).days
        if delta == 1:
            params['streak'] += 1
        elif delta > 1:
            params['streak'] = 1
    else:
        params['streak'] = 1
        
    params['last_active'] = today
    with open(params_path, 'w') as f:
        json.dump(params, f)
    return params['streak']


def get_user_file_path(chat_id):
    # Перевіряємо, чи існує файл для користувача
    ru_file = f"ru_words_{chat_id}.csv"
    uk_file = f"uk_words_{chat_id}.csv"
    
    if os.path.exists(ru_file):
        return ru_file, "ru"
    elif os.path.exists(uk_file):
        return uk_file, "uk"
    else:
        return None, None

def clear_state(chat_id):
    if chat_id in user_state:
        if "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except:
                pass
        del user_state[chat_id]

def get_dataframe(chat_id):
    file_path, _ = get_user_file_path(chat_id)
    if not file_path:
        return None
    return pd.read_csv(file_path, encoding='utf-8-sig')

def save_dataframe(chat_id, df, language):
    file_path = f"{language}_words_{chat_id}.csv"
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

def main_menu_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити")
    return keyboard

def main_menu_cancel():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Відміна")
    return keyboard

def language_selection_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🇺🇦 Українська", "🇷🇺 Російська")
    return keyboard

@bot.message_handler(commands=["start"])
def main_menu(message):
    clear_state(message.chat.id)
    file_path, language = get_user_file_path(message.chat.id)
    track_activity(message.chat.id)  # Додано цей рядок
    
    if not file_path:
        # Якщо файл не існує, пропонуємо вибрати мову
        bot.send_message(message.chat.id, "🌍 Виберіть мову, на якій бажаєте отримувати переклад слів:", reply_markup=language_selection_keyboard())
        user_state[message.chat.id] = {"step": "language_selection"}
    else:
        # Якщо файл існує, просто показуємо головне меню
        bot.send_message(message.chat.id, "Оберіть дію:", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: message.text in ["🇺🇦 Українська", "🇷🇺 Російська"])
def handle_language_selection(message):
    chat_id = message.chat.id
    if user_state.get(chat_id, {}).get("step") == "language_selection":
        language = "uk" if message.text == "🇺🇦 Українська" else "ru"
        
        # Створюємо порожній словник для користувача
        df = pd.DataFrame(columns=["word", "translation", "priority"])
        save_dataframe(chat_id, df, language)
        
        bot.send_message(chat_id, f"✅ Мову перекладу обрано: {message.text}. Тепер ви можете додавати слова та вивчати їх.", reply_markup=main_menu_keyboard())
        clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "➕ Додати нове слово")
def add_word(message):
    clear_state(message.chat.id)
    bot.send_message(message.chat.id, "Введіть слово, яке хочете додати:", reply_markup=main_menu_cancel())
    user_state[message.chat.id] = {"step": "adding_word"}

@bot.message_handler(func=lambda message: message.text == "Відміна")
def cancel_action(message):
    clear_state(message.chat.id)
    bot.send_message(message.chat.id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "adding_word")
def handle_translation(message):
    if not message.text or message.text.startswith('/'):
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть слово текстом!")
        return
        
    # Перевіряємо, чи не є введений текст командою
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть нове слово, а не команду.")
        return
        
    word = message.text.strip()
    file_path, language = get_user_file_path(message.chat.id)
    if not file_path:
        bot.send_message(message.chat.id, "❌ Мову перекладу не обрано. Спробуйте /start.")
        return
    
    translation = translator.translate(word, src="de", dest=language).text
    
    if translation:
        user_state[message.chat.id] = {
            "step": "confirm_translation",
            "word": word,
            "auto_translation": translation
        }
        keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("Так", "Ні","Відміна")
        bot.send_message(message.chat.id, f"Знайдено переклад: {translation}. Це правильно?", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Не вдалося перекласти слово. Спробуйте ще раз.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "confirm_translation")
def handle_confirmation(message):
    if message.text == "Так":
        save_word(message.chat.id)
        bot.send_message(message.chat.id, "✅ Слово успішно додано!", reply_markup=main_menu_keyboard())
    elif message.text == "Ні":
        # Видалено перевірку на команди (вона тут недоречна)
        bot.send_message(message.chat.id, "Введіть правильний переклад вручну:", reply_markup=telebot.types.ReplyKeyboardRemove())
        user_state[message.chat.id]["step"] = "manual_translation"
    elif message.text == "Відміна":
        clear_state(message.chat.id)
        bot.send_message(message.chat.id, "🚫 Дію скасовано.", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Будь ласка, виберіть 'Так', 'Ні' або 'Відміна'.")

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("step") == "manual_translation")
def handle_manual_translation(message):
    # Перевіряємо, чи не є введений текст командою
    if message.text in ["➕ Додати нове слово", "📖 Вчити нові слова", "🔄 Повторити", "🇺🇦 Українська", "🇷🇺 Російська"]:
        bot.send_message(message.chat.id, "❌ Будь ласка, введіть правильний переклад, а не команду.")
        return  # Додаємо return, щоб не продовжував зберігати команду
    
    save_word(message.chat.id, message.text.strip())
    bot.send_message(message.chat.id, "✅ Слово успішно додано з вашим перекладом!", reply_markup=main_menu_keyboard())

def save_word(chat_id, translation=None):
    file_path, language = get_user_file_path(chat_id)
    if not file_path:
        bot.send_message(chat_id, "❌ Мову перекладу не обрано. Спробуйте /start.")
        return
    
    df = get_dataframe(chat_id)
    if df is None:  # Додано перевірку на None
        df = pd.DataFrame(columns=["word", "translation", "priority"])
    data = user_state[chat_id]
    translation = translation or data["auto_translation"]
    
    new_row = pd.DataFrame({
        "word": [data["word"]],
        "translation": [translation],
        "priority": [0.0]
    })
    
    if not new_row.empty:
        df = pd.concat([df, new_row], ignore_index=True)
        save_dataframe(chat_id, df, language)
    clear_state(chat_id)

@bot.message_handler(func=lambda message: message.text == "📖 Вчити нові слова")
def learn_words(message):
    clear_state(message.chat.id)
    streak = track_activity(message.chat.id)
    df = get_dataframe(message.chat.id)
    
    if df is None or df.empty:
        bot.send_message(message.chat.id, "📭 У вас ще немає доданих слів.")
        return
    
    df = df.sort_values(by="priority", ascending=False)
    words = df.sample(min(10, len(df)))
    
    translations = words['translation'].tolist()
    de_words = words['word'].tolist()
    random.shuffle(translations)
    random.shuffle(de_words)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for tr, de in zip(translations, de_words):
        markup.add(
            telebot.types.InlineKeyboardButton(tr, callback_data=f'tr_{tr}'),
            telebot.types.InlineKeyboardButton(de, callback_data=f'de_{de}')
        )
    
    user_state[message.chat.id] = {
        "pairs": list(zip(words['translation'], words['word'])),
        "selected_tr": None,
        "message_id": None
    }
    
    sent_message = bot.send_message(message.chat.id, "🔍 Оберіть пару слів:", reply_markup=markup)
    user_state[message.chat.id]["message_id"] = sent_message.message_id

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
        
        save_dataframe(chat_id, df, get_user_file_path(chat_id)[1])
        state['selected_tr'] = None

@bot.message_handler(func=lambda message: message.text == "🔄 Повторити")
def repeat_words(message):
    clear_state(message.chat.id)
    streak = track_activity(message.chat.id)
    df = get_dataframe(message.chat.id)
    
    if df is None or df.empty:
        bot.send_message(message.chat.id, "📭 У вас ще немає доданих слів.")
        return
    
    word = df.sample(1).iloc[0]
    sample_size = min(3, len(df))
    translations = df['translation'].sample(sample_size).tolist()
    if word['translation'] not in translations:
        translations[0] = word['translation']
    random.shuffle(translations)
    
    markup = telebot.types.InlineKeyboardMarkup()
    for tr in translations:
        markup.add(telebot.types.InlineKeyboardButton(
            tr, 
            callback_data=f"ans_{word['word']}_{tr}"
        ))
    
    sent_message = bot.send_message(message.chat.id, f"📖 Оберіть переклад для слова: {word['word']}", reply_markup=markup)
    user_state[message.chat.id] = {
        "current_word": word,
        "message_id": sent_message.message_id
    }

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
    
    save_dataframe(chat_id, df, get_user_file_path(chat_id)[1])


# @bot.message_handler(commands=['fire'])
# def test_fire(message):
#     if message.from_user.id == YOUR_ADMIN_ID:  # Додайте свій ID
#         send_reminder()
#         bot.reply_to(message, "Нагадування відправлено!")

# @bot.message_handler(commands=['stop'])
# def stop_bot(message):
#     if message.from_user.id == YOUR_ADMIN_ID:
#         bot.stop_polling()
#         scheduler.shutdown()
#         os._exit(0)




@bot.message_handler(commands=['fire'])
def test_fire(message):
    if message.from_user.id == 476376623:
        try:
            send_reminder()
            bot.reply_to(message, "Нагадування відправлено!")
        except Exception as e:
            print(f"Помилка в /fire: {e}")
            bot.reply_to(message, f"Помилка: {str(e)}")
@bot.message_handler(commands=['stop'])
def stop_bot(message):
    if message.from_user.id == 476376623:
        bot.stop_polling()
        scheduler.shutdown(wait=False)  # Зупиняємо планувальник
        print("Бот зупинено!")
        exit(0)

if __name__ == '__main__':
    if not scheduler.running:  # Перевіряємо, чи він ще не запущений
        scheduler.start()
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1)
        except requests.exceptions.ConnectionError:
            print("Помилка з'єднання. Повторна спроба через 5 секунд...")
            time.sleep(5)
        except Exception as e:
            print(f"Критична помилка: {e}")
            time.sleep(5)