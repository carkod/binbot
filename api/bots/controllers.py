from pymongo import ReturnDocument
from time import time
from datetime import datetime
from bson.objectid import ObjectId
from fastapi.exceptions import RequestValidationError
from account.account import Account
from database.mongodb.db import Database
from deals.schema import MarginOrderSchema
from deals.models import BinanceOrderModel, DealModel
from base_producer import BaseProducer
from tools.enum_definitions import BinbotEnums, DealType, Status, Strategy
from tools.handle_error import json_response, json_response_message, json_response_error
from typing import List
from fastapi import Query
from bots.schemas import BotSchema, ErrorsRequestBody
from deals.controllers import CreateDealController
from tools.exceptions import BinanceErrors, InsufficientBalance


class Bot(Database, Account):
    def __init__(self, collection_name="paper_trading"):
        super().__init__()
        self.db_collection = self._db[collection_name]
        self.base_producer = BaseProducer()
        self.producer = self.base_producer.start_producer()
        self.deal: CreateDealController | None = None

    def set_deal_controller(self, bot: BotSchema, collection="bots"):
        self.deal = CreateDealController(bot, db_collection=collection)
        pass

    def get_active_pairs(self, symbol: str | None = None):
        """
        Get distinct (non-repeating) bots by status active
        """
        params = {"status": Status.active}
        if symbol:
            params["pair"] = symbol

        bots = list(self.db_collection.distinct("pair", params))
        return bots

    def get(self, status, start_date=None, end_date=None, no_cooldown=False):
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
            except ValueError:
                resp = json_response(
                    {"message": "start_date must be a timestamp float", "data": []}
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
                    {"message": f"end_date must be a timestamp float: {e}", "data": []}
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

    def get_one(self, bot_id=None, symbol=None, status: Status = None):
        if bot_id:
            params = {"id": bot_id}
        elif symbol:
            params = {"pair": symbol}
        else:
            raise ValueError("id or symbol is required to find bot")

        if status:
            params["status"] = status

        bot = self.db_collection.find_one(params)
        return bot

    def create(self, data: BotSchema):
        """
        Always creates new document
        """
        try:
            bot = data.model_dump()
            bot["id"] = str(ObjectId())

            self.db_collection.insert_one(bot)
            resp = json_response(
                {
                    "message": "Successfully created bot!",
                    "botId": str(bot["id"]),
                }
            )
            self.base_producer.update_required(self.producer, "CREATE_BOT")

        except RequestValidationError as error:
            resp = json_response_error(f"Failed to create new bot: {error}")
            pass

        return resp

    def edit(self, botId, data: BotSchema):
        if not botId:
            return json_response_message("id is required to update bot")

        try:
            # Merge new data with old data
            initial_bot_data = self.db_collection.find_one({"id": botId})
            # Ensure if client-side updated current_price is not overwritten
            # Client side most likely has most up to date current_price because of websockets single pair update in BotDetail
            if data.deal.current_price:
                initial_bot_data["deal"]["current_price"] = data.deal.current_price
            data.deal = initial_bot_data["deal"]
            data.orders = initial_bot_data["orders"]
            data.created_at = initial_bot_data["created_at"]
            data.total_commission = initial_bot_data["total_commission"]
            data.updated_at = round(time() * 1000)
            bot = data.model_dump()
            if "id" in bot:
                bot.pop("id")
            self.db_collection.update_one({"id": botId}, {"$set": bot})
            resp = json_response(
                {"message": "Successfully updated bot", "botId": str(botId)}
            )
        except RequestValidationError as e:
            resp = json_response_error(f"Failed validation: {e}")
            pass

        self.base_producer.update_required(self.producer, "EDIT_BOT")
        return resp

    def delete(self, bot_ids: List[str] = Query(...)):
        """
        Delete by multiple ids.
        For a single id, pass one id in a list
        """

        try:
            self.db_collection.delete_many({"id": {"$in": [id for id in bot_ids]}})
            resp = json_response_message("Successfully deleted bot(s)")
            self.base_producer.update_required(self.producer, "DELETE_BOT")
        except Exception as error:
            resp = json_response_error(f"Failed to delete bot(s) {error}")

        return resp

    def activate(self, bot: dict | BotSchema):
        if isinstance(bot, dict):
            self.active_bot = BotSchema.model_validate(bot)
        else:
            self.active_bot = bot

        CreateDealController(self.active_bot, db_collection="bots").open_deal()
        self.base_producer.update_required(self.producer, "ACTIVATE_BOT")
        return bot

    def deactivate(self, bot: BotSchema) -> dict:
        """
        DO NOT USE, LEGACY CODE NEEDS TO BE REVAMPED
        Close all deals, sell pair and deactivate
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        # Close all active orders
        if len(bot.orders) > 0:
            for d in bot.orders:
                if d.status == "NEW" or d.status == "PARTIALLY_FILLED":
                    order_id = d.order_id
                    try:
                        self.delete_opened_order(bot.pair, order_id)
                    except BinanceErrors as error:
                        if error.code == -2011:
                            self.update_deal_logs(
                                "Order not found. Most likely not completed", bot
                            )
                            pass

        if not bot.deal.buy_total_qty or bot.deal.buy_total_qty == 0:
            msg = "Not enough balance to close and sell"
            self.update_deal_logs(msg, bot)
            raise InsufficientBalance(msg)

        deal_controller = CreateDealController(bot, db_collection="bots")

        if bot.strategy == Strategy.margin_short:
            order_res = deal_controller.margin_liquidation(bot.pair)
            panic_close_order = MarginOrderSchema(
                timestamp=order_res["transactTime"],
                deal_type=DealType.panic_close,
                order_id=order_res["orderId"],
                pair=order_res["symbol"],
                order_side=order_res["side"],
                order_type=order_res["type"],
                price=order_res["price"],
                qty=order_res["origQty"],
                fills=order_res["fills"],
                time_in_force=order_res["timeInForce"],
                status=order_res["status"],
                is_isolated=order_res["isIsolated"],
            )

            for chunk in order_res["fills"]:
                bot.total_commission += float(chunk["commission"])

            bot.orders.append(panic_close_order)
        else:
            try:
                res = deal_controller.spot_liquidation(bot.pair)
            except InsufficientBalance as error:
                self.update_deal_logs(error.message, bot)
                bot.status = Status.completed
                bot = self.save_bot_streaming(bot)
                return bot

            panic_close_order = BinanceOrderModel(
                timestamp=res["transactTime"],
                order_id=res["orderId"],
                deal_type=DealType.panic_close,
                pair=res["symbol"],
                order_side=res["side"],
                order_type=res["type"],
                price=res["price"],
                qty=res["origQty"],
                fills=res["fills"],
                time_in_force=res["timeInForce"],
                status=res["status"],
            )

            for chunk in res["fills"]:
                bot.total_commission += float(chunk["commission"])

            bot.orders.append(panic_close_order)

        bot.deal = DealModel(
            buy_timestamp=res["transactTime"],
            buy_price=res["price"],
            buy_total_qty=res["origQty"],
            current_price=res["price"],
        )

        bot.status = Status.completed
        bot_obj = bot.model_dump()
        if "_id" in bot_obj:
            bot_obj.pop("_id")

        document = self.db_collection.find_one_and_update(
            {"id": bot.id},
            {"$set": bot},
            return_document=ReturnDocument.AFTER,
        )

        return document

    def put_archive(self, botId):
        """
        Change status to archived
        """
        bot = self.db_collection.find_one({"id": botId})
        if bot["status"] == "active":
            return json_response(
                {"message": "Cannot archive an active bot!", "botId": botId}
            )

        if bot["status"] == "archived":
            status = "inactive"
        else:
            status = "archived"

        try:
            self.db_collection.update_one({"id": botId}, {"$set": {"status": status}})
            resp = json_response(
                {"message": "Successfully archived bot", "botId": botId}
            )
            return resp
        except Exception as error:
            resp = json_response({"message": f"Failed to archive bot {error}"})

        return resp

    def post_errors_by_id(self, bot_id: str, reported_error: ErrorsRequestBody):
        """
        Directly post errors to Bot
        which should show in the BotForm page in Web

        Similar to update_deal_errors
        but without a bot instance.
        """
        operation = {"$push": {"errors": reported_error}}
        if isinstance(reported_error, list):
            operation = {"$push": {"errors": {"$each": reported_error}}}
        elif isinstance(reported_error, str):
            operation = {"$push": {"errors": reported_error}}
        else:
            raise ValueError("reported_error must be a list")

        self.db_collection.update_one({"id": bot_id}, operation)
        pass
