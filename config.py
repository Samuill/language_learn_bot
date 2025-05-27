# -*- coding: utf-8 -*-
import telebot
import os
from googletrans import Translator
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "7616425414:AAFaZCuYss9UyNSXm_MJCd42rLjAKNWy0Mc"
ADMIN_ID = 476376623

# Global objects
bot = telebot.TeleBot(TOKEN)
translator = Translator()
scheduler = BackgroundScheduler()
user_state = {}

# Constants
COMMON_DICT_FILE = "common_dictionary.csv"
PERSONAL_DICT_FOLDER = "personal_dictionaries"
PERSONAL_DICT_TEMPLATE = "{user_id}_dictionary.csv"

# Dictionary access permissions
class DictionaryAccess:
    # For personal dictionaries
    PERSONAL_READ = True   # All users can read their own dictionary
    PERSONAL_WRITE = True  # All users can add to their own dictionary
    
    # For common/global dictionary
    COMMON_READ = True     # All users can read common dictionary
    COMMON_WRITE = False   # Regular users cannot add to common dictionary

# Ensure personal dictionary folder exists
if not os.path.exists(PERSONAL_DICT_FOLDER):
    os.makedirs(PERSONAL_DICT_FOLDER)

# Helper functions for dictionary access
def get_personal_dict_path(user_id):
    """Get the file path for a user's personal dictionary"""
    return os.path.join(PERSONAL_DICT_FOLDER, PERSONAL_DICT_TEMPLATE.format(user_id=user_id))

def can_edit_common_dict(user_id):
    """Check if user has rights to edit the common dictionary"""
    return user_id == ADMIN_ID
