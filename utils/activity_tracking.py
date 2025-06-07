# -*- coding: utf-8 -*-

"""
Functions for tracking user activity.
"""

import datetime
import db_manager
from config import DEBUG_MODE

def track_activity(chat_id, activity_type="general"):
    """
    Track user activity to update streak and log usage data
    
    Args:
        chat_id: User's chat ID
        activity_type: Type of activity (optional)
    """
    try:
        # Update user streak in database
        streak = db_manager.update_user_streak(chat_id)
        
        # If debugging is enabled, log more detailed information
        if DEBUG_MODE:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"User activity: {chat_id} - {activity_type} at {current_time}")
            from debug_logger import log_activity
            log_activity(chat_id, activity_type)
            
        return streak
    except Exception as e:
        print(f"Error tracking activity: {e}")
        return 0
