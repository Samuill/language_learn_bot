# -*- coding: utf-8 -*-

"""
Обробники для повторення слів.
"""

from config import bot, user_state

@bot.message_handler(func=lambda message: message.text == "🔄 Повторити")
def repeat_words_handler(message):
    """Handler for repeat words - redirect to easy_level.py"""
    from handlers.easy_level import repeat_words
    repeat_words(message)
