from datetime import datetime
import threading
from time import time
from api.account.account import Account
from api.bots.controllers import Bot
from api.bots.schemas import BotSchema
from api.deals.models import DealModel
from api.deals.schema import DealSchema
from api.orders.models.book_order import Book_Order
from api.paper_trading.deal import TestDeal
from api.paper_trading.schemas import PaperTradingBotSchema
from api.threads import market_update_thread
from api.tools.exceptions import BaseDealError
from api.tools.handle_error import (
    QuantityTooLow,
    handle_binance_errors,
    jsonResp,
    jsonResp_error_message,
    jsonResp_message,
)
from api.tools.round_numbers import supress_notation
from bson.objectid import ObjectId
from flask import Response, current_app, request
from requests import delete
from api.paper_trading.schemas import PaperTradingBotSchema
from api.tools.enum_definitions import EnumDefinitions
from marshmallow import EXCLUDE
from marshmallow.exceptions import ValidationError

class PaperTradingController(Bot):
    def __init__(self):
        self.app = current_app
        self.default_deal = DealSchema()

    def _restart_websockets(self):
        """
        Restart websockets threads after list of active bots altered
        """
        print("Restarting market_updates")
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            if thread.name == "market_updates_thread" and hasattr(thread, "_target"):
                thread._target.__self__.markets_streams.close()
                market_update_thread()
        print("Finished restarting market_updates")
        return

    def activate(self):
        findId = request.view_args.get("botId")
        bot = self.app.db.paper_trading.find_one({"_id": ObjectId(findId)})

        if bot:
            try:
                TestDeal(bot).open_deal()
            except BaseDealError as error:
                return jsonResp_error_message(error)

            botId = self.app.db.paper_trading.update_one(
                {"_id": ObjectId(findId)}, {"$set": {"status": "active"}}
            )

            if botId:
                resp = jsonResp(
                    {
                        "message": "Successfully activated bot and triggered deals with no errors",
                        "botId": str(findId),
                    },
                    200,
                )
                self._restart_websockets()
            else:
                resp = jsonResp(
                    {
                        "message": "Unable to save bot",
                        "botId": str(findId),
                    },
                    200,
                )
            return resp
        else:
            resp = jsonResp({"message": "Bot not found", "botId": findId}, 400)
        return resp

    def deactivate(self):
        """
        Close all deals, sell pair and deactivate
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        findId = request.view_args["id"]
        bot = self.app.db.paper_trading.find_one({"_id": ObjectId(findId)})
        resp = jsonResp_error_message(
            "Not enough balance to close and sell. Please directly delete the bot."
        )
        if bot:
            orders = bot["orders"]

            # Close all active orders
            if len(orders) > 0:
                for d in orders:
                    if "deal_type" in d and (
                        d["status"] == "NEW" or d["status"] == "PARTIALLY_FILLED"
                    ):
                        order_id = d["order_id"]
                        res = delete(
                            url=f'{self.bb_close_order_url}/{bot["pair"]}/{order_id}'
                        )
                        error_msg = f"Failed to delete opened order {order_id}."
                        # Handle error and continue
                        handle_binance_errors(res, message=error_msg)

            # Sell everything
            pair = bot["pair"]
            base_asset = self.find_baseAsset(pair)
            deal_object = TestDeal(bot)
            precision = deal_object.price_precision
            qty_precision = deal_object.qty_precision
            balance = deal_object.get_one_balance(base_asset)
            if balance:
                qty = float(balance)
                book_order = Book_Order(pair)
                price = float(book_order.matching_engine(False, qty))

                if price:
                    order = {
                        "pair": pair,
                        "qty": supress_notation(qty, qty_precision),
                        "price": supress_notation(price, precision),
                    }
                    try:
                        order_res = self.request(
                            method="POST", url=self.bb_sell_order_url, json=order
                        )
                    except QuantityTooLow:
                        bot["status"] = "closed"
                        try:
                            bot = PaperTradingBotSchema().update_test_bots(bot)
                        except Exception as e:
                            resp = jsonResp_error_message(e)
                    return resp
                else:
                    order = {
                        "pair": pair,
                        "qty": supress_notation(price, qty_precision),
                    }
                    try:
                        order_res = self.request(
                            method="POST", url=self.bb_sell_market_order_url, json=order
                        )
                    except QuantityTooLow:
                        bot["status"] = "closed"
                        try:
                            bot = PaperTradingBotSchema().update_test_bots(bot)
                        except Exception as e:
                            resp = jsonResp_error_message(e)
                        return resp

                # Enforce that deactivation occurs
                # If it doesn't, redo
                if "status" not in order_res and order_res["status"] == "NEW":
                    deactivation_order = {
                        "order_id": order_res["orderId"],
                        "deal_type": "deactivate_order",
                        "pair": order_res["symbol"],
                        "order_side": order_res["side"],
                        "order_type": order_res["type"],
                        "price": order_res["price"],
                        "qty": order_res["origQty"],
                        "fills": order_res["fills"],
                        "time_in_force": order_res["timeInForce"],
                        "status": order_res["status"],
                    }
                    self.app.db.paper_trading.update_one(
                        {"_id": ObjectId(findId)},
                        {
                            "$push": {
                                "orders": deactivation_order,
                                "errors": "Order failed to close. Re-deactivating...",
                            },
                        },
                    )
                    self.deactivate()

                deactivation_order = {
                    "order_id": order_res["orderId"],
                    "deal_type": "deactivate_order",
                    "pair": order_res["symbol"],
                    "order_side": order_res["side"],
                    "order_type": order_res["type"],
                    "price": order_res["price"],
                    "qty": order_res["origQty"],
                    "fills": order_res["fills"],
                    "time_in_force": order_res["timeInForce"],
                    "status": order_res["status"],
                }
                self.app.db.paper_trading.update_one(
                    {"_id": ObjectId(findId)},
                    {
                        "$set": {
                            "status": "completed",
                            "deal.sell_timestamp": time(),
                            "deal.sell_price": order_res["price"],
                        },
                        "$push": {
                            "orders": deactivation_order,
                            "errors": "Orders updated. Trying to close bot...",
                        },
                    },
                )

                self._restart_websockets()
                return jsonResp_message(
                    "Active orders closed, sold base asset, deactivated"
                )
            else:
                self.app.db.paper_trading.update_one(
                    {"_id": ObjectId(findId)}, {"$set": {"status": "error"}}
                )
                return jsonResp_error_message("Not enough balance to close and sell")
