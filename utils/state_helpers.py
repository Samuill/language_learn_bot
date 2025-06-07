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
        # Зберігаємо важливі дані перед очищенням
        preserved_data = {}
        
        # Тип словника
        if preserve_dict_type and "dict_type" in user_state[chat_id]:
            preserved_data["dict_type"] = user_state[chat_id]["dict_type"]
        
        # Рівень складності
        if preserve_level and "level" in user_state[chat_id]:
            preserved_data["level"] = user_state[chat_id]["level"]
        
        # Shared dict ID, якщо є
        if preserve_dict_type and "shared_dict_id" in user_state[chat_id]:
            preserved_data["shared_dict_id"] = user_state[chat_id]["shared_dict_id"]
            
        # ID повідомлення, якщо потрібно зберегти
        message_id = None
        if preserve_messages and "message_id" in user_state[chat_id]:
            message_id = user_state[chat_id]["message_id"]
            preserved_data["message_id"] = message_id
            
        # Видаляємо повідомлення, якщо є і не потрібно зберігати
        if not preserve_messages and "message_id" in user_state[chat_id]:
            try:
                bot.delete_message(chat_id, user_state[chat_id]["message_id"])
            except Exception as e:
                print(f"Error deleting message: {e}")
        
        # Видаляємо запис користувача з user_state
        del user_state[chat_id]
        
        # Відновлюємо збережені дані
        if preserved_data:
            user_state[chat_id] = preserved_data
            debug_info = ", ".join([f"{k}={v}" for k, v in preserved_data.items()])
            print(f"Debug: Preserved data for user {chat_id}: {debug_info}")
