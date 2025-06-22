# -*- coding: utf-8 -*-

"""
Обробники для бота вивчення німецької.

У цьому пакеті зібрані всі обробники повідомлень для телеграм-боту.
"""

# Основні обробники
from .main_menu import main_menu, cancel_action, return_to_main_menu
from .start import start_handler, show_language_selection

# Імпорт обробників для різних рівнів складності
from .easy_level import learn_words, repeat_words, learn_articles
from .medium_level import spelling_choice_game, missing_letters_game
from .hard_level import hard_game, word_typing_game, article_typing_game

# Імпорт обробників для роботи зі словником
from .add_word import add_word
from .dictionaries import set_difficulty_level, personal_dictionary_button
from .shared_dicts import shared_dictionary_menu, create_shared_dictionary, join_shared_dictionary
from .shared_dicts import my_shared_dictionaries, use_shared_dictionary

# Імпорт функцій для активностей
from .easy_level import start_learning, start_repetition, start_article_activity

# Імпорт обробника для присвійних займенників
from .possessive_articles import start_possessive_exercise_handler

# Адміністративні обробники
from .admin import test_fire, stop_bot

# Додаткові імпорти для зворотньої сумісності
from .articles import learn_articles_handler
