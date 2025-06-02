# -*- coding: utf-8 -*-
from config import user_state, bot, ADMIN_ID
from utils import clear_state, main_menu_keyboard
import db_manager
from german_article_finder import find_german_article  # Додаємо імпорт новою функції

def save_word(chat_id, translation=None):
    """Save word to dictionary"""
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    print(f"Debug: save_word for user {chat_id}, dict_type={dict_type}")
    
    # Check permissions for common dictionary
    if dict_type == "common" and chat_id != ADMIN_ID:
        bot.send_message(
            chat_id, 
            "❌ Додати слово неможливо, змініть свій словник на персональний.", 
            reply_markup=main_menu_keyboard(chat_id)
        )
        clear_state(chat_id)
        return
    
    data = user_state.get(chat_id, {})
    if not data or "word" not in data:
        bot.send_message(chat_id, "❌ Помилка: дані слова не знайдено.")
        clear_state(chat_id)
        return
    
    word = data["word"]
    translation = translation or data["auto_translation"]
    
    # Пошук артикля у базі німецьких слів
    article, clean_word = find_german_article(word)
    print(f"Debug: Article finder returned article='{article}', clean_word='{clean_word}' for '{word}'")
    
    # Якщо артикль знайдено, використовуємо його і очищене слово
    if article:
        print(f"Found article '{article}' for word '{word}' -> '{clean_word}'")
        word_to_save = clean_word  # Зберігаємо слово без артикля
        article_to_save = article  # Окремо зберігаємо артикль
    else:
        # Визначаємо артикль зі слова (якщо є)
        import re
        article_match = re.match(r'^(der|die|das)\s+(.+)$', word, re.IGNORECASE)
        if article_match:
            article_to_save = article_match.group(1).lower()
            word_to_save = article_match.group(2).strip()
        else:
            # Якщо артикль не знайдено
            word_to_save = word
            article_to_save = None
    
    # Перевірка, чи слово вже існує в словнику користувача
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    exists_in_personal = False
    
    if dict_type == "personal":
        # Перевіряємо, чи слово вже є в словнику користувача
        try:
            cursor.execute(f"""
                SELECT 1 FROM words w
                JOIN user_{chat_id} u ON w.id = u.word_id
                WHERE LOWER(w.word) = LOWER(?)
            """, (word_to_save,))
            exists_in_personal = cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking if word exists: {e}")
    
    conn.close()
    
    # Зберігаємо слово в базу даних із можливим артиклем
    success = db_manager.add_word(chat_id, word_to_save, translation, dict_type, article_to_save)
    
    if success:
        # Формуємо повідомлення в залежності від наявності артикля та існування слова
        if exists_in_personal:
            if article_to_save:
                message = f"✅ Слово '{article_to_save} {word_to_save}' оновлено у вашому словнику!"
            else:
                message = f"✅ Слово '{word_to_save}' оновлено у вашому словнику!"
        else:
            if article_to_save:
                message = f"✅ Слово '{article_to_save} {word_to_save}' успішно додано!"
            else:
                message = f"✅ Слово '{word_to_save}' успішно додано!"
            
        bot.send_message(
            chat_id, 
            message, 
            reply_markup=main_menu_keyboard(chat_id)
        )
    else:
        bot.send_message(
            chat_id, 
            "❌ Помилка при збереженні слова.", 
            reply_markup=main_menu_keyboard(chat_id)
        )
    
    # Очищаємо стан користувача, зберігаючи тип словника для адміна
    preserve_dict_type = (chat_id == ADMIN_ID and dict_type == "common")
    clear_state(chat_id, preserve_dict_type=preserve_dict_type)

