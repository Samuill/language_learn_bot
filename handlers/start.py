# -*- coding: utf-8 -*-

"""
Start handler for the bot.
"""

import telebot
from config import bot, user_state
import db_manager
from utils import main_menu_keyboard
from utils.language_utils import get_text
from utils.state_helpers import save_message_id

# Define language flags and codes for easier identification
LANGUAGE_FLAGS = {
    "🇬🇧": "en",
    "🇺🇦": "uk",
    "🇷🇺": "ru",
    "🇹🇷": "tr",
    "🇸🇾": "ar"
}

# Language names in their native form
LANGUAGE_NAMES = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
    "tr": "Türkçe",
    "ar": "العربية"
}

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Handle the /start command - only show language selection for new users"""
    chat_id = message.chat.id
    
    # Check if user already has a language set
    import db_manager
    existing_language = db_manager.get_user_language(chat_id)
    
    if existing_language:
        # User already has language - redirect to main menu
        from handlers.main_menu import main_menu
        main_menu(message)
        return
    
    # New user - show language selection
    if chat_id in user_state:
        user_state.pop(chat_id)
    
    user_state[chat_id] = {"state": "language_selection"}
    show_language_selection(chat_id)

def show_language_selection(chat_id):
    """Show language selection keyboard to user"""
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Add language buttons in rows of 2
    row = []
    for flag, code in LANGUAGE_FLAGS.items():
        name = LANGUAGE_NAMES.get(code, code.upper())
        button_text = f"{flag} {name}"
        row.append(button_text)
        
        if len(row) == 2:
            keyboard.row(*row)
            row = []
    
    # Add any remaining buttons
    if row:
        keyboard.row(*row)
    
    sent_message = bot.send_message(
        chat_id,
        get_text("choose_language", chat_id),  # Use the localized key instead of hardcoded text
        reply_markup=keyboard
    )
    save_message_id(chat_id, sent_message.message_id)

@bot.message_handler(commands=['language', 'change_language', 'lang'])
def change_language_command(message):
    """Handle language change commands - force language selection"""
    chat_id = message.chat.id
    
    # Save important state data
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    level = user_state.get(chat_id, {}).get("level", "easy")
    
    # Set state for language selection but preserve key settings
    user_state[chat_id] = {
        "state": "language_selection",
        "dict_type": dict_type,
        "shared_dict_id": shared_dict_id,
        "level": level
    }
    
    # Show language selection
    show_language_selection(chat_id)

# Add message handlers for each specific language button to prioritize them
@bot.message_handler(func=lambda message: message.text in ["🇬🇧 English", "🇺🇦 Українська", "🇷🇺 Русский", "🇹🇷 Türkçe", "🇸🇾 العربية"])
def handle_language_button(message):
    """Handle direct language button presses"""
    chat_id = message.chat.id
    text = message.text
    
    # Map button text to language codes
    language_map = {
        "🇬🇧 English": "en",
        "🇺🇦 Українська": "uk",
        "🇷🇺 Русский": "ru",
        "🇹🇷 Türkçe": "tr",
        "🇸🇾 العربية": "ar"
    }
    
    language_code = language_map.get(text)
    
    if language_code:
        # Backup user state
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        try:
            # Update language in database
            success = db_manager.set_user_language(chat_id, language_code)
            
            # Clear language cache explicitly
            from utils.language_utils import clear_language_cache
            clear_language_cache(chat_id)
            
            if success:
                # Update user state
                user_state[chat_id] = {
                    "state": "main_menu",
                    "dict_type": dict_type,
                    "level": level,
                    "language": language_code
                }
                
                if shared_dict_id:
                    user_state[chat_id]["shared_dict_id"] = shared_dict_id
                
                # Send confirmation - IMPORTANT: Get text AFTER updating the language
                confirmation_message = get_text("language_selected", chat_id)
                bot.send_message(chat_id, confirmation_message)
                
                # Send main menu using localization
                menu_message = get_text("main_menu", chat_id)
                sent_message = bot.send_message(
                    chat_id, 
                    menu_message, 
                    reply_markup=main_menu_keyboard(chat_id)
                )
                save_message_id(chat_id, sent_message.message_id)
            else:
                bot.send_message(chat_id, get_text("error_occurred", chat_id))
        except Exception as e:
            print(f"Error setting language: {e}")
            bot.send_message(chat_id, get_text("error_occurred", chat_id))

@bot.message_handler(func=lambda message: user_state.get(message.chat.id, {}).get("state") == "language_selection")
def handle_language_selection(message):
    """Handle language selection from keyboard during language selection state"""
    chat_id = message.chat.id
    text = message.text
    
    # Define language mappings
    language_buttons = [
        ("🇬🇧", "en", "English"),
        ("🇺🇦", "uk", "Українська"),
        ("🇷🇺", "ru", "Русский"),
        ("🇹🇷", "tr", "Türkçe"),
        ("🇸🇾", "ar", "العربية")
    ]
    
    # Extract language code from button text
    language_code = None
    
    for flag, code, name in language_buttons:
        if flag in text or name in text:
            language_code = code
            break
    
    if not language_code:
        bot.send_message(chat_id, "Sorry, I couldn't recognize your language choice. Please try again.")
        return
    
    try:
        # Save previous state settings we want to keep
        dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
        shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
        level = user_state.get(chat_id, {}).get("level", "easy")
        
        # Update language in database
        db_manager.set_user_language(chat_id, language_code)
        
        # Update user state
        user_state[chat_id] = {
            "state": "main_menu",
            "dict_type": dict_type,
            "level": level,
            "language": language_code  # Store the selected language in state
        }
        
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        
        # Send confirmation message using localization
        bot.send_message(chat_id, get_text("language_selected", chat_id))
        
        # Send main menu message using localization
        menu_markup = main_menu_keyboard(chat_id)
        sent_message = bot.send_message(
            chat_id, 
            get_text("main_menu", chat_id), 
            reply_markup=menu_markup
        )
        save_message_id(chat_id, sent_message.message_id)
        
    except Exception as e:
        print(f"Error in language selection: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(chat_id, get_text("error_occurred", chat_id))
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
import requests
# Шлях до PID файлу для запобігання запуску кількох екземплярів бота
PID_FILE = "bot.pid"
DEBUG_MODE = True
# Record start time for uptime calculation
START_TIME = time.time()

def check_instance():
    """Перевіряє, чи вже запущено екземпляр бота"""
    try:
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
                    print("psutil not installed, cannot reliably check if another instance is running by PID.")
                    pass
                    
            except (IOError, ValueError) as e:
                print(f"Error reading or parsing PID file: {e}. Assuming no other instance or stale PID file.")
                pass # Проблеми з читанням PID або перевіркою процесу
        
        # Записуємо поточний PID до файлу
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        
        return True
    except Exception as e:
        print(f"Unexpected error in check_instance: {e}")
        return True # Allow bot to start if PID check fails unexpectedly


def cleanup():
    """Видалення PID файлу при завершенні роботи"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            print("PID file removed.")
    except OSError as e:
        print(f"Error removing PID file: {e}")
    except Exception as e:
        print(f"Unexpected error in cleanup: {e}")

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print("\nReceived shutdown signal. Stopping bot...")
    
    cleanup() # Call cleanup here to remove PID file on shutdown

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
    try:
        for chat_id in list(user_state.keys()): # Iterate over a copy of keys for safe modification
            if "dict_type" in user_state.get(chat_id, {}): # Check if chat_id still exists
                user_state[chat_id]["dict_type"] = "personal"
                # Also remove shared_dict_id if resetting to personal
                if "shared_dict_id" in user_state[chat_id]:
                    del user_state[chat_id]["shared_dict_id"]
        print("User dictionaries reset to 'personal' on startup.")
    except Exception as e:
        print(f"Error resetting dictionaries: {e}")


