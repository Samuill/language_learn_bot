# -*- coding: utf-8 -*-

"""
Functions to track user activity and manage streaks.
"""

import sqlite3
import datetime

def track_activity(chat_id):
    """
    Track user activity in the database. Updates:
    1. Streak count (consecutive days)
    2. Last active timestamp
    """
    try:
        from utils.logger import log_activity
        import db_manager
        
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # First, check if active_days column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # If active_days column doesn't exist, add it
        if 'active_days' not in columns:
            print("Adding active_days column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN active_days INTEGER DEFAULT 0")
            conn.commit()
        
        # Now safely proceed with the update
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Update last_active timestamp
        cursor.execute("""
            UPDATE users 
            SET last_active = ?
            WHERE chat_id = ?
        """, (today, chat_id))
        
        # Update streak count
        # This needs schema verification first in case other columns are missing
        try:
            cursor.execute("""
                UPDATE users 
                SET streak = CASE 
                    WHEN date(last_active, '-1 day') >= date('now', '-1 day') THEN streak + 1
                    ELSE 1
                END,
                active_days = COALESCE(active_days, 0) + 1
                WHERE chat_id = ?
            """, (chat_id,))
        except sqlite3.OperationalError as e:
            print(f"Error updating streak: {e}")
            # Fallback to just update streak without active_days
            cursor.execute("""
                UPDATE users 
                SET streak = CASE 
                    WHEN date(last_active, '-1 day') >= date('now', '-1 day') THEN streak + 1
                    ELSE 1
                END
                WHERE chat_id = ?
            """, (chat_id,))
        
        conn.commit()
        conn.close()
        
        # Log user activity
        log_activity(f"User {chat_id} activity tracked")
        return True
        
    except Exception as e:
        print(f"Error tracking activity: {e}")
        import traceback
        traceback.print_exc()
        return False
