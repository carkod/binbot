import threading
from datetime import date
from time import time

from api.account.account import Account
from api.deals.models import Deal
from api.orders.models.book_order import Book_Order
from api.threads import market_update_thread
from api.tools.handle_error import handle_binance_errors, jsonResp
from api.tools.round_numbers import round_numbers, supress_notation
from bson.objectid import ObjectId
from flask import Response, current_app, request
from requests import delete, post
from pymongo.errors import DuplicateKeyError

class Bot(Account):
    def __init__(self):
        self.app = current_app
        self.default_deal = (
            {
                "buy_price": "0",
                "current_price": "0",
                "buy_total_qty": "0",
                "take_profit": "0",
            },
        )
        self.defaults = {
            "pair": "",
            "status": "inactive",  # New replacement for active (inactive, active, completed)
            "name": "Default Bot",
            "mode": "manual",
            "max_so_count": "0",
            "balance_usage_size": "0.0001",
            "balance_to_use": "GBP",
            "base_order_size": "0.0001",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "candlestick_interval": "15m",
            "take_profit": "3",
            "trailling": "false",
            "trailling_deviation": "0.63",
            "trailling_profit": 0,  # Trailling activation (first take profit hit)
            "deal_min_value": "0",
            "orders": [],
            "stop_loss": "0",
            "deal": self.default_deal,
            "safety_orders": {},
            "errors": [],
            "total_commission": 0
        }
        self.default_so = {"so_size": "0", "price": "0", "price_deviation_so": "0.63"}

    def _restart_websockets(self):
        """
        Restart websockets threads after list of active bots altered
        """
        print("Restarting market_updates")
        # Notify market updates websockets to update
        for thread in threading.enumerate():
            if thread.name == "market_updates_thread":
                thread._target.__self__.markets_streams.close()
                market_update_thread()
        print("Finished restarting market_updates")
        return

    def get(self):
        """
        Get all bots in the db except archived
        Args:
        - archive=false
        """
        params = {}
        if request.args.get("status") == "active":
            params["active"] = "active"

        bot = list(self.app.db.bots.find(params).sort([("_id", -1), ("status", 1), ("pair", 1)]))
        if bot:
            resp = jsonResp({"data": bot})
        else:
            resp = jsonResp({"message": "Bots not found", "data": []})
        return resp

    def get_one(self):
        findId = request.view_args["id"]
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})
        if bot:
            resp = jsonResp({"message": "Bot found", "data": bot})
        else:
            resp = jsonResp({"message": "Bots not found"}, 404)
        return resp

    def create(self):
        data = request.json
        data["name"] = (
            data["name"] if data["name"] != "" else f"{data['pair']}-{date.today()}"
        )
        self.defaults.update(data)
        self.defaults["safety_orders"] = data["safety_orders"]
        try:
            botId = self.app.db.bots.save(
                self.defaults, {"$currentDate": {"createdAt": "true"}}
            )
        except DuplicateKeyError:
            resp = jsonResp(
                {"message": "Profit canibalism, bot with this pair already exists!", "error": 1}, 200
            )
            return resp
        if botId:
            resp = jsonResp(
                {"message": "Successfully created new bot", "botId": str(botId)}, 200
            )
            self._restart_websockets()
        else:
            resp = jsonResp({"message": "Failed to create new bot"}, 400)

        return resp

    def edit(self):
        data = request.json
        findId = request.view_args["id"]
        find_bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})
        self.defaults.update(data)
        self.defaults["safety_orders"] = data["safety_orders"]
        # Deal and orders are internal, should never be updated by outside data
        self.defaults["deal"] = find_bot["deal"]
        self.defaults["orders"] = find_bot["orders"]
        botId = self.app.db.bots.update_one(
            {"_id": ObjectId(findId)}, {"$set": self.defaults}
        )
        if botId.acknowledged:
            resp = jsonResp(
                {"message": "Successfully updated bot", "botId": findId}, 200
            )
            self._restart_websockets()
        else:
            resp = jsonResp({"message": "Failed to update bot"}, 400)

        return resp

    def delete(self):
        findId = request.view_args["id"]
        delete_action = self.app.db.bots.delete_one({"_id": ObjectId(findId)})
        if delete_action:
            resp = jsonResp(
                {"message": "Successfully delete bot", "botId": findId}, 200
            )
            self._restart_websockets()
        else:
            resp = jsonResp({"message": "Bot deletion is not available"}, 400)
        return resp

    def required_field_validation(self, data, key):
        if key in data:
            return data[key]
        else:
            resp = jsonResp(
                {
                    "message": "Validation failed {} is required".format(key),
                    "botId": data["_id"],
                },
                400,
            )
            return resp

    def activate(self):
        findId = request.view_args["botId"]
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})

        if bot:
            order_errors = Deal(bot).open_deal()

            if isinstance(order_errors, Response):
                return order_errors

            # If error
            if len(order_errors) > 0:
                # If base order fails makes no sense to activate
                if "base_order_error" in order_errors[0]:
                    resp = jsonResp(
                        {
                            "message": f'Failed to activate bot, {order_errors[0]["base_order_error"]}',
                            "botId": str(findId),
                            "error": 1,
                        }
                    )
                else:
                    resp = jsonResp(
                        {
                            "message": f"Failed to activate bot, {','.join(order_errors)}",
                            "botId": str(findId),
                            "error": 1,
                        }
                    )
                return resp

            botId = self.app.db.bots.find_one_and_update(
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
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})

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
            deal_object = Deal(bot)
            balance = deal_object.get_one_balance(base_asset)
            if balance:
                qty = round_numbers(balance, deal_object.qty_precision)
                book_order = Book_Order(pair)
                price = float(book_order.matching_engine(True, qty))

                if price:
                    order = {
                        "pair": pair,
                        "qty": qty,
                        "price": supress_notation(price, deal_object.price_precision),
                    }
                    res = post(url=self.bb_sell_order_url, json=order)
                else:
                    order = {
                        "pair": pair,
                        "qty": qty,
                    }
                    res = post(url=self.bb_sell_market_order_url, json=order)

                handle_binance_errors(res)

        # Hedge with GBP and complete bot
        deal_object.buy_gbp_balance()
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})
        if "errors" in bot and len(bot["errors"]) > 0:
            self.app.db.bots.find_one_and_update(
                {"pair": pair},
                {"$set": {"status": "errors"}},
            )
            resp = jsonResp(
                {
                    "message": "Errors encountered during deactivation, please check bot errors.",
                    "error": 1,
                }
            )
            self._restart_websockets()

        else:
            self.app.db.bots.find_one_and_update(
                {"pair": pair}, {"$set": {"status": "completed", "deal.sell_timestamp": time()}}
            )
            resp = jsonResp(
                {
                    "message": "Active orders closed, sold base asset, bought back GBP, deactivated",
                    "error": 0,
                }
            )
            self._restart_websockets()
        return resp

    def put_archive(self):
        """
        Change status to archived
        """
        botId = request.view_args["id"]
        bot = self.app.db.bots.find_one_and_update({"_id": ObjectId(botId)})
        if bot["status"] == "active":
            return jsonResp(
                {"message": "Cannot archive an active bot!", "botId": botId}
            )

        if bot["status"] == "archived":
            status = "inactive"
        else:
            status = "archived"

        archive = self.app.db.bots.update(
            {"_id": ObjectId(botId)}, {"$set": {"status": status}}
        )
        if archive:
            resp = jsonResp(
                {"message": "Successfully archived bot", "botId": botId})
        else:
            resp = jsonResp({"message": "Failed to archive bot"})
        return resp
