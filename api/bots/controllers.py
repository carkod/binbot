import threading
from datetime import datetime
from time import time

from api.account.account import Account
from api.bots.schemas import BotSchema, SafetyOrderSchema
from api.deals.controllers import CreateDealController
from api.orders.models.book_order import Book_Order
from api.threads import market_update_thread
from api.tools.enum_definitions import EnumDefinitions
from api.tools.exceptions import OpenDealError
from api.tools.handle_error import (
    NotEnoughFunds,
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
from marshmallow.exceptions import ValidationError
from marshmallow import EXCLUDE

class Bot(Account):
    def __init__(self, collection_name="bots"):
        self.app = current_app
        self.db_collection = self.app.db[collection_name]

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
                print(
                    "Finished restarting market_updates. Current #threads",
                    [t for t in threading.enumerate() if t.name == "market_updates_thread"],
                )
        return

    def post_dump(self, schema, data):
        """
        Deserialize to store in DB
        """

        return schema.load(data)

    def get(self):
        """
        Get all bots in the db except archived
        Args:
        - archive=false
        - filter_by: string - last-week, last-month, all
        """
        status = request.args.get("status")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        no_cooldown = request.args.get("no_cooldown")
        params = {}

        if status and status in EnumDefinitions.statuses:
            params["active"] = status

        if start_date:
            try:
                float(start_date)
            except ValueError as error:
                resp = jsonResp(
                    {"message": f"start_date must be a timestamp float", "data": []}
                )
                return resp

            obj_start_date = datetime.fromtimestamp(int(float(start_date) / 1000))
            gte_tp_id = ObjectId.from_datetime(obj_start_date)
            try:
                params["_id"]["$gte"] = gte_tp_id
            except KeyError:
                params["_id"] = {"$gte": gte_tp_id}

        if end_date:
            try:
                float(end_date)
            except ValueError as e:
                resp = jsonResp(
                    {"message": f"end_date must be a timestamp float", "data": []}
                )
                return resp

            obj_end_date = datetime.fromtimestamp(int(float(end_date) / 1000))
            lte_tp_id = ObjectId.from_datetime(obj_end_date)
            params["_id"]["$lte"] = lte_tp_id

        # Only retrieve active and cooldown bots
        # These bots will be removed from signals
        if status and no_cooldown:
            current_ts = time() * 1000
            params = {
                "$or": [
                    {"status": status},
                    {
                        "$where": f"{current_ts} - this.deal.sell_timestamp < (this.cooldown * 1000)"
                    },
                ]
            }

        bot = list(
            self.db_collection.find(params).sort(
                [("_id", -1), ("status", 1), ("pair", 1)]
            )
        )
        if bot:
            resp = jsonResp({"message": "Sucessfully found bots!", "data": bot})
        else:
            resp = jsonResp({"message": "Bots not found", "data": []})
        return resp

    def get_one(self):
        findId = request.view_args["id"]
        bot = self.db_collection.find_one({"_id": ObjectId(findId)})
        if bot:
            resp = jsonResp({"message": "Bot found", "data": bot})
        else:
            resp = jsonResp({"message": "Bots not found"}, 404)
        return resp

    def create(self):
        data = request.get_json()
        try:
            bot_schema = BotSchema(unknown=EXCLUDE)
            bot = bot_schema.load(data)
            if "_id" in bot:
                result = self.db_collection.update_one({"_id": ObjectId(bot["_id"])}, bot)
                resp = jsonResp(
                    {"message": "This bot already exists, successfully updated bot", "botId": str(result.updated_id)}
                )
            else:
                result = self.db_collection.insert_one(bot)
                resp = jsonResp(
                    {"message": "Successfully created new bot", "botId": str(result.inserted_id)}
                )
        except ValidationError as e:
            resp = jsonResp_error_message(f"Failed validation: {e.messages}")
        except Exception as e:
            resp = jsonResp_error_message(f"Failed to create new bot: {e}")
        return resp

    def edit(self):
        data = request.get_json()
        if "id" not in request.view_args:
            return jsonResp_error_message("id is required to update bot")

        botId = request.view_args["id"]
        try:
            bot_schema = BotSchema()
            bot = bot_schema.load(data)
            if "_id" in bot:
                bot.pop("_id")
            result = self.db_collection.update_one({"_id": ObjectId(botId)}, {"$set": bot})
            resp = jsonResp({"message": "Successfully updated bot", "botId": str(botId)})
        except ValidationError as e:
            resp = jsonResp_error_message(f"Failed validation: {e.messages}")
        except Exception as e:
            resp = jsonResp_error_message(f"Failed to create new bot: {e}")
        return resp

    def delete(self):
        botIds = request.args.getlist("id")

        if not botIds or not isinstance(botIds, list):
            return jsonResp_error_message("At least one bot id is required")

        delete_action = self.db_collection.delete_many(
            {"_id": {"$in": [ObjectId(item) for item in botIds]}}
        )
        if delete_action:
            resp = jsonResp_message("Successfully deleted bot")
        else:
            resp = jsonResp({"message": "Bot deletion is not available"}, 400)
        return resp

    def activate(self):
        botId = request.view_args["botId"]
        bot = self.db_collection.find_one({"_id": ObjectId(botId)})

        if bot:
            try:
                CreateDealController(bot).open_deal()
            except OpenDealError as error:
                return jsonResp_error_message(error)
            except NotEnoughFunds as e:
                return jsonResp_error_message(e.args[0])

            try:
                botId = self.db_collection.update_one(
                    {"_id": ObjectId(botId)}, {"$set": {"status": "active"}}
                )
                resp = jsonResp_message("Successfully activated bot!")
                self._restart_websockets()
            except Exception as error:
                resp = jsonResp(
                    {
                        "message": f"Unable to save bot: {error}",
                        "botId": str(botId),
                    },
                    200,
                )
                return resp

        return resp

    def deactivate(self):
        """
        Close all deals, sell pair and deactivate
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        findId = request.view_args["id"]
        bot = self.db_collection.find_one({"_id": ObjectId(findId)})
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

                if price and float(supress_notation(qty, qty_precision)) < 1:
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
                            self.bot_schema.update(bot)
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
                            self.bot_schema.update(bot)
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
                    self.db_collection.update_one(
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
                self.db_collection.update_one(
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
                self.db_collection.update_one(
                    {"_id": ObjectId(findId)}, {"$set": {"status": "error"}}
                )
                return jsonResp_error_message("Not enough balance to close and sell")

    def put_archive(self):
        """
        Change status to archived
        """
        botId = request.view_args["id"]
        bot = self.db_collection.find_one({"_id": ObjectId(botId)})
        if bot["status"] == "active":
            return jsonResp(
                {"message": "Cannot archive an active bot!", "botId": botId}
            )

        if bot["status"] == "archived":
            status = "inactive"
        else:
            status = "archived"

        archive = self.db_collection.update(
            {"_id": ObjectId(botId)}, {"$set": {"status": status}}
        )
        if archive:
            resp = jsonResp({"message": "Successfully archived bot", "botId": botId})
        else:
            resp = jsonResp({"message": "Failed to archive bot"})
        return resp
