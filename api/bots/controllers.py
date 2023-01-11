import asyncio
from datetime import datetime
from time import time

import requests
from bson.objectid import ObjectId
from fastapi.exceptions import RequestValidationError

from account.account import Account
from db import setup_db
from deals.controllers import CreateDealController
from orders.models.book_order import Book_Order
from tools.enum_definitions import BinbotEnums
from tools.exceptions import OpenDealError
from tools.handle_error import (
    NotEnoughFunds,
    QuantityTooLow,
    handle_binance_errors,
    json_response,
    json_response_message,
    json_response_error
)
from tools.round_numbers import supress_notation
from typing import List
from fastapi import Query
from bots.schemas import BotSchema

class Bot(Account):
    def __init__(self, collection_name="paper_trading"):
        self.db = setup_db()
        self.db_collection = self.db[collection_name]
    
    def _update_required(self):
        self.db.research_controller.update_one({"_id": "settings"}, {"$set": {"update_required": True}})
        return

    def get(self, status, start_date, end_date, no_cooldown):
        """
        Get all bots in the db except archived
        Args:
        - archive=false
        - filter_by: string - last-week, last-month, all
        """
        params = {}

        if status and status in BinbotEnums.statuses:
            params["status"] = status

        if start_date:
            try:
                float(start_date)
            except ValueError as error:
                resp = json_response(
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
                resp = json_response(
                    {"message": f"end_date must be a timestamp float", "data": []}
                )
                return resp

            obj_end_date = datetime.fromtimestamp(int(float(end_date) / 1000))
            lte_tp_id = ObjectId.from_datetime(obj_end_date)
            params["_id"]["$lte"] = lte_tp_id

        # Only retrieve active and cooldown bots
        # These bots will be removed from signals
        if status and no_cooldown:
            params = {
                "$or": [
                    {"status": status},
                    {
                        "$where": """function () {
                            if (this.deal !== undefined) {
                                return new Date().getTime() - this.deal.sell_timestamp < (this.cooldown * 1000)
                            } else {
                                return (new Date().getTime() - this.created_at < (this.cooldown * 1000))
                            }
                        }"""
                    },
                ]
            }

        try:
            bot = list(
                self.db_collection.find(params).sort(
                    [("_id", -1), ("status", 1), ("pair", 1)]
                )
            )
            resp = json_response({"message": "Sucessfully found bots!", "data": bot})
        except Exception as error:
            resp = json_response_message(error)

        return resp

    def get_one(self, findId):
        bot = self.db_collection.find_one({"id": findId})
        if bot:
            resp = json_response({"message": "Bot found", "data": bot})
        else:
            resp = json_response({"message": "Bots not found"}, 404)
        return resp

    def create(self, data):
        """
        Always creates new document
        """
        try:
            bot = data.dict()
            self.db_collection.insert_one(bot)
            resp = json_response(
                {
                    "message": "Successfully created bot!",
                    "botId": str(bot["id"]),
                }
            )

            self._update_required()
        except RequestValidationError as error:
            resp = json_response_error(f"Failed to create new bot: {error}")
        except Exception as e:
            resp = json_response_error(f"Failed to create new bot: {e}")
        return resp

    def edit(self, botId, data):
        if not botId:
            return json_response_message("id is required to update bot")

        try:
            bot = data.dict()
            if "id" in bot:
                bot.pop("id")
            self.db_collection.update_one({"id": ObjectId(botId)}, {"$set": bot})
            resp = json_response(
                {"message": "Successfully updated bot", "botId": str(botId)}
            )
            self._update_required()
        except RequestValidationError as e:
            resp = json_response_error(f"Failed validation: {e}")
        except Exception as e:
            resp = json_response_error(f"Failed to create new bot: {e}")
        return resp

    def delete(self, bot_ids: List[str] = Query(...)):

        if not bot_ids or not isinstance(bot_ids, list):
            return json_response_error("At least one bot id is required")

        try:
            self.db_collection.delete_many(
                {"id": {"$in": [id for id in bot_ids]}}
            )
            resp = json_response_message("Successfully deleted bot(s)")
        except Exception as error:
            resp = json_response_error(f"Failed to delete bot(s) {error}")
            
        return resp

    def activate(self, botId: str):
        bot = self.db_collection.find_one({"id": botId})
        if bot:

            try:
                CreateDealController(
                    bot, db_collection=self.db_collection.name
                ).open_deal()
                resp = json_response_message("Successfully activated bot!")
                self._update_required()
                # asyncio.Event.connection_open = False  # type: ignore
                return resp
            except OpenDealError as error:
                print(error)
                return json_response_error(error.args[0])
            except NotEnoughFunds as e:
                return json_response_error(e.args[0])
            except Exception as error:
                resp = json_response_error(f"Unable to activate bot: {error}")
                return resp
        else:
            return json_response_error("Bot not found.")

    def deactivate(self, findId):
        """
        Close all deals, sell pair and deactivate
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        bot = self.db_collection.find_one({"id": findId })
        resp = json_response_message(
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
                        res = requests.delete(
                            url=f'{self.bb_close_order_url}/{bot["pair"]}/{order_id}'
                        )
                        error_msg = f"Failed to delete opened order {order_id}."
                        # Handle error and continue
                        handle_binance_errors(res)

            # Sell everything
            pair = bot["pair"]
            base_asset = self.find_baseAsset(pair)
            bot = BotSchema.parse_obj(bot)
            precision = self.price_precision
            qty_precision = self.qty_precision
            balance = self.get_one_balance(base_asset)
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
                    order_res = self.request(
                        method="POST", url=self.bb_sell_order_url, json=order
                    )
                    
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
                            resp = json_response_message(e)
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
                        {"id": ObjectId(findId)},
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
                    {"id": ObjectId(findId)},
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

                asyncio.Event.connection_open = False
                return json_response_message(
                    "Active orders closed, sold base asset, deactivated"
                )
            else:
                self.db_collection.update_one(
                    {"id": ObjectId(findId)}, {"$set": {"status": "error"}}
                )
                return json_response_message("Not enough balance to close and sell")

    def put_archive(self, botId):
        """
        Change status to archived
        """
        bot = self.db_collection.find_one({"id": botId })
        if bot["status"] == "active":
            return json_response(
                {"message": "Cannot archive an active bot!", "botId": botId}
            )

        if bot["status"] == "archived":
            status = "inactive"
        else:
            status = "archived"

        try:
            self.db_collection.update_one(
                {"id": ObjectId(botId)}, {"$set": {"status": status}}
            )
            resp = json_response(
                {"message": "Successfully archived bot", "botId": botId}
            )
            return resp
        except Exception as error:
            resp = json_response({"message": f"Failed to archive bot {error}"})
            
        return resp
