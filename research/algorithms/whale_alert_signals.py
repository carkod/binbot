import logging
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
        self.transaction_count_limit = 2
        self.exclude_list = ["GUSD","USDC", "USDT", "BUSD", "BTC", "ETH"]
    
    def get_last_transaction(self):
        start_time = int(time.time() - 600)
        success, transactions, status = self.whale_alert.get_transactions(start_time, api_key=self.api_key, limit=self.transaction_count_limit)
        if success:
            if (transactions[0]["amount_usd"] != transactions[1]["amount_usd"]) and transactions[1]["symbol"] not in self.exclude_list:
                return transactions[1]
            else:
                return None
        else:
            return status

    def run_bot(self) -> None:
        """Run the bot."""
        logging.info("Running Whale alert signals...")
        transaction = self.get_last_transaction()
        if transaction:
            from_owner = "#" + transaction["from"]["owner"] if transaction["from"]["owner"] == "unknown" else transaction["to"]["owner"]
            to_owner = "#" + transaction["to"]["owner"] if transaction["to"]["owner"] == "unknown" else transaction["to"]["owner"]

            msg = f'[{os.getenv("ENV")}] <strong>#Whale alert</strong>: {transaction["transaction_type"]} of #{transaction["symbol"]} ({transaction["amount_usd"]} USD) from {from_owner} wallet to {to_owner}\n- https://www.binance.com/en/trade/{transaction["symbol"]}_USDT \n- Dashboard trade http://terminal.binbot.in/admin/bots/new/{transaction["symbol"]}USDT'
            self.telegram_bot.send_msg(msg)
        
        pass
