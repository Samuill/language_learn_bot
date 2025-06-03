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
    
    # Скидаємо всі активні словники до персонального
    reset_dictionaries()
    
    # Перевіряємо доступ до бази даних
    try:
        import db_manager
        conn = db_manager.get_connection()
        print(f"Successfully connected to database at {db_manager.DB_PATH}")
        
        # Міграція та виправлення даних спільних словників
        try:
            from migration_tools import migrate_shared_dictionary_users, fix_dictionary_admin_status
            migrate_shared_dictionary_users()
            fix_dictionary_admin_status()
        except Exception as e:
            print(f"Error during shared dictionary migration: {e}")
            import traceback as tb  # Перейменовуємо імпорт, щоб уникнути конфлікту
            tb.print_exc()
        
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        traceback.print_exc()
    
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
    
    while True:
        try:
            print(f"Bot started at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
            # Збільшуємо таймаут до 60 секунд (замість 25 за замовчуванням)
            bot.polling(none_stop=True, interval=1, timeout=60, long_polling_timeout=60)
        except requests.exceptions.ConnectionError:
            print("Помилка з'єднання. Повторна спроба через 5 секунд...")
            time.sleep(5)
        except requests.exceptions.ReadTimeout:
            print("Таймаут читання. Повторна спроба через 5 секунд...")
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
