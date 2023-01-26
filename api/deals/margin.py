import os
from time import time

from binance.client import Client


class MarginDeal:
    def __init__(self, deal_controller) -> None:
        # Inherit from parent class
        self.client = Client(os.environ["BINANCE_KEY"], os.environ["BINANCE_SECRET"])
        self.deal_controller = deal_controller

    def simulate_margin_order(self, pair, price, qty, side):
        order = {
            "symbol": pair,
            "orderId": self.deal_controller.generate_id(),
            "orderListId": -1,
            "clientOrderId": self.deal_controller.generate_id(),
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "marginBuyBorrowAmount": 5,
            "marginBuyBorrowAsset": "BTC",
            "fills": [],
        }
        return order

    def open_margin_deal(self):
        print("ACTIVATION MARGIN DEAL")
        pass
