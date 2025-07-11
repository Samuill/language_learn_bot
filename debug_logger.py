# -*- coding: utf-8 -*-
import os
import time
import json
from datetime import datetime
import inspect
import telebot
from config import ADMIN_ID  # Додано імпорт ADMIN_ID

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Log file paths
DEBUG_LOG = os.path.join(LOGS_DIR, "debug.log")
ERROR_LOG = os.path.join(LOGS_DIR, "error.log")
COMMAND_LOG = os.path.join(LOGS_DIR, "commands.log")
USER_INPUT_LOG = os.path.join(LOGS_DIR, "user_inputs.log")
NAVIGATION_LOG = os.path.join(LOGS_DIR, "navigation.log")

def get_timestamp():
    """Return formatted timestamp for logging"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def log_message(message, response=None):
    """Log incoming message with user info and timestamp"""
    timestamp = get_timestamp()
    
    # Extract user information
    user_id = message.from_user.id if message.from_user else "Unknown"
    username = message.from_user.username if message.from_user and message.from_user.username else "No username"
    first_name = message.from_user.first_name if message.from_user and message.from_user.first_name else "No name"
    
    # Get message content
    content = message.text if hasattr(message, 'text') and message.text else "No text"
    
    # Determine if it's a command
    is_command = content.startswith('/') if isinstance(content, str) else False
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "message": content,
        "is_command": is_command,
        "chat_id": message.chat.id if hasattr(message, 'chat') else None
    }
    
    # Convert to string for logging
    log_str = f"[{timestamp}] User {user_id} ({username}/{first_name}) sent: '{content}'"
    
    # Special handling for commands
    if is_command:
        with open(COMMAND_LOG, 'a', encoding='utf-8') as f:
            f.write(f"{log_str}\n")
    
    # Always log all user input messages (commands and regular messages)
    with open(USER_INPUT_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"📩 INPUT: {log_str}")
    
    return log_entry

def log_response(user_id, response_text, original_entry=None):
    """Log bot's response with timestamp"""
    timestamp = get_timestamp()
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "response_to_user": user_id,
        "response_text": response_text
    }
    
    # Add original message info if available
    if original_entry:
        log_entry["original_message"] = original_entry
    
    # Convert to string for logging
    log_str = f"[{timestamp}] Response to User {user_id}: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'"
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"📤 OUTPUT: {log_str}")
    
    return log_entry

def log_navigation(chat_id, from_section, to_section, via_button=None):
    """Log user navigation between sections"""
    timestamp = get_timestamp()
    
    # Create log entry
    log_str = f"[{timestamp}] NAVIGATION: User {chat_id} moved from '{from_section}' to '{to_section}'"
    if via_button:
        log_str += f" via button '{via_button}'"
    
    # Write to navigation log
    with open(NAVIGATION_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"🧭 {log_str}")

def log_callback(call):
    """Log callback query (button click) with user info and timestamp"""
    timestamp = get_timestamp()
    
    # Extract user information
    user_id = call.from_user.id if call.from_user else "Unknown"
    username = call.from_user.username if call.from_user and call.from_user.username else "No username"
    first_name = call.from_user.first_name if call.from_user and call.from_user.first_name else "No name"
    
    # Get callback data
    callback_data = call.data if hasattr(call, 'data') else "No data"
    
    # Create log entry
    log_str = f"[{timestamp}] User {user_id} ({username}/{first_name}) clicked button: '{callback_data}'"
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Write to navigation log
    with open(NAVIGATION_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"🔘 BUTTON: {log_str}")

def log_error(error, context=None):
    """Log errors with timestamp and context"""
    timestamp = get_timestamp()
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "error": str(error),
        "context": context
    }
    
    # Convert to string for logging
    log_str = f"[{timestamp}] ERROR: {str(error)}"
    if context:
        log_str += f" | Context: {context}"
    
    # Write to error log
    with open(ERROR_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Write to debug log as well
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"❌ {log_str}")
    
    return log_entry

def log_dict_operation(chat_id, operation, dict_type, path, success=True):
    """Log dictionary operations with more detail"""
    timestamp = get_timestamp()
    
    is_admin = chat_id == ADMIN_ID
    admin_text = " (ADMIN)" if is_admin else ""
    
    # Create log entry
    log_str = f"[{timestamp}] Dictionary {operation}: User {chat_id}{admin_text} {operation} {dict_type} dictionary at {path}"
    if not success:
        log_str += " (FAILED)"
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"📚 {log_str}")

def log_section_change(chat_id, section_name, additional_info=None):
    """Log when a user enters a specific section of the bot"""
    timestamp = get_timestamp()
    
    # Create log entry
    log_str = f"[{timestamp}] SECTION: User {chat_id} entered section '{section_name}'"
    if additional_info:
        log_str += f" | {additional_info}"
    
    # Write to navigation log
    with open(NAVIGATION_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(f"📋 {log_str}")

# Create a decorator for message handlers that adds logging
def log_handler(func):
    """Decorator to log incoming messages and outgoing responses for handlers"""
    def wrapper(message, *args, **kwargs):
        # Log incoming message
        entry = log_message(message)
        
        # Call original handler
        func(message, *args, **kwargs)
        
        # Note: We can't easily capture the response here since the response
        # is sent directly by the bot inside the handler function
        
    return wrapper

# Add this function for scheduler logging
def log_action(action_name, data=None, user_info=None):
    """Log an action with optional data and user info"""
    timestamp = get_timestamp()
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "action": action_name
    }
    
    if data:
        log_entry.update(data)
    
    if user_info:
        log_entry["user"] = user_info
    
    # Convert to string for logging
    log_str = f"[{timestamp}] [INFO] Action '{action_name}' | {json.dumps(log_entry)}"
    
    # Write to debug log
    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{log_str}\n")
    
    # Print to console for immediate feedback
    print(log_str)
    
    return log_entry

def extract_user_info(message):
    """Extract user info from a message for logging"""
    if not message or not message.from_user:
        return None
        
    return {
        "id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name
    }

# Decorator for logging message handlers - simpler alternative to middleware
def log_message_decorator(func):
    """Decorator to log message handling"""
    def wrapper(message, *args, **kwargs):
        # Log the message
        log_message(message)
        
        # Call the original function
        result = func(message, *args, **kwargs)
        
        # Return the result
        return result
    return wrapper
