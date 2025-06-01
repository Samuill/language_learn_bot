# -*- coding: utf-8 -*-
import time
import requests
import os
import sys
import signal
import traceback
import sqlite3  # Додаємо імпорт sqlite3
from config import bot, scheduler, user_state, DEBUG_MODE
from scheduler import setup_scheduler
import handlers  # Import handlers to register them

# Шлях до PID файлу для запобігання запуску кількох екземплярів бота
PID_FILE = "bot.pid"

# Record start time for uptime calculation
START_TIME = time.time()

def check_instance():
    """Перевіряє, чи вже запущено екземпляр бота"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            
            # Перевіряємо, чи процес із цим PID все ще активний
            try:
                import psutil
                if psutil.pid_exists(old_pid):
                    print(f"Бот вже запущено (PID: {old_pid})! Закриваємо цей екземпляр.")
                    return False
            except ImportError:
                # Якщо psutil не встановлено, просто продовжуємо
                pass
                
        except (IOError, ValueError):
            # Проблеми з читанням PID або перевіркою процесу
            pass
    
    # Записуємо поточний PID до файлу
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    
    return True

def cleanup():
    """Видалення PID файлу при завершенні роботи"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass

def signal_handler(sig, frame):
    """Обробник сигналів для коректного завершення"""
    print("Завершення роботи бота...")
    cleanup()
    scheduler.shutdown(wait=False)
    sys.exit(0)

def reset_dictionaries():
    """Скидаємо всі активні словники до персонального при запуску"""
    for chat_id in user_state:
        if "dict_type" in user_state[chat_id]:
            user_state[chat_id]["dict_type"] = "personal"

def migrate_files():
    """Переміщує старі файли користувача в новий каталог"""
    from storage import USER_DICT_DIR
    
    # Створюємо директорію, якщо вона не існує
    if not os.path.exists(USER_DICT_DIR):
        try:
            os.makedirs(USER_DICT_DIR)
            print(f"Created directory {USER_DICT_DIR}")
        except Exception as e:
            print(f"Failed to create directory {USER_DICT_DIR}: {e}")
    
    # Знаходимо усі файли словників у поточній директорії
    word_files = [f for f in os.listdir() if (f.startswith("ru_words_") or f.startswith("uk_words_")) and f.endswith(".csv")]
    
    # Переміщуємо файли до нової директорії
    import shutil
    moved_count = 0
    for file in word_files:
        try:
            source = file
            target = os.path.join(USER_DICT_DIR, file)
            
            # Якщо файл уже існує в цільовій директорії, порівнюємо розміри
            if os.path.exists(target):
                if os.path.getsize(source) > os.path.getsize(target):
                    shutil.copy2(source, target)
                    print(f"Copied newer/larger file {source} to {target}")
                    moved_count += 1
            else:
                shutil.move(source, target)
                print(f"Moved file {source} to {target}")
                moved_count += 1
        except Exception as e:
            print(f"Failed to move file {file}: {e}")
    
    print(f"Migration complete. Moved {moved_count} files.")
    
    # Переміщуємо загальний словник, якщо він є
    if os.path.exists("common_dictionary.csv"):
        try:
            source = "common_dictionary.csv"
            target = os.path.join(USER_DICT_DIR, "common_dictionary.csv")
            if not os.path.exists(target):
                shutil.move(source, target)
                print(f"Moved common dictionary to {target}")
            elif os.path.getsize(source) > os.path.getsize(target):
                shutil.copy2(source, target)
                print(f"Copied newer/larger common dictionary to {target}")
        except Exception as e:
            print(f"Failed to move common dictionary: {e}")

def migrate_to_sqlite():
    """Migrate data from CSV to SQLite if needed"""
    import os
    from db_init import DB_PATH, create_database, migrate_from_csv
    
    if not os.path.exists(DB_PATH):
        print("\n=== STARTING MIGRATION FROM CSV TO SQLITE ===")
        print("Creating new SQLite database...")
        create_database()
        print("Migrating data from CSV files...")
        migrate_from_csv()
        print("=== MIGRATION COMPLETED ===\n")
    else:
        print(f"SQLite database already exists at {DB_PATH}")
        # Перевіряємо, чи є нові CSV файли для міграції
        from storage import USER_DICT_DIR
        import glob
        
        user_dict_pattern = os.path.join(USER_DICT_DIR, "*_words_*.csv")
        user_dict_files = glob.glob(user_dict_pattern)
        
        if user_dict_files:
            print(f"Found {len(user_dict_files)} CSV files that might need migration.")
            
            # Перевіряємо, чи всі користувачі вже мігровані
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Отримуємо список існуючих таблиць користувачів
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'user_%'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Перевіряємо, чи є CSV файли для користувачів, які ще не мігровані
            need_migration = False
            for file_path in user_dict_files:
                filename = os.path.basename(file_path)
                import re
                match = re.search(r'_(\d+)\.csv$', filename)
                if match:
                    chat_id = match.group(1)
                    if f"user_{chat_id}" not in existing_tables:
                        need_migration = True
                        break
            
            conn.close()
            
            if need_migration:
                print("New CSV files found. Running migration...")
                migrate_from_csv()
            else:
                print("All users are already migrated.")

def main():
    """Main function to run the bot"""
    # Перевірка, чи вже запущено екземпляр бота
    if not check_instance():
        return
    
    # Реєстрація обробників сигналів для правильного завершення
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # При виході з програми видаляємо PID файл
    import atexit
    atexit.register(cleanup)
    
    # Переміщуємо існуючі файли в новий каталог
    migrate_files()
    
    # Скидаємо всі активні словники до персонального
    reset_dictionaries()
    
    # Міграція даних з CSV до SQLite, якщо потрібно
    migrate_to_sqlite()
    
    # Додамо логування для відстеження типів словників при старті
    print("Initializing user dictionaries state:")
    for chat_id, state in user_state.items():
        dict_type = state.get("dict_type", "personal")
        print(f"User {chat_id} using dictionary type: {dict_type}")
    
    setup_scheduler()
    
    # Setup debug logging
    if DEBUG_MODE:
        from debug_logger import log_error, log_dict_operation
        print(f"Debug logging enabled. Logs will be saved to logs/debug.log")
        
        # Log file permissions for troubleshooting
        try:
            from storage import USER_DICT_DIR
            common_file = os.path.join(USER_DICT_DIR, "common_dictionary.csv")
            if os.path.exists(common_file):
                import stat
                permissions = os.stat(common_file).st_mode
                print(f"Common dictionary permissions: {stat.filemode(permissions)}")
                print(f"Is writable: {os.access(common_file, os.W_OK)}")
        except Exception as e:
            print(f"Error checking file permissions: {e}")
    
    while True:
        try:
            print(f"Bot started at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
            bot.polling(none_stop=True, interval=1)
        except requests.exceptions.ConnectionError:
            print("Помилка з'єднання. Повторна спроба через 5 секунд...")
            time.sleep(5)
        except Exception as e:
            print(f"Критична помилка: {e}")
            print(f"Тип помилки: {type(e).__name__}")
            traceback.print_exc()
            
            # Log error to debug log
            if DEBUG_MODE:
                from debug_logger import log_error
                log_error(e, "Critical error in main loop")
                
            time.sleep(5)

if __name__ == '__main__':
    main()
