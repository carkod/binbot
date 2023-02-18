import uuid
from decimal import Decimal
from time import time

from account.account import Account
from bots.schemas import BotSchema
from db import setup_db

class DealCreationError(Exception):
    pass

class BaseDeal(Account):
    """
    Base Deal class to share with CreateDealController and MarginDeal
    """

    def __init__(self, bot, db_collection):
        self.active_bot = BotSchema.parse_obj(bot)
        self.db = setup_db()
        self.db_collection = self.db[db_collection]
        self.decimal_precision = self.get_quote_asset_precision(self.active_bot.pair)
        # PRICE_FILTER decimals
        self.price_precision = -1 * (
            Decimal(str(self.price_filter_by_symbol(self.active_bot.pair, "tickSize")))
            .as_tuple()
            .exponent
        )
        self.qty_precision = -1 * (
            Decimal(str(self.lot_size_by_symbol(self.active_bot.pair, "stepSize")))
            .as_tuple()
            .exponent
        )

    def __repr__(self) -> str:
        """
        To check that BaseDeal works for all children classes
        """
        return f"BaseDeal({self.__dict__})"

    def generate_id(self):
        return uuid.uuid4().hex

    def simulate_order(self, pair, price, qty, side):
        order = {
            "symbol": pair,
            "orderId": self.generate_id(),
            "orderListId": -1,
            "clientOrderId": self.generate_id(),
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return order

    def simulate_response_order(self, pair, price, qty, side):
        response_order = {
            "symbol": pair,
            "orderId": id,
            "orderListId": -1,
            "clientOrderId": id,
            "transactTime": time() * 1000,
            "price": price,
            "origQty": qty,
            "executedQty": qty,
            "cummulativeQuoteQty": qty,
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": side,
            "fills": [],
        }
        return response_order

    def update_deal_logs(self, msg):
        self.db_collection.update_one(
            {"id": self.active_bot.id},
            {"$push": {"errors": msg}},
        )
        return msg

    def replace_order(self):
        params = [
                ("symbol", self.active_bot.pair),
                ("type", "MARKET"),
                ("side", "SELL"),
                ("cancelReplaceMode", "ALLOW_FAILURE")
            ]
        response = self.signed_request(url=self.cancel_replace_url, method="POST", params=params)
        if "code" in response:
            raise DealCreationError(response["msg"], response["data"])
    
        return response["newOrderResponse"]
