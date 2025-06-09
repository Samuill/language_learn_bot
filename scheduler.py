# -*- coding: utf-8 -*-

"""
Планувальник для відправки нагадувань про вивчення слів.
"""

import datetime
from config import scheduler, bot
import db_manager
import logging
from utils import language_utils
from utils.path_helpers import get_user_params_path
def send_streak_info(chat_id):
    """Send streak info to user"""
    import json
    from handlers import repeat_words
    
    params_path = get_user_params_path(chat_id)
    try:
        with open(params_path, 'r') as f:
            params = json.load(f)
        streak = params.get('streak', 0)
        
        # Send reminder message
        bot.send_message(chat_id, "Не забудьте сьогодні потренуватись!")
        
        # Send streak sticker if available
        try:
            with open(f'fires/{streak}.webp', 'rb') as sticker_file:
                bot.send_sticker(chat_id, sticker_file)
        except FileNotFoundError:
            print(f"Стікер для streak {streak} не знайдено")

        # Create fake message for repeat_words call
        class FakeMessage:
            def __init__(self, chat_id):
                self.chat = FakeChat(chat_id)
        
        class FakeChat:
            def __init__(self, chat_id):
                self.id = chat_id
        
        fake_msg = FakeMessage(chat_id)
        
        try:
            repeat_words(fake_msg)
        except Exception as e:
            print(f"Помилка при відправці завдання: {e}")
        
    except FileNotFoundError:
        from utils import update_streak
        update_streak(chat_id)
        send_streak_info(chat_id)

def send_reminder():
    """Send reminders to users who haven't been active for more than 24 hours"""
    print("Running scheduled reminder task...")
    
    try:
        # Get users who were last active more than 24 hours ago
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get current time minus 24 hours to find inactive users
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Select users who were active more than 24 hours ago or have never been active
        cursor.execute("""
            SELECT chat_id, language, active_days 
            FROM users 
            WHERE last_activity < ? OR last_activity IS NULL
        """, (yesterday,))
        
        inactive_users = cursor.fetchall()
        
        # Count of messages sent
        sent_count = 0
        
        for user_id, language, active_days in inactive_users:
            try:
                # Active days might be NULL in the database
                if active_days is None:
                    active_days = 0
                
                # Construct message based on activity streak
                if active_days == 0:
                    message_key = "reminder_new"
                elif active_days < 3:
                    message_key = "reminder_short_streak"
                elif active_days < 7:
                    message_key = "reminder_medium_streak" 
                else:
                    message_key = "reminder_long_streak"
                
                # Get localized message
                message = language_utils.get_text(message_key, user_id, f"Time to practice German! You've been active for {active_days} days.")
                
                # Send reminder
                bot.send_message(user_id, message)
                sent_count += 1
                
                print(f"Sent reminder to user {user_id} with {active_days} active days")
                
            except Exception as e:
                print(f"Failed to send reminder to user {user_id}: {e}")
        
        print(f"Reminder task completed: sent {sent_count} reminders")
        conn.close()
        
    except Exception as e:
        print(f"Error in send_reminder: {e}")
        import traceback
        traceback.print_exc()

def schedule_reminders():
    """Schedule the daily reminder job"""
    # Set reminder time to 18:00
    reminder_time = datetime.time(hour=18, minute=0)
    
    # Schedule the job
    job = scheduler.add_job(
        send_reminder, 
        'cron', 
        hour=reminder_time.hour, 
        minute=reminder_time.minute,
        id='daily_reminder'
    )
    
    print(f"Daily reminder scheduled for {reminder_time.strftime('%H:%M')} (job id: {job.id})")
    logging.info(f"Scheduled daily reminder for {reminder_time.strftime('%H:%M')}")
    
    # Return time and job ID
    return (reminder_time.strftime("%H:%M"), job.id)

# When imported directly
if __name__ == "__main__":
    send_reminder()
