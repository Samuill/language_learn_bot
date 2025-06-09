# -*- coding: utf-8 -*-

"""
DISABLED: Middleware for comprehensive logging of all bot interactions.
This module is now replaced with simpler logging to be compatible with the 
current telebot version.

For basic logging, use the log_message_decorator from debug_logger instead.
"""

import telebot
from config import bot, user_state
from debug_logger import log_message, log_error

# This middleware implementation is not supported in current telebot version
def setup_logging_middleware():
    """Set up middleware for logging all bot interactions"""
    print("WARNING: Middleware functionality is not supported in current telebot version.")
    print("Using standard logging instead.")
    return False
