# -*- coding: utf-8 -*-

"""
Helper functions for managing file paths in the application.
"""

import os

# Base directory for user data
USER_DATA_DIR = "user_data"
USER_PARAMS_DIR = "user_params"

def get_user_params_path(chat_id):
    """
    Get path to user parameters file
    
    Args:
        chat_id: User's chat ID
    
    Returns:
        Path to user parameters file
    """
    # Create user_params directory if it doesn't exist
    if not os.path.exists(USER_PARAMS_DIR):
        os.makedirs(USER_PARAMS_DIR)
    
    # Return path to user's parameters file
    return os.path.join(USER_PARAMS_DIR, f"user_{chat_id}.json")
