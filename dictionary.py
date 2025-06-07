# -*- coding: utf-8 -*-
from config import user_state, bot, ADMIN_ID
from utils import clear_state, main_menu_keyboard
import db_manager
from german_article_finder import find_german_article  # Додаємо імпорт новою функції
import pandas as pd  # Add missing import for pandas

def save_word(chat_id, manual_translation=None):
    """Save word to user dictionary"""
    if chat_id not in user_state:
        return False
    
    state = user_state[chat_id]
    if "word" not in state:
        return False
    
    word = state["word"]
    
    # Determine which translation to use
    translation = manual_translation if manual_translation else state.get("auto_translation", "")
    
    # Determine dictionary type
    dict_type = state.get("dict_type", "personal")
    if dict_type == "common" and chat_id != ADMIN_ID:
        return False
    
    if dict_type == "personal":
        from storage import get_dataframe, save_dataframe, get_user_file_path
        
        file_path, language = get_user_file_path(chat_id)
        try:
            df = get_dataframe(chat_id)
            
            # Перевірка та виправлення структури DataFrame
            if 'word' not in df.columns:
                df['word'] = ""
            if 'translation' not in df.columns:
                df['translation'] = ""
            if 'priority' not in df.columns:
                df['priority'] = 0.0
            
            # Check if word already exists
            if not df[df['word'] == word].empty:
                return False
            
            # Add new word
            df.loc[len(df)] = {
                'word': word, 
                'translation': translation, 
                'priority': 0.0
            }
            
            save_dataframe(chat_id, df, language)
            return True
        except Exception as e:
            print(f"Error saving word to personal dictionary: {e}")
            return False
    
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

def start_activity(chat_id, mode, exclude_max_rating=False):
    """Start learning or repetition activity"""
    # Зберігаємо поточний тип словника і рівень перед очищенням стану
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal") 
    level = user_state.get(chat_id, {}).get("level", "easy")
    # Отримуємо shared_dict_id ДО очищення стану
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id", None)
    
    print(f"Debug: Starting {mode} activity for user {chat_id} with dict_type={dict_type}, level={level}, shared_dict_id={shared_dict_id}")
    
    # Оновлюємо стан користувача і видаляємо повідомлення активності
    clear_state(chat_id, preserve_dict_type=True, preserve_messages=False)
    
    # Відновлюємо необхідні параметри після очищення
    new_state = {"dict_type": dict_type, "level": level}
    if shared_dict_id:
        new_state["shared_dict_id"] = shared_dict_id
    user_state[chat_id] = new_state
    
    # Якщо це спільний словник, переконаємось, що shared_dict_id правильний
    if dict_type == "shared":
        if not shared_dict_id:
            # Спробуємо отримати shared_dict_id з бази даних
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT shared_dict_id FROM users WHERE chat_id = ?", (chat_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                user_state[chat_id]["shared_dict_id"] = result[0]
                print(f"Retrieved shared_dict_id={result[0]} from database for user {chat_id}")
    
    try:
        # Оновлюємо streak користувача
        streak = db_manager.update_user_streak(chat_id)
        
        # Отримуємо слова для користувача з урахуванням типу словника
        df = None
        if dict_type == "shared":
            current_shared_dict_id = user_state[chat_id].get("shared_dict_id")
            if current_shared_dict_id:
                df = db_manager.get_shared_dictionary_words(chat_id, current_shared_dict_id)
                print(f"Got {len(df) if df is not None else 0} words from shared dictionary {current_shared_dict_id}")
            else:
                print("Error: shared_dict_id is missing for shared dictionary type")
                bot.send_message(chat_id, "❌ Помилка: не вибрано спільний словник.")
                return False
        else:
            df = db_manager.get_user_words(chat_id, dict_type)
        
        # Фільтрація слів з максимальним рейтингом для не-складних рівнів, якщо потрібно
        if exclude_max_rating and len(df) > 5:  # Якщо слів достатньо багато для фільтрації
            df_filtered = df[df['priority'] < 4.9]
            
            # Якщо після фільтрації залишилось достатньо слів, використовуємо фільтрований набір
            if len(df_filtered) >= 5:
                df = df_filtered
                print(f"Filtered out max-rating words, {len(df)} words remaining")
        
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
        
        # Для складного рівня беремо 30% найтяжчих слів
        if level == "hard":
            # Переконаємося, що priority має числовий тип
            df['priority'] = pd.to_numeric(df['priority'], errors='coerce').fillna(0.0)
            
            # Вивід статистики рейтингів для відлагодження
            print(f"DEBUG priority stats: min={df['priority'].min()}, max={df['priority'].max()}, mean={df['priority'].mean()}")
            print(f"DEBUG priority distribution: {df['priority'].value_counts().sort_index().to_dict()}")
            
            # Сортуємо за рейтингом у спадаючому порядку (найвищі рейтинги спочатку)
            df = df.sort_values(by='priority', ascending=False)
            
            # Беремо верхні 30% слів
            top_words_count = max(1, int(len(df) * 0.3))
            df = df.head(top_words_count)
            
            # Показуємо деталі про обрані слова
            print(f"Hard level: selected {len(df)} top-rated words. Ratings: {df['priority'].tolist()[:5]}")
        
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
    
    try:
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
    except Exception as e:
        print(f"Error in set_dictionary_type: {e}")
    finally:
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
