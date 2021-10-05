from api.threads import market_update_thread
import threading
from flask import Response, request, current_app
from datetime import date

from api.account.account import Account
from api.deals.models import Deal
from bson.objectid import ObjectId
from api.tools.handle_error import jsonResp
from api.tools.handle_error import bot_errors

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
            "max_so_count": "0",
            "balance_usage_size": "0.0001",
            "balance_to_use": "GBP",
            "base_order_size": "0.0001",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "short_stop_price": "0",  # Flip to short strategy threshold
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
        }
        self.default_so = {"so_size": "0", "price": "0", "price_deviation_so": "0.63"}

    def get(self):
        resp = jsonResp({"message": "Endpoint failed"}, 200)
        bot = list(self.app.db.bots.find())
        if bot:
            resp = jsonResp({"data": bot}, 200)
        else:
            resp = jsonResp({"message": "Bots not found", "data": []}, 200)
        return resp

    def get_one(self):
        findId = request.view_args["id"]
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})
        if bot:
            resp = jsonResp({"message": "Bot found", "data": bot}, 200)
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
        botId = self.app.db.bots.save(
            self.defaults, {"$currentDate": {"createdAt": "true"}}
        )
        if botId:
            resp = jsonResp(
                {"message": "Successfully created new bot", "botId": str(botId)}, 200
            )
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
            # Notify market updates websockets to update
            for thread in threading.enumerate():
                if thread.name == "market_updates_thread":
                    thread._target.__self__.markets_streams.close()
                    market_update_thread()
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
                        },
                        200,
                    )
                else:
                    resp = jsonResp(
                        {
                            "message": f"Failed to activate bot, {','.join(order_errors)}",
                            "botId": str(findId),
                            "error": 1,
                        },
                        200,
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
            close_response = Deal(bot).close_all()
            bot_errors(close_response, bot)

            updated_bot = self.app.db.bots.update_one(
                {"_id": ObjectId(findId)},
                {"$set": {"deal": self.default_deal, "status": "closed"}},
            )
            if updated_bot:
                # We don't want to automatically delete after closing
                # As this closing function may be executed by algo
                resp = jsonResp(
                    {
                        "message": "Active orders closed, sold base asset, bought back GBP, deactivated"
                    },
                    200,
                )
                return resp
            else:
                bot_errors(updated_bot, bot)
                resp = jsonResp(
                    {
                        "message": "Active orders closed, sold base asset, bought back GBP, deactivation failed"
                    },
                    200,
                )
                return resp

        else:
            response = jsonResp({"message": "Bot not found", "botId": findId}, 400)

        return response
