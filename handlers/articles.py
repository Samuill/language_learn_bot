# -*- coding: utf-8 -*-

"""
Обробники для вивчення артиклів.
"""

from config import bot, user_state
import db_manager

@bot.message_handler(func=lambda message: message.text == "🏷️ Вивчати артиклі")
def learn_articles_handler(message):
    """Handler for learning articles - redirect to easy_level.py"""
    from handlers.easy_level import learn_articles
    learn_articles(message)
