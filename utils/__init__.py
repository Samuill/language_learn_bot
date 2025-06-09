# -*- coding: utf-8 -*-

"""
Модуль з утилітами для бота.
"""

from .state_helpers import clear_state, save_message_id
from .activity_tracking import track_activity
from .path_helpers import *
from .keyboards import (
    main_menu_keyboard,
    main_menu_cancel,
    easy_level_keyboard,
    medium_level_keyboard,
    hard_level_keyboard,
    shared_dictionary_keyboard,
    yes_no_cancel_keyboard
)

# Backward compatibility
def get_user_params_path(chat_id):
    from .path_helpers import get_user_params_path as gup
    return gup(chat_id)
