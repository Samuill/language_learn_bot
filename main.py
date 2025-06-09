# -*- coding: utf-8 -*-
import datetime
import logging
import os
import signal
import sys
import time
import threading
from config import user_state
from config import bot, scheduler
import db_manager

# Шлях до PID файлу для запобігання запуску кількох екземплярів бота
PID_FILE = "bot.pid"
DEBUG_MODE = True
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
    """Handle shutdown signals gracefully"""
    print("\nReceived shutdown signal. Stopping bot...")
    
    try:
        # Stop bot polling first
        bot.stop_polling()
        print("Bot polling stopped.")
    except Exception as e:
        print(f"Error stopping bot polling: {e}")
    
    try:
        # Check if scheduler is running before attempting to shut it down
        if scheduler.running:
            scheduler.shutdown(wait=False)
            print("Scheduler stopped.")
        else:
            print("Scheduler was not running.")
    except Exception as e:
        print(f"Error stopping scheduler: {e}")
    
    try:
        # Log the shutdown
        from debug_logger import log_action
        log_action("Bot stopped", {"reason": "shutdown_signal"})
    except Exception as e:
        print(f"Error logging shutdown: {e}")
    
    print("Bot shutdown complete.")
    sys.exit(0)

def reset_dictionaries():
    """Скидаємо всі активні словники до персонального при запуску"""
    for chat_id in user_state:
        if "dict_type" in user_state[chat_id]:
            user_state[chat_id]["dict_type"] = "personal"

@bot.message_handler(commands=['language', 'lang', 'change_language'])
def change_language_command(message):
    """Handle language change command"""
    chat_id = message.chat.id
    
    print(f"Language command received from user {chat_id}")
    
    # Set state for language selection
    user_state[chat_id] = {
        "state": "language_selection",
        "dict_type": user_state.get(chat_id, {}).get("dict_type", "personal"),
        "shared_dict_id": user_state.get(chat_id, {}).get("shared_dict_id")
    }
    
    print(f"Updated user state: {user_state[chat_id]}")
    
    # Show language selection keyboard
    from utils.language_utils import create_language_keyboard
    keyboard = create_language_keyboard()
    
    print(f"Sending language selection keyboard to user {chat_id}")
    bot.send_message(
        chat_id, 
        "Please select your language / Оберіть мову / Выберите язык:", 
        reply_markup=keyboard
    )

def setup_scheduler():
    """Set up the scheduler for reminders - replacement for the missing setup_scheduler function"""
    try:
        # Schedule the daily reminder job
        from scheduler import schedule_reminders
        job = schedule_reminders()
        
        # Log success with standard logging instead of log_action
        print(f"Daily reminder scheduled for {job[0]} (job id: {job[1]})")
        logging.info(f"Scheduler initialized with job ID: {job[1]}")
        return True
    except Exception as e:
        print(f"Error setting up scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False

# Initialize the database schema on startup if needed
def setup_database():
    """Initialize the database with necessary tables"""
    # Initialize database
    db_manager.init_db()
    
    # Ensure the active_days column exists in users table
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Check if active_days column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'active_days' not in columns:
        print("Adding active_days column to users table")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN active_days INTEGER DEFAULT 0")
            conn.commit()
            print("Successfully added active_days column")
        except Exception as e:
            print(f"Error adding active_days column: {e}")
    
    conn.close()

def setup_logging():
    """Set up logging for the application"""
    import logging
    import os
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    log_file = os.path.join(log_dir, 'bot.log')
    
    # Set up basic configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")
    
    return logger

def main():
    """Main entry point for the bot"""
    print("Bot started at {}...".format(
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("Press Ctrl+C to stop the bot")
    
    # Setup database
    setup_database()
    
    # Setup logging
    setup_logging()
    
    # Set up message handlers
    import handlers.main_menu
    import handlers.dictionaries
    import handlers.start
    import handlers.add_word
    import handlers.easy_level
    import handlers.medium_level
    import handlers.hard_level
    import handlers.shared_dicts
    import handlers.possessive_articles
    
    # Admin handlers
    import handlers.admin
    
    # Try to add optional/experimental handlers
    try:
        import handlers.status
    except ImportError:
        pass
    
    # Initialize reminder scheduler
    setup_scheduler()
    
    try:
        # Start bot polling - increase interval to reduce API requests
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        from debug_logger import log_error
        log_error(e, "Critical error in main loop")

if __name__ == "__main__":
    main()
