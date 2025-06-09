# -*- coding: utf-8 -*-

"""
Функції для відстеження активності користувачів.
"""

import datetime
import db_manager

def track_activity(chat_id):
    """
    Track user activity by updating last_activity timestamp and incrementing active_days
    if the user wasn't active today.
    
    Args:
        chat_id: The user's chat ID
    """
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # First check if the column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "last_activity" not in columns:
            # Add the missing column
            cursor.execute("ALTER TABLE users ADD COLUMN last_activity TEXT")
            print("Added missing column 'last_activity' to users table")
        
        # Get current datetime
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Check if user exists and when they were last active
        cursor.execute("""
            SELECT last_activity, active_days 
            FROM users 
            WHERE chat_id = ?
        """, (chat_id,))
        
        result = cursor.fetchone()
        
        if result:
            last_activity, active_days = result
            
            # If last_activity is None, treat as new user
            if last_activity is None:
                cursor.execute("""
                    UPDATE users 
                    SET last_activity = ?, active_days = 1, last_active_date = ?
                    WHERE chat_id = ?
                """, (now, today, chat_id))
                
            else:
                # Convert string to datetime object for comparison
                last_active_date = None
                
                # Try to get the date part of the last_activity
                try:
                    if last_activity:
                        last_active_date = datetime.datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                except Exception as e:
                    print(f"Error parsing last_activity date: {e}")
                
                # Update last_activity timestamp
                cursor.execute("""
                    UPDATE users 
                    SET last_activity = ?
                    WHERE chat_id = ?
                """, (now, chat_id))
                
                # If user wasn't active today, increment active_days and update last_active_date
                if last_active_date != today:
                    # If active_days is None, start with 1
                    if active_days is None:
                        active_days = 0
                    
                    cursor.execute("""
                        UPDATE users 
                        SET active_days = ?, last_active_date = ?
                        WHERE chat_id = ?
                    """, (active_days + 1, today, chat_id))
        else:
            # User doesn't exist, they will be created elsewhere, but log the issue
            print(f"Warning: Tried to track activity for non-existent user {chat_id}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error tracking activity: {e}")
        import traceback
        traceback.print_exc()