@bot.message_handler(commands=['language', 'lang', 'change_language'])
def change_language_command(message):
    """Handle language change command"""
    try:
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
    except Exception as e:
        print(f"Error in change_language_command for chat_id {message.chat.id if message else 'N/A'}: {e}")
        if message and message.chat:
            bot.send_message(message.chat.id, "An error occurred while trying to change language. Please try again later.")


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
    try:
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
        print("Database setup check complete.")
    except Exception as e:
        print(f"Error during database setup: {e}")
        import traceback
        traceback.print_exc()

def setup_logging():
    """Set up logging for the application"""
    try:
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
    except Exception as e:
        print(f"Error setting up logging: {e}")
        # Fallback to basic print if logging setup fails
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.error(f"Logging setup failed: {e}", exc_info=True)
        return logging.getLogger(__name__) # Return a basic logger

# configure file logging for all bot traffic
logging.basicConfig(
    filename='bot2.log', level=logging.INFO,
    format='%(asctime)s %(message)s'
)
# listener to log every incoming update
def log_all_updates(messages):
    for message in messages:
        if hasattr(message, 'text'):
            chat_id = message.chat.id
            text = message.text
            log_str = f"INCOMING | From: {chat_id} | Text: {text}"
            logging.info(log_str)
            print(f"[SERVER LOG] {log_str}")
# attach listener
bot.set_update_listener(log_all_updates)

def main():
    """Main entry point for the bot"""
    if not check_instance(): # Check if another instance is running
        return

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure cleanup runs on exit, even if not via signal (e.g. normal termination)
    import atexit
    atexit.register(cleanup)

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
    
    print("Bot is starting to poll...")
    try:
        # Start bot polling - increase interval to reduce API requests
        bot.polling(none_stop=True, interval=1, timeout=60)
    except requests.exceptions.ReadTimeout:
        print("Bot polling ReadTimeout. Restarting polling...")
        time.sleep(10) # Wait a bit before restarting
        main() # Be careful with recursion here, might need a loop
    except requests.exceptions.ConnectionError:
        print("Bot polling ConnectionError. Retrying in 60 seconds...")
        time.sleep(60)
        main() # Be careful with recursion here
    except Exception as e:
        print(f"Critical error in bot polling loop: {e}")
        import traceback
        traceback.print_exc()
        from debug_logger import log_error
        log_error(e, "Critical error in main loop")

if __name__ == "__main__":
    main()
