# -*- coding: utf-8 -*-

"""
Модуль обробників для телеграм-бота вивчення німецької мови.
Цей файл імпортує обробники з усіх модулів для реєстрації їх у боті.
"""

# Імпортуємо всі модулі обробників, щоб вони зареєструвалися
from . import core
from . import main_menu
from . import add_word
from . import learn
from . import repeat
from . import articles
from . import dictionaries
from . import shared_dicts
from . import admin

# Експортуємо функції, що потрібні в інших модулях
from .core import start_learning, start_repetition, start_article_activity
