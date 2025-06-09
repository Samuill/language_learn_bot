# -*- coding: utf-8 -*-

"""
Сумісність з попередньою структурою проекту.
Цей модуль реекспортує функції з easy_level.py для зворотної сумісності.
"""

# Re-export functions from their new locations for backward compatibility
from .easy_level import start_learning, start_repetition, learn_articles as start_article_activity
