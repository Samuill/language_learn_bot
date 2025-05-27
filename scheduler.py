# -*- coding: utf-8 -*-
import os
import random
from config import bot, scheduler
from utils import get_user_params_path

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
    """Send reminders to all users"""
    for filename in os.listdir():
        if filename.startswith("params_") and filename.endswith(".json"):
            chat_id = filename.split('_')[1].split('.')[0]
            try:
                send_streak_info(chat_id)
            except Exception as e:
                print(f"Помилка для {chat_id}: {e}")

def setup_scheduler():
    """Setup reminder scheduler"""
    scheduler.add_job(send_reminder, 'cron', hour=random.randint(10,22), minute=random.randint(0,59))
    if not scheduler.running:
        scheduler.start()
