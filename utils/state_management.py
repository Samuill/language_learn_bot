# -*- coding: utf-8 -*-

"""
Utility functions for managing user state consistently.
"""

from config import user_state

def get_user_state_value(chat_id, key, default=None):
    """
    Get a value from user state with default fallback
    
    Args:
        chat_id (int): User's chat ID
        key (str): State key
        default: Default value if key doesn't exist
        
    Returns:
        Value or default
    """
    return user_state.get(chat_id, {}).get(key, default)

def set_user_state_value(chat_id, key, value):
    """
    Set a specific value in user state
    
    Args:
        chat_id (int): User's chat ID
        key (str): State key
        value: Value to set
    """
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    user_state[chat_id][key] = value
    return value

def update_user_state(chat_id, new_values, preserve_keys=None):
    """
    Update user state with new values while preserving specific keys
    
    Args:
        chat_id (int): User's chat ID
        new_values (dict): New state values to set
        preserve_keys (list): List of keys to preserve
    """
    if preserve_keys is None:
        preserve_keys = []
        
    # Store preserved values
    preserved = {}
    if chat_id in user_state:
        for key in preserve_keys:
            if key in user_state[chat_id]:
                preserved[key] = user_state[chat_id][key]
    
    # Update state
    if chat_id in user_state:
        user_state[chat_id].update(new_values)
    else:
        user_state[chat_id] = new_values
    
    # Restore preserved values
    for key, value in preserved.items():
        user_state[chat_id][key] = value
        
    return user_state[chat_id]