def start_activity(chat_id, mode):
    """Start learning or repetition activity"""
    # Зберігаємо поточний тип словника і рівень перед очищенням стану
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    print(f"Debug: Starting {mode} activity for user {chat_id} with dict_type={dict_type}, level={level}")
    
    clear_state(chat_id)
    
    # Відразу встановлюємо поточний тип словника і рівень після очищення
    user_state[chat_id] = {"dict_type": dict_type, "level": level}
    
    # Якщо це спільний словник, завжди отримуємо shared_dict_id з бази даних
    if dict_type == "shared":
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            shared_dict_id = result[0]
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
            print(f"Debug: Retrieved shared_dict_id={shared_dict_id} from database for user {chat_id}")
        else:
            print(f"Warning: User {chat_id} has dict_type 'shared' but no shared_dict_id in database")
    elif shared_dict_id:
        # Якщо не спільний словник, але shared_dict_id вказано, зберігаємо його
        user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    try:
        # Використовуємо ВИКЛЮЧНО SQLite для отримання слів
        import db_manager
        
        # Оновлюємо streak користувача
        streak = db_manager.update_user_streak(chat_id)
        print(f"User {chat_id} streak updated: {streak}")
        
        # Отримуємо слова для користувача з урахуванням типу словника
        df = None
        if dict_type == "shared" and shared_dict_id:
            # Для спільного словника викликаємо спеціальну функцію
            df = db_manager.get_shared_dictionary_words(chat_id, shared_dict_id)
            print(f"Got {len(df) if df is not None else 0} words from shared dictionary {shared_dict_id}")
        else:
            # Для персонального або загального словника використовуємо звичайний метод
            df = db_manager.get_user_words(chat_id, dict_type)
        
        # Перевіряємо результат
        if df is None or df.empty:
            dict_name = "спільному словнику" if dict_type == "shared" else "загальному словнику" if dict_type == "common" else "персональному словнику"
            bot.send_message(chat_id, f"📭 У {dict_name} ще немає доданих слів.")
            return False
            
        # Переконуємося, що всі необхідні колонки присутні
        if 'id' not in df.columns:
            print(f"WARNING: DataFrame lacks 'id' column!")
            # Додаємо id колонку зі значеннями за замовчуванням
            df['id'] = range(1, len(df) + 1)
            
        print(f"Successfully retrieved {len(df)} words from database with columns: {df.columns.tolist()}")
        
        # Запускаємо відповідну активність
        if mode == 'repeat':
            from handlers import start_repetition
            return start_repetition(chat_id, df)
        elif mode == 'learn':
            from handlers import start_learning
            return start_learning(chat_id, df)
    except Exception as e:
        print(f"ERROR using SQLite database: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, f"❌ Помилка при доступі до бази даних.")
        return False

def return_to_appropriate_menu(chat_id, success=True, message=None):
    """Return to the appropriate menu based on user's level"""
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    if not message:
        message = "✅ Завершено!" if success else "❌ Помилка!"
    
    if level == "easy":
        # Повернення до меню легкого рівня
        from utils import easy_level_keyboard
        bot.send_message(chat_id, message, reply_markup=easy_level_keyboard())
    else:
        # Повернення до головного меню
        from utils import main_menu_keyboard
        bot.send_message(chat_id, message, reply_markup=main_menu_keyboard(chat_id))

def set_dictionary_type(chat_id, dict_type):
    """Set dictionary type to personal or common"""
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    # Зберігаємо попередній тип для порівняння
    prev_type = user_state[chat_id].get("dict_type", "personal")
    
    # Встановлюємо новий тип словника
    user_state[chat_id]["dict_type"] = dict_type
    print(f"Set dictionary type for {chat_id} to {dict_type}")
    
    # Оновлюємо БД при зміні типу словника
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Інформуємо користувача про зміну
    if dict_type == "personal":
        # При переході на персональний словник очищаємо shared_dict_id в БД
        cursor.execute("UPDATE users SET shared_dict_id = NULL WHERE chat_id = ?", (chat_id,))
        conn.commit()
        
        message = f"📚 Обрано персональний словник."
        bot.send_message(chat_id, message, reply_markup=main_menu_keyboard(chat_id))
    elif dict_type == "common":
        # Для загального словника також очищаємо shared_dict_id в БД
        cursor.execute("UPDATE users SET shared_dict_id = NULL WHERE chat_id = ?", (chat_id,))
        conn.commit()
        
        message = f"📚 Обрано загальний словник."
        if chat_id != ADMIN_ID:
            message += "\n⚠️ У загальному словнику ви можете тільки вчити та повторювати слова."
        bot.send_message(chat_id, message, reply_markup=main_menu_keyboard(chat_id))
    elif dict_type == "shared":
        # Для спільного словника перевіряємо наявність активного словника
        cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            # Користувач вже має вибраний спільний словник
            shared_dict_id = result[0]
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
            
            # Отримуємо назву словника
            cursor.execute("SELECT name FROM shared_dictionaries WHERE id = ?", (shared_dict_id,))
            dict_name = cursor.fetchone()[0]
            
            # Показуємо меню з вибраним словником
            bot.send_message(
                chat_id,
                f"📚 Обрано спільний словник: <b>{dict_name}</b>",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(chat_id)
            )
        else:
            # Користувач ще не вибрав спільний словник
            from utils import shared_dictionary_keyboard
            bot.send_message(chat_id, "👥 Спільні словники - оберіть опцію:",
                        reply_markup=shared_dictionary_keyboard())
    
    conn.close()
    return dict_type

# Залишаємо toggle_dictionary для зворотної сумісності
def toggle_dictionary(chat_id):
    """Toggle between dictionaries"""
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    current = user_state[chat_id].get("dict_type", "personal")
    
    if current == "personal":
        new_type = "common"
    else:
        new_type = "personal"
    
    return set_dictionary_type(chat_id, new_type)
