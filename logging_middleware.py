# -*- coding: utf-8 -*-

"""
Middleware for comprehensive logging of all bot interactions.
This module intercepts all incoming messages and callback queries
to log user actions in the console and log files.
"""

import telebot
from config import bot, user_state
from debug_logger import log_message, log_callback, log_navigation, log_section_change

# Keep track of last section for each user
user_last_section = {}

def setup_logging_middleware():
    """Set up middleware for logging all bot interactions"""
    try:
        bot.add_middleware_handler(message_logging_middleware, update_types=['message'])
        bot.add_middleware_handler(callback_logging_middleware, update_types=['callback_query'])
        print("✅ Logging middleware initialized")
    except RuntimeError as e:
        print(f"⚠️ Middleware error: {e}")
        print("Make sure telebot.apihelper.ENABLE_MIDDLEWARE is set to True before creating the bot")

def message_logging_middleware(bot_instance, message):
    """Log all incoming messages before they reach handlers"""
    # Log the message
    log_message(message)
    
    # Track menu location
    if hasattr(message, 'text') and message.text:
        chat_id = message.chat.id
        text = message.text
        
        # Dictionary of recognized sections/menus
        menu_sections = {
            "🟢 Легкий рівень": "Easy Level Menu",
            "🟠 Середній рівень": "Medium Level Menu",
            "🔴 Складний рівень": "Hard Level Menu",
            "👥 Спільний словник": "Shared Dictionary Menu",
            "👤 Персональний словник": "Personal Dictionary",
            "↩️ Повернутися до головного меню": "Main Menu"
        }
        
        # Check if the message text matches any known section
        if text in menu_sections:
            menu_name = menu_sections[text]
            previous_section = user_last_section.get(chat_id, "Unknown")
            
            # Log navigation
            log_navigation(chat_id, previous_section, menu_name, text)
            
            # Update last section
            user_last_section[chat_id] = menu_name
            
            # Log section change
            log_section_change(chat_id, menu_name)
    
    # Allow the message to proceed to handlers
    return message

def callback_logging_middleware(bot_instance, call):
    """Log all callback queries (button clicks) before they reach handlers"""
    # Log the callback
    log_callback(call)
    
    # Track section changes based on callback data
    if hasattr(call, 'data') and call.data:
        chat_id = call.message.chat.id
        
        # Log the button click with its data
        print(f"Button clicked: {call.data} by user {chat_id}")
    
    # Allow the callback to proceed to handlers
    return call
