# -*- coding: utf-8 -*-

"""
Основні функції для обробників телеграм-бота.
Цей модуль містить спільні функції, що використовуються в різних обробниках.
"""

import random
import telebot
import pandas as pd
from config import bot, user_state

# NOTE: Easy level games have been moved to handlers/easy_level.py
# These functions are left empty as stubs for backward compatibility
# and will be removed in a future version

# Replace the easy level functions with stubs that redirect to easy_level.py
def start_learning(chat_id, df):
    """Stub: Start learning new words activity (moved to easy_level.py)"""
    from handlers.easy_level import start_learning
    return start_learning(chat_id, df)

def start_repetition(chat_id, df):
    """Stub: Start repetition activity (moved to easy_level.py)"""
    from handlers.easy_level import start_repetition
    return start_repetition(chat_id, df)

def start_article_activity(chat_id):
    """Stub: Start learning articles activity (moved to easy_level.py)"""
    from handlers.easy_level import start_article_activity
    return start_article_activity(chat_id)

# You can keep other non-easy level core functionality here
