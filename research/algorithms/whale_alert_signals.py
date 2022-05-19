import os
import time

from telegram_bot import TelegramBot  # For formatted dictionary printing
from whalealert.whalealert import WhaleAlert


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
    
    def get_last_transaction(self):
        success, transactions, status = self.whale_alert.get_transactions(self.start_time, api_key=self.api_key, limit=self.transaction_count_limit)
        if success:
            return transactions[0]
        else:
            return status

    def run_bot(self) -> None:
        """Run the bot."""
        transaction = self.get_last_transaction()
        msg = f'[{os.getenv("ENV")}] <strong>Whale alert</strong>: {transaction["transaction_type"]} of #{transaction["symbol"]} ({transaction["amount_usd"]} USD) from {transaction["from"]["owner"]} ({transaction["from"]["owner_type"]}) to {transaction["to"]["owner"]} ({transaction["to"]["owner_type"]})\n- https://www.binance.com/en/trade/{transaction["symbol"]}USDT \n- Dashboard trade http://binbot.in/admin/bots/new{transaction["symbol"]}USDT'
        self.telegram_bot.send_msg(msg)
        pass
