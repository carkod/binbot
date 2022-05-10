import time
from pprint import pprint
from telegram_bot import TelegramBot  # For formatted dictionary printing
from whalealert.whalealert import WhaleAlert
import os

class WhaleAlertSignals:
    """
    Receive Whale alerts from telegram channel
    """
    def __init__(self):
        self.api_key = os.getenv("WHALER_KEY")
        self.whale_alert = WhaleAlert()
        self.telegram_bot = TelegramBot()
        self.start_time = int(time.time() - 600)
        self.transaction_count_limit = 1
    
    def get_last_transaction(self, index):
        success, transactions, status = self.whale_alert.get_transactions(self.start_time, api_key=self.api_key, limit=self.transaction_count_limit)
        if success:
            return transactions[index - 1]
        else:
            return status

    def run_bot(self, index=1) -> None:
        """Run the bot."""
        transaction = self.get_last_transaction(index)
        if transaction["symbol"] not in ["USDT", "BTC"]:

            msg = f'[{os.getenv("ENV")}]Whale alert: {transaction["transaction_type"]} of {transaction["symbol"]} ({transaction["amount_usd"]} USD) from {transaction["from"]["owner"]} ({transaction["from"]["owner_type"]}) to {transaction["to"]["owner"]} ({transaction["to"]["owner_type"]})'
            self.telegram_bot.send_msg(msg)
        else:
            index += 1
            self.run_bot(index)
        return
