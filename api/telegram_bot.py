import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, Updater, MessageHandler, Filters

class TelegramBot:

    token = os.getenv("TELEGRAM_BOT_KEY")
    chat_id = os.getenv("TELEGRAM_USER_ID")

    def __init__(self):
        pass

    def buy(self, update: Update, context: CallbackContext) -> None:
        """Sends a message with three inline buttons attached."""
        keyboard = [
            [
                InlineKeyboardButton("Buy", callback_data="1"),
                InlineKeyboardButton("Cancel", callback_data="2"),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            symbol = context.args[0]
            message = f"Proceed to start {symbol} bot @ 3% take profit?"
            update.message.reply_text(message, reply_markup=reply_markup)
        except KeyError:
            message = "Error: incorrect command argument, please enter a crypto market e.g. BNBBTC"
            update.message.reply_text(message)

    def button(self, update, context):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        query.answer()
        if query.data == "1":
            query.edit_message_text(text="Opening bot...")
        else:
            query.edit_message_text(text="Cancelled request")

    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Displays info on how to use the bot."""
        update.message.reply_text("Use /start to test this bot.")

    def send_msg(self, msg):
        self.updater.bot.send_message(chat_id=self.chat_id, text=msg)

    def stop(self):
        self.updater.stop()

    def run_bot(self) -> None:
        """Run the bot."""
        self.updater = Updater(self.token)
        self.updater.dispatcher.add_handler(CommandHandler("t", self.buy))
        self.updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: u.message.reply_text(u.message.text)))
        self.updater.dispatcher.add_handler(CallbackQueryHandler(self.button))
        self.updater.start_polling()
        # self.updater.idle()
        return