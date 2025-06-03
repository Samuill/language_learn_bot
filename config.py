# -*- coding: utf-8 -*-
import os
import telebot
from googletrans import Translator
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# TOKEN = "7616425414:AAFaZCuYss9UyNSXm_MJCd42rLjAKNWy0Mc"
TOKEN = "7588170834:AAEpkiHnLxUY_HJBmY3_OEeGB0q_gg259Dw"
ADMIN_ID = 476376623  # ID адміністратора

# Глобальні об'єкти
bot = telebot.TeleBot(TOKEN, num_threads=4)  # Збільшуємо кількість потоків
translator = Translator()
scheduler = BackgroundScheduler()
user_state = {}

# Створюємо директорію для словників, якщо її немає
USER_DICT_DIR = "user_dictionaries"
if not os.path.exists(USER_DICT_DIR):
    try:
        os.makedirs(USER_DICT_DIR)
    except Exception as e:
        print(f"Error creating directory {USER_DICT_DIR}: {e}")

# Константи для шляхів
COMMON_DICT_FILE = os.path.join(USER_DICT_DIR, "common_dictionary.csv")
PERSONAL_DICT_TEMPLATE = "{user_id}_dictionary.csv"

# Dictionary access permissions
class DictionaryAccess:
    # For personal dictionaries
    PERSONAL_READ = True   # All users can read their own dictionary
    PERSONAL_WRITE = True  # All users can add to their own dictionary
    
    # For common/global dictionary
    COMMON_READ = True     # All users can read common dictionary
    COMMON_WRITE = False   # Regular users cannot add to common dictionary

# Helper functions for dictionary access
def get_personal_dict_path(user_id):
    """Get the file path for a user's personal dictionary"""
    return os.path.join(USER_DICT_DIR, PERSONAL_DICT_TEMPLATE.format(user_id=user_id))

def can_edit_common_dict(user_id):
    """Check if user has rights to edit the common dictionary"""
    return user_id == ADMIN_ID

# Налаштування таймаутів для запитів до API Telegram
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
    backoff_factor=1
)
adapter = HTTPAdapter(max_retries=retry_strategy)
bot_session = requests.Session()
bot_session.mount("https://", adapter)
bot_session.mount("http://", adapter)

# Встановлюємо цю сесію для telebot
import telebot.apihelper
telebot.apihelper.SESSION = bot_session
telebot.apihelper.CONNECT_TIMEOUT = 60  # Збільшуємо таймаут підключення
telebot.apihelper.READ_TIMEOUT = 60     # Збільшуємо таймаут читання

# Enable debug mode
DEBUG_MODE = True

# Original send_message function to be patched for debug logging
original_send_message = telebot.TeleBot.send_message

# Patch the send_message method to add logging
def send_message_with_logging(self, chat_id, text, *args, **kwargs):
    """Override of TeleBot.send_message that adds logging"""
    # Call original implementation
    result = original_send_message(self, chat_id, text, *args, **kwargs)
    
    if DEBUG_MODE:
        try:
            from debug_logger import log_response
            log_response(chat_id, text)
        except Exception as e:
            print(f"Error in debug logging: {e}")
    
    return result

# Apply the patch
telebot.TeleBot.send_message = send_message_with_logging
