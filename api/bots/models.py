from flask import Response, current_app as app
from flask import request
from datetime import date

from api.account.models import Account
from api.deals.models import Deal
from bson.objectid import ObjectId
from api.tools.jsonresp import jsonResp


class Bot(Account):
    def __init__(self):
        self.defaults = {
            "pair": "",
            "active": "false",
            "strategy": "long",
            "name": "Default Bot",
            "max_so_count": "0",
            "balance_usage": "1",  # 100% of All Btc balance
            "balance_usage_size": "0.0001",
            "base_order_size": "3",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "short_stop_price": "0",  # Flip to short strategy threshold
            "short_order": "0",  # Quantity flip to short
            "start_condition": "true",
            "so_size": "0.0001",  # Top band
            "take_profit": "0.003",  # 3% take profit
            "price_deviation_so": "0.63",  # % percentage
            "trailling": "false",
            "trailling_deviation": "0.63",
            "deal_min_value": "0",
            "cooldown": "0",
            "deals": [],
            "stop_loss": "0",
        }

    def get(self):
        resp = jsonResp({"message": "Endpoint failed"}, 200)
        bot = list(app.db.bots.find())
        if bot:
            resp = jsonResp({"data": bot}, 200)
        else:
            resp = jsonResp({"message": "Bots not found", "data": []}, 200)
        return resp

    def get_one(self):
        resp = jsonResp({"message": "No bots found"}, 200)
        findId = request.view_args["id"]
        bot = app.db.bots.find_one({"_id": ObjectId(findId)})
        if bot:
            resp = jsonResp({"message": "Bot found", "data": bot}, 200)
        else:
            resp = jsonResp({"message": "Bots not found"}, 404)
        return resp

    def create(self):
        resp = jsonResp({"message": "Bot creation not available"}, 400)
        data = request.json
        data["name"] = (
            data["name"] if data["name"] != "" else f"{data['pair']}-{date.today()}"
        )
        self.defaults.update(data)
        botId = app.db.bots.save(self.defaults, {"$currentDate": {"createdAt": "true"}})
        if botId:
            resp = jsonResp(
                {"message": "Successfully created new bot", "botId": str(botId)}, 200
            )
        else:
            resp = jsonResp({"message": "Failed to create new bot"}, 400)

        return resp

    def edit(self):
        resp = jsonResp({"message": "Bot update is not available"}, 400)
        data = request.json
        findId = request.view_args["id"]
        self.defaults.update(data)
        botId = app.db.bots.update_one(
            {"_id": ObjectId(findId)}, {"$set": self.defaults}, upsert=False
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
        delete_action = app.db.bots.delete_one({"_id": ObjectId(findId)})
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
        bot = app.db.bots.find_one({"_id": ObjectId(findId)})

        if bot:
            dealId, order_errors = Deal(bot, app).open_deal()

            # If error
            if isinstance(dealId, Response):
                resp = jsonResp(dealId.json, 200)
                return resp

            if dealId and not order_errors:
                bot["active"] = "true"
                bot["deals"].append(dealId)
                botId = app.db.bots.save(bot)
                if botId:
                    resp = jsonResp(
                        {
                            "message": "Successfully activated bot and triggered deals with no errors",
                            "botId": str(findId),
                        },
                        200,
                    )
                return resp
            elif dealId and order_errors:
                bot["active"] = "true"
                bot["deals"].append(dealId)
                botId = app.db.bots.save(bot)
                if botId:
                    resp = jsonResp(
                        {
                            "message": f"Successfully activated bot, deals had errors {','.join(order_errors)}",
                            "botId": str(findId),
                        },
                        200,
                    )
                return resp
            else:
                resp = jsonResp(
                    {"message": "Deal base order failed", "botId": findId}, 400
                )

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
        bot = app.db.bots.find_one({"_id": ObjectId(findId)})
        if bot:

            # Close deals and sell everything
            dealId = Deal(bot, app).close_deals()

            # If error
            if isinstance(dealId, Response):
                resp = dealId
                return resp

            if dealId:
                bot["active"] = "false"
                bot["deals"] = []
                botId = app.db.bots.update_one(
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
