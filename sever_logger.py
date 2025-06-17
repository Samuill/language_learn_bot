import telebot
import logging
from dotenv import load_dotenv
import os

# Завантаження токена з .env
load_dotenv()
TOKEN = os.getenv('TOKEN')

# Налаштування логування у файл
logging.basicConfig(
    filename='bot2.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

bot = telebot.TeleBot(TOKEN)

# Логування та print всіх вхідних повідомлень
@bot.message_handler(func=lambda message: True)
def log_all_messages(message):
    log_str = f"INCOMING | From: {message.from_user.id} | Text: {message.text}"
    logging.info(log_str)
    print(f"[SERVER RESPONSE] {message}")

# Якщо потрібно логувати вихідні повідомлення
def send_and_log(chat_id, text):
    log_str = f"OUTGOING | To: {chat_id} | Text: {text}"
    logging.info(log_str)
    print(f"[SERVER RESPONSE] To: {chat_id} | Text: {text}")
    bot.send_message(chat_id, text)

if __name__ == '__main__':
    print("[LOGGER STARTED]")
    bot.polling()
