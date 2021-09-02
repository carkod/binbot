from flask import Response
from flask import request
from datetime import date

from api.account.account import Account
from api.deals.models import Deal
from bson.objectid import ObjectId
from api.tools.jsonresp import jsonResp
from api.app import create_app

class Bot(Account):
    def __init__(self):
        self.app = create_app()
        self.defaults = {
            "pair": "",
            "active": "false",
            "strategy": "long",
            "name": "Default Bot",
            "max_so_count": "0",
            "balance_usage": "1",  # 100% of All Btc balance
            "balance_usage_size": "0.0001",
            "balance_to_use": "GBP",
            "base_order_size": "3",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "short_stop_price": "0",  # Flip to short strategy threshold
            "short_order": "0",  # Quantity flip to short
            "start_condition": "true",
            "take_profit": "0.003",  # 3% take profit
            "trailling": "false",
            "trailling_deviation": "0.63",
            "deal_min_value": "0",
            "deals": [],
            "orders": [],
            "stop_loss": "0",
            "deal": {
                "buy_price": "",
                "current_price": "",
                "buy_total_qty": "",
                "take_profit": "",
            },
            "safety_orders": {}
        }
        self.default_so = {
            "so_size": "0",
            "price": "0",
            "price_deviation_so": "0.63"
        }

    def get(self):
        resp = jsonResp({"message": "Endpoint failed"}, 200)
        bot = list(self.app.db.bots.find())
        if bot:
            resp = jsonResp({"data": bot}, 200)
        else:
            resp = jsonResp({"message": "Bots not found", "data": []}, 200)
        return resp

    def get_one(self):
        resp = jsonResp({"message": "No bots found"}, 200)
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
        botId = self.app.db.bots.save(self.defaults, {"$currentDate": {"createdAt": "true"}})
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
        self.defaults.update(data)
        self.defaults["safety_orders"] = data["safety_orders"]
        botId = self.app.db.bots.update_one(
            {"_id": ObjectId(findId)}, {"$set": self.defaults}, upsert=True
        )
        if botId.acknowledged:
            resp = jsonResp(
                {"message": "Successfully updated bot", "botId": findId}, 200
            )
        else:
            resp = jsonResp({"message": "Failed to update bot"}, 400)

        return resp

    def delete(self):
        resp = jsonResp({"message": "Bot update is not available"}, 400)
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
                    resp = jsonResp({
                        "message": f'Failed to activate bot, {order_errors[0]["base_order_error"]}',
                        "botId": str(findId),
                        "error": 1
                    }, 200)
                else:
                    resp = jsonResp({
                        "message": f"Failed to activate bot, {','.join(order_errors)}",
                        "botId": str(findId),
                        "error": 1
                    }, 200)
                return resp

            botId = self.app.db.bots.find_one_and_update({"_id": ObjectId(findId)}, {
                "$set": {
                    "active": "true"
                }
            })

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
        Deactivation involves
        - Closing all deals (opened orders)
        - Selling all assets in the market
        - Finally emptying the deals array in the bot
        - After above actions succeed, update the DB with all these changes
        The bot is kept for archive purposes
        """
        resp = jsonResp({"message": "Bot deactivation is not available"}, 400)
        findId = request.view_args["botId"]
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})
        if bot:

            # Close deals and sell everything
            dealId = Deal(bot).close_deals()

            # If error
            if isinstance(dealId, Response):
                resp = dealId
                return resp

            if dealId:
                bot["active"] = "false"
                bot["deals"] = []
                botId = self.app.db.bots.update_one(
                    {"_id": ObjectId(findId)},
                    {"$set": {"deals": [], "active": "false"}},
                )
                if botId:
                    resp = jsonResp(
                        {"message": "Successfully deactivated bot!", "data": bot}, 200
                    )
        else:
            resp = jsonResp({"message": "Bot not found", "botId": findId}, 400)
        return resp

    def close(self):
        """
        Close all deals and sell pair
        1. Close all deals
        2. Sell Coins
        3. Delete bot
        """
        findId = request.view_args["id"]
        bot = self.app.db.bots.find_one({"_id": ObjectId(findId)})

        if bot:
            close_response = Deal(bot).close_all()
            if isinstance(close_response, Response):
                return close_response

            self.delete()

            response = jsonResp({"message": "Successfully closed bots", "botId": findId}, 400)
            return response

        else:
            response = jsonResp({"message": "Bot not found", "botId": findId}, 400)

        return response
