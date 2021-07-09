import os

import telegram


class TelegramBot:

    token = os.getenv("TELEGRAM_BOT_KEY")
    chat_id = os.getenv("TELEGRAM_USER_ID")

    def __init__(self):
        pass

    def send_msg(self, msg):
        """
        Send a mensage to a telegram user specified on chatId
        chat_id must be a number!
        """
        bot = telegram.Bot(token=self.token)
        bot.sendMessage(chat_id=self.chat_id, text=msg)
