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

def ensure_dict_state(chat_id):
    """
    Ensure dictionary-related state is properly initialized
    
    Args:
        chat_id: User's chat ID
        
    Returns:
        tuple: (dict_type, shared_dict_id)
    """
    # Get the current dictionary type from database or state
    dict_type = user_state.get(chat_id, {}).get("dict_type", "personal")
    shared_dict_id = user_state.get(chat_id, {}).get("shared_dict_id")
    
    # Double-check with database
    try:
        import db_manager
        db_info = db_manager.get_user_dictionary_info(chat_id)
        if db_info:
            db_dict_type, db_shared_id, _ = db_info
            dict_type = db_dict_type
            shared_dict_id = db_shared_id
            
            # Validate that the shared dictionary actually exists if dict_type is "shared"
            if dict_type == "shared" and shared_dict_id:
                # Check if the shared dictionary exists
                if not db_manager.shared_dictionary_exists(shared_dict_id):
                    print(f"WARNING: Shared dictionary {shared_dict_id} does not exist for user {chat_id}, resetting to personal")
                    dict_type = "personal"
                    shared_dict_id = None
                    # Update the database to reset user's dictionary to personal
                    db_manager.reset_user_dictionary(chat_id)
    except Exception as e:
        print(f"Error getting dictionary info from database: {e}")
    
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
