# -*- coding: utf-8 -*-

"""
Utility functions for managing user state consistently.
"""

from config import user_state

def update_user_state(chat_id, new_state, preserve_keys=None):
    """
    Update user state with new values while preserving specified keys.
    
    Args:
        chat_id: User's chat ID
        new_state: Dictionary with new state values
        preserve_keys: List of keys to preserve from existing state
    """
    if preserve_keys is None:
        preserve_keys = []
    
    # Store values to preserve
    preserved_values = {}
    if chat_id in user_state:
        for key in preserve_keys:
            if key in user_state[chat_id]:
                preserved_values[key] = user_state[chat_id][key]
    
    # Update or create state
    if chat_id in user_state:
        user_state[chat_id].update(new_state)
    else:
        user_state[chat_id] = new_state.copy()
    
    # Restore preserved values
    for key, value in preserved_values.items():
        user_state[chat_id][key] = value
    
    return user_state[chat_id]

def get_user_state_value(chat_id, key, default=None):
    """Get a value from user state with fallback default"""
    return user_state.get(chat_id, {}).get(key, default)

def set_user_state_value(chat_id, key, value):
    """Set a specific value in user state"""
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    user_state[chat_id][key] = value
    return value

def ensure_dict_state(chat_id):
    """Ensure dictionary-related state is properly initialized"""
    # Get from database if needed
    import db_manager
    dict_type, shared_dict_id, _ = db_manager.get_user_dictionary_info(chat_id)
    
    # Update state
    if chat_id in user_state:
        user_state[chat_id]["dict_type"] = dict_type
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
        elif "shared_dict_id" in user_state[chat_id]:
            del user_state[chat_id]["shared_dict_id"]
    else:
        user_state[chat_id] = {
            "dict_type": dict_type
        }
        if shared_dict_id:
            user_state[chat_id]["shared_dict_id"] = shared_dict_id
    
    return dict_type, shared_dict_id
