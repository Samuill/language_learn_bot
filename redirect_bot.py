import telebot

def start_redirect_bot():
    TOKEN = "7616425414:AAFaZCuYss9UyNSXm_MJCd42rLjAKNWy0Mc"
    redirect_bot = telebot.TeleBot(TOKEN)

    # Повідомлення-заглушка
    MESSAGE = (
        "👋 Привіт! Я переїхав до нового бота. "
        "Будь ласка, пиши мені тут 👉 @language_learn_helper_bot\n\n"
        "👋 Hello! I've moved to a new bot. "
        "Please contact me here 👉 @language_learn_helper_bot"
    )

    # Реакція на будь-яке повідомлення
    @redirect_bot.message_handler(func=lambda message: True)
    def send_stub_message(message):
        redirect_bot.send_message(message.chat.id, MESSAGE)

    print("Starting redirect bot...")
    redirect_bot.polling(non_stop=True)

if __name__ == "__main__":
    start_redirect_bot()