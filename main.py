# -*- coding: utf-8 -*-
import datetime
import logging
import os
import signal
import sys
import time
import threading

# Enable middleware support before initializing the bot
import telebot.apihelper
telebot.apihelper.ENABLE_MIDDLEWARE = True

# Now import the bot and other modules
from config import bot, scheduler
import db_manager
import handlers
# Import everything else...

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
    """Setup APScheduler for daily reminders"""
    try:
        from scheduler import send_reminder
        import random
        
        # Check if scheduler is already running
        if scheduler.running:
            print("Scheduler is already running, skipping setup...")
            return
        
        # Check if there's already a job with this ID before adding it
        existing_jobs = [job.id for job in scheduler.get_jobs()]
        
        # Use unique job ID by adding random suffix to avoid conflicts
        reminder_job_id = f"daily_reminder_{random.randint(1000, 9999)}"
        
        # Create a job to send reminders daily at 18:00
        if "daily_reminder" not in existing_jobs:
            scheduler.add_job(
                send_reminder, 
                'cron', 
                hour=18, 
                minute=0,
                id=reminder_job_id,
                replace_existing=True
            )
            print(f"Daily reminder scheduled for 18:00 (job id: {reminder_job_id})")
        else:
            print("Daily reminder already scheduled, skipping...")
        
        # Start the scheduler in a separate thread
        if not scheduler.running:
            scheduler.start()
            log_action("Reminder scheduler initialized")
        
    except Exception as e:
        print(f"Error setting up scheduler: {e}")
        import traceback
        traceback.print_exc()

def setup_logging():
    """Set up logging configuration"""
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    # Set up file handler for logging
    log_file = os.path.join(logs_dir, "debug.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Set up formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Get logger and add handler
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    
    print(f"Debug logging enabled. Logs will be saved to {log_file}")
    
    # Setup console logger for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set up comprehensive interaction logging middleware
    try:
        from logging_middleware import setup_logging_middleware
        setup_logging_middleware()
        print("Comprehensive logging middleware enabled")
    except Exception as e:
        print(f"Error setting up logging middleware: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run the bot"""
    try:
        # Import required modules at the top
        import traceback  # Add explicit import of traceback
        import db_manager  # Ensure db_manager is imported
        import datetime
        
        # Initialize logging
        import logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        # Load user states from database to ensure consistency
        print("Loading user states from database...")
        db_manager.update_user_state_from_db()
        
        # Initialize database
        print("Initializing database...")
        # Use create_database instead of setup_database
        db_manager.create_database()
        
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
        
        # Завантаження станів користувачів з бази даних для забезпечення узгодженості
        print("Loading user states from database...")
        db_manager.update_user_state_from_db()
        
        # Додамо логування для відстеження типів словників при старті
        print("Initializing user dictionaries state:")
        for chat_id, state in user_state.items():
            dict_type = state.get("dict_type", "personal")
            print(f"User {chat_id} using dictionary type: {dict_type}")
        
        # Setup the scheduler
        setup_scheduler()
        
        # Setup debug logging
        if DEBUG_MODE:
            from debug_logger import log_error, log_dict_operation
            print(f"Debug logging enabled. Logs will be saved to logs/debug.log")
        
        # Register command handlers
        bot.set_my_commands([
            telebot.types.BotCommand("/start", "Start the bot"),
            telebot.types.BotCommand("/language", "Change language")
        ])
        
        # Setup enhanced logging
        setup_logging()
        
        print(f"Bot started at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
        print("Press Ctrl+C to stop the bot")
        
        # Start polling in a try-except block
        while True:
            try:
                bot.polling(none_stop=True, interval=1, timeout=60)
                break  # If polling exits normally, break the loop
            except requests.exceptions.ConnectionError:
                print("Connection error. Retrying in 5 seconds...")
                time.sleep(5)
            except requests.exceptions.ReadTimeout:
                print("Read timeout. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                print(f"Critical error: {e}")
                traceback.print_exc()
                if DEBUG_MODE:
                    from debug_logger import log_error
                    log_error(e, "Critical error in main loop")
                time.sleep(5)
    except Exception as e:
        log_error(f"Critical error: {e}", "Critical error in main loop")
        print(f"Critical error: {e}")
        import traceback  # Import traceback here as well for redundancy
        traceback.print_exc()

if __name__ == "__main__":
    try:
        # Initialize database before starting the bot
        import db_manager
        # Use create_database instead of setup_database
        db_manager.create_database()
        print("Database initialized successfully")
        main()
    except Exception as e:
        print(f"Error setting up database: {e}")
        import traceback  # Import traceback here for redundancy
        traceback.print_exc()

# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
from config import bot, scheduler
import db_manager
from utils.language_utils import create_language_keyboard
from utils.logger import log_action, log_error
from scheduler import setup_scheduler  # Import the scheduler setup function

# Load environment variables from .env file
load_dotenv()
print("Using environment variables from .env file")

# Логуємо запуск бота
log_action("Bot starting", {"version": "1.0", "environment": os.environ.get("ENVIRONMENT", "production")})

# Set up scheduler
setup_scheduler()
log_action("Reminder scheduler initialized")

# Set up database
try:
    db_manager.setup_database()
    log_action("Database setup complete")
except Exception as e:
    log_error(e, "Error setting up database")
    raise

# Import handlers to register them
try:
    import handlers
    log_action("Handlers registered successfully")
except Exception as e:
    log_error(e, "Error registering handlers")
    raise

# Start the bot
if __name__ == "__main__":
    # Start the scheduler in a background thread
    scheduler.start()
    log_action("Scheduler started")
    
    print("Bot started!")
    log_action("Bot polling started")
    
    # Start bot polling with error handling
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
    except Exception as e:
        print(f"Error in bot polling: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Graceful shutdown
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
                print("Scheduler shutdown complete.")
        except Exception as e:
            print(f"Error during scheduler shutdown: {e}")
        
        log_action("Bot stopped")
        print("Bot stopped gracefully.")
