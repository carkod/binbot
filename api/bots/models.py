import threading
from datetime import date
from time import time
from api.account.account import Account
from api.deals.models import Deal
from api.deals.schema import DealSchema
from api.orders.models.book_order import Book_Order
from api.threads import market_update_thread
from api.tools.enum_definitions import EnumDefinitions
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
from api.bots.schemas import BotSchema


class Bot(Account):
    def __init__(self):
        self.app = current_app
        self.default_deal = DealSchema()
        self.defaults = BotSchema()
        self.default_so = {"so_size": "0", "price": "0", "price_deviation_so": "0.63"}

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

    def get(self):
        """
        Get all bots in the db except archived
        Args:
        - archive=false
        """
        params = {}
        bot_schema = BotSchema()
        if request.args.get("status") in bot_schema.statuses:
            params["active"] = request.args.get("status")

        bot = list(
            self.app.db.bots.find(params).sort(
                [("_id", -1), ("status", 1), ("pair", 1)]
            )
        )
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
        data = request.get_json()
        try:
            result = BotSchema().update(data)
            botId = str(result.inserted_id)
            resp = jsonResp(
                {"message": "Successfully created new bot", "botId": str(botId)}
            )
        except Exception as e:
            resp = jsonResp_error_message(f"Failed to create new bot: {e}")
        return resp

    def edit(self):
        data = request.get_json()
        botId = request.view_args["id"]
        try:
            BotSchema().update(data)
            resp = jsonResp(
                {"message": "Successfully updated bot", "botId": botId}, 200
            )
        except Exception as e:
            resp = jsonResp_error_message(f"Failed to update bot: {e}")

        return resp

    def delete(self):
        botIds = request.args.getlist("id")

        if not botIds or not isinstance(botIds, list):
            return jsonResp_error_message("At least one bot id is required")
        

            
        delete_action = self.app.db.bots.delete_many({"_id": {"$in": [ObjectId(item) for item in botIds]}})
        if delete_action:
            resp = jsonResp_message("Successfully deleted bot")
            self._restart_websockets()
        else:
            resp = jsonResp({"message": "Bot deletion is not available"}, 400)
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
            deal_object = Deal(bot)
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
                            BotSchema().update(bot)
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
                            BotSchema().update(bot)
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
                    self.app.db.bots.update_one(
                        {"_id": ObjectId(findId)},
                        {
                            "$push": {"orders": deactivation_order, "errors": "Order failed to close. Re-deactivating..."},
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
                self.app.db.bots.update_one(
                    {"_id": ObjectId(findId)},
                    {
                        "$set": {"status": "completed", "deal.sell_timestamp": time()},
                        "$push": {"orders": deactivation_order, "errors": "Orders updated. Trying to close bot..."},
                    },
                )

                self._restart_websockets()
                return jsonResp_message(
                    "Active orders closed, sold base asset, deactivated"
                )
            else:
                self.app.db.bots.update_one(
                    {"_id": ObjectId(findId)}, {"$set": {"status": "error"}}
                )
                return jsonResp_error_message("Not enough balance to close and sell")

    def put_archive(self):
        """
        Change status to archived
        """
        botId = request.view_args["id"]
        bot = self.app.db.bots.find_one({"_id": ObjectId(botId)})
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
            resp = jsonResp({"message": "Successfully archived bot", "botId": botId})
        else:
            resp = jsonResp({"message": "Failed to archive bot"})
        return resp
