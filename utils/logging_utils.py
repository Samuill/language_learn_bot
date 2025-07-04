# -*- coding: utf-8 -*-

"""
Utilities for logging and debugging.
"""

import os
import time
import datetime
import traceback
import json  # Add import for JSON serialization

# Directory for log files
LOG_DIR = "logs"

# Ensure log directory exists
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Log file paths
DEBUG_LOG = os.path.join(LOG_DIR, "debug.log")
LANGUAGE_LOG = os.path.join(LOG_DIR, "language_selection.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")

def log_debug(message):
    """Log a debug message"""
    _write_log(DEBUG_LOG, f"[DEBUG] {message}")

def log_language(action, chat_id, details):
    """Log language-related actions"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] [LANG] [User {chat_id}] {action}: {details}"
    
    # Print to console with highlighting for better visibility
    print(f"\033[1;33m{message}\033[0m")  # Yellow color and bold
    
    # Write to log file
    _write_log(LANGUAGE_LOG, message)

def log_error(error, context=""):
    """Log an error with traceback"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] [ERROR] {context}: {str(error)}"
    traceback_msg = traceback.format_exc()
    
    # Print to console with highlighting for errors
    print(f"\033[1;31m{message}\033[0m")  # Red color
    print(f"\033[0;31m{traceback_msg}\033[0m")  # Lighter red for traceback
    
    # Write to log file
    _write_log(ERROR_LOG, f"{message}\n{traceback_msg}")

def log_language_event(chat_id, event_type, details):
    """
    Log a language selection event
    
    Args:
        chat_id: User's chat ID
        event_type: Type of event (e.g., BUTTON_PRESSED, LANGUAGE_IDENTIFIED)
        details: Additional details about the event
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[{timestamp}] [User {chat_id}] [{event_type}] {details}"
    
    # Print to console with highlighting for better visibility
    print(f"\033[1;36m{message}\033[0m")  # Cyan color and bold
    
    # Write to log file
    try:
        with open(LANGUAGE_LOG, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except Exception as e:
        print(f"\033[1;31mERROR writing to language log: {e}\033[0m")  # Red color for errors

def log_action(action, data=None):
    """Log a generic action with optional data payload"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"action": action, "data": data}
    message = f"[{timestamp}] [ACTION] {action}: {json.dumps(data, ensure_ascii=False)}"

    # Print to console for visibility
    print(f"\033[1;35m{message}\033[0m")  # Magenta color and bold

    # Write to debug log
    _write_log(DEBUG_LOG, message)

def _write_log(log_file, message):
    """Write a message to a log file"""
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except Exception as e:
        print(f"\033[1;31mError writing to log file {log_file}: {e}\033[0m")
