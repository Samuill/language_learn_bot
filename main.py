# -*- coding: utf-8 -*-
import time
import requests
import signal
import sys
from config import bot, scheduler
from scheduler import setup_scheduler
import handlers  # Import handlers to register them

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nЗупиняємо бота...')
    bot.stop_polling()
    scheduler.shutdown(wait=False)
    sys.exit(0)

def main():
    """Main function to run the bot"""
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    setup_scheduler()
    
    while True:
        try:
            print("Bot started...")
            bot.polling(none_stop=True, interval=1)
        except requests.exceptions.ConnectionError:
            print("Помилка з'єднання. Повторна спроба через 5 секунд...")
            time.sleep(5)
        except Exception as e:
            print(f"Критична помилка: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
