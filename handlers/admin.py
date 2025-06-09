# -*- coding: utf-8 -*-

"""
Адміністративні обробники для бота.
"""

from config import bot, ADMIN_ID, scheduler

@bot.message_handler(commands=['fire'])
def test_fire(message):
    """Test the reminder functionality by manually triggering it"""
    if message.from_user.id == ADMIN_ID:
        try:
            from scheduler import send_reminder
            send_reminder()
            bot.reply_to(message, "Нагадування відправлено всім неактивним користувачам!")
        except Exception as e:
            print(f"Помилка в /fire: {e}")
            bot.reply_to(message, f"Помилка: {str(e)}")
    else:
        # Silently ignore if not admin
        pass

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    if message.from_user.id == ADMIN_ID:
        bot.stop_polling()
        scheduler.shutdown(wait=False)
        print("Бот зупинено!")
        exit(0)
