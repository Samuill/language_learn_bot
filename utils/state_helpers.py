# -*- coding: utf-8 -*-

"""
Вспомогательные функции для работы с состоянием пользователя.
"""

from config import bot, user_state

def clear_state(chat_id, preserve_dict_type=False, preserve_messages=False, preserve_level=False):
    """Clear user state and delete message if exists
    
    Args:
        chat_id: User's chat ID
        preserve_dict_type: If True, preserve the dict_type setting for this user
        preserve_messages: If True, don't delete associated messages
        preserve_level: If True, preserve the level setting for this user
    """
    if chat_id in user_state:
        preserved_data = {}
        # Зберігаємо важливі дані перед очищенням
        if preserve_dict_type:
            for key in ["dict_type", "shared_dict_id"]:
                if key in user_state[chat_id]:
                    preserved_data[key] = user_state[chat_id][key]
        
        if preserve_level and "level" in user_state[chat_id]:
            preserved_data["level"] = user_state[chat_id]["level"]
            
        # Видаляємо активні повідомлення
        if not preserve_messages:
            # Видаляємо окремі повідомлення з message_id
            if "message_id" in user_state[chat_id]:
                try:
                    bot.delete_message(chat_id, user_state[chat_id]["message_id"])
                except Exception as e:
                    print(f"Error deleting message: {e}")
                    
            # Видаляємо всі активні повідомлення зі списку active_messages
            if "active_messages" in user_state[chat_id] and isinstance(user_state[chat_id]["active_messages"], list):
                for msg_id in user_state[chat_id]["active_messages"]:
                    try:
                        bot.delete_message(chat_id, msg_id)
                    except Exception as e:
                        print(f"Error deleting message from list: {e}")
        elif "message_id" in user_state[chat_id]:
            preserved_data["message_id"] = user_state[chat_id]["message_id"]
        
        # Видаляємо запис користувача з user_state
        del user_state[chat_id]
        
        # Відновлюємо збережені дані
        if preserved_data:
            user_state[chat_id] = preserved_data
            debug_info = ", ".join([f"{k}={v}" for k, v in preserved_data.items()])
            print(f"Debug: Preserved data for user {chat_id}: {debug_info}")

def save_message_id(chat_id, message_id):
    """Save message ID to user state"""
    from config import user_state
    
    # Ensure user_state exists for this chat_id
    if chat_id not in user_state:
        user_state[chat_id] = {}
    
    # Save current message ID
    if "messages" not in user_state[chat_id]:
        user_state[chat_id]["messages"] = []
    
    user_state[chat_id]["messages"].append(message_id)
    
    # Log state change for debugging
    try:
        from debug_logger import log_section_change
        current_state = user_state.get(chat_id, {}).get("state", "Unknown")
        log_section_change(chat_id, f"State update: {current_state}", f"Added message ID: {message_id}")
    except ImportError:
        pass  # If debug_logger is not available
    
    return True

def log_state_change(chat_id, old_state=None):
    """Log changes in user state"""
    from config import user_state
    
    try:
        from debug_logger import log_section_change
        current_state = user_state.get(chat_id, {})
        
        # Strip out some noisy fields for logging
        if "messages" in current_state:
            current_state = {k: v for k, v in current_state.items() if k != "messages"}
        
        # Log the state change
        log_section_change(
            chat_id, 
            f"State: {current_state.get('state', 'Unknown')}", 
            f"Full state: {current_state}"
        )
    except (ImportError, Exception) as e:
        print(f"Error logging state change: {e}")
