from flask import current_app as app
from flask import request
from datetime import date

from main import tools
from main.account.models import Account
from main.deals.models import Deal
from bson.objectid import ObjectId

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
            "base_order_size": "0.003",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "start_condition": "true",
            "so_size": "0.0001",  # Top band
            "take_profit": "0.003", # 30% take profit
            "price_deviation_so": "0.0063",  # % percentage
            "trailling": "false",
            "trailling_deviation": "0.0063",
            "deal_min_value": "0",
            "cooldown": "0",
            "deals": [],
        }

    def get(self):
        resp = tools.JsonResp({"message": "No bots found"}, 200)
        bot = list(app.db.bots.find())
        if bot:
            resp = tools.JsonResp({"data": bot}, 200)
        else:
            resp = tools.JsonResp({"message": "Bots not found"}, 404)
        return resp

    def get_one(self):
        resp = tools.JsonResp({"message": "No bots found"}, 200)
        findId = request.view_args["id"]
        bot = list(app.db.bots.find_one({"_id": findId}))

        if bot:
            resp = tools.JsonResp({"data": bot}, 200)
        else:
            resp = tools.JsonResp({"message": "Bots not found"}, 404)
        return resp

    def create(self):
        resp = tools.JsonResp({"message": "Bot creation not available"}, 400)
        data = request.json
        # base_order_size = self.get_base_order_size(data['pair'], data['maxSOCount'], data['take_profit'])

        data["name"] = data["name"] if data["name"] != "" else f"Bot-{date.today()}"
        self.defaults.update(data)
        botId = app.db.bots.save(data)
        if botId:
            resp = tools.JsonResp(
                {"message": "Successfully created new bot", "botId": str(botId)}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Failed to create new bot"}, 400)

        return resp

    def edit(self):
        resp = tools.JsonResp({"message": "Bot update is not available"}, 400)
        data = request.json
        self.defaults.update(data)
        botId = app.db.bots.update_one(
            {"_id": ObjectId(data["_id"])}, {"$set": self.defaults}, upsert=False
        )
        if botId.acknowledged:
            resp = tools.JsonResp(
                {"message": "Successfully updated bot", "botId": data["_id"]}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Failed to update bot"}, 400)

        return resp

    def delete(self, id):
        resp = tools.JsonResp({"message": "Bot update is not available"}, 400)
        id = request.view_args["id"]
        delete_action = app.db.bots.delete_one({"_id": ObjectId(id)})
        if delete_action:
            resp = tools.JsonResp(
                {"message": "Successfully delete bot", "botId": id}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Bot deletion is not available"}, 400)
        return resp
    
    def required_field_validation(self, data, key):
        if key in data:
            return data[key]
        else:
            resp = tools.JsonResp(
                {
                    "message": "Validation failed {} is required".format(key),
                    "botId": data["_id"],
                },
                400,
            )
            return resp

    def activate(self):
        resp = tools.JsonResp({"message": "Bot activation is not available"}, 400)
        findId = request.view_args["botId"]
        bot = app.db.bots.find_one({"_id": ObjectId(findId)})
        btc_balance = self.get_one_balance()
        if bot:
            # bot["active"] = "true"
            dealId = Deal(bot, app).open_deal()
            if dealId:
                if "deals" not in bot.keys():
                    bot["deals"] = []
                bot["deals"].append(dealId)
                botId = app.db.bots.save(bot)
                if botId:
                    resp = tools.JsonResp(
                        {"message": "Successfully activated bot", "bodId": str(findId)},
                        200,
                    )
                else:
                    resp = tools.JsonResp(
                        {"message": "Bot failed to save", "bodId": str(findId)}, 400
                    )
                return resp
            else:
                resp = tools.JsonResp(
                    {"message": "Deal creation failed", "botId": findId}, 400
                )
        else:
            resp = tools.JsonResp({"message": "Bot not found", "botId": findId}, 400)
        return resp

    def deactivate(self):
        resp = tools.JsonResp({"message": "Bot deactivation is not available"}, 400)
        findId = request.view_args["botId"]
        bot = app.db.bots.find_one({"_id": ObjectId(findId)})
        if bot:
            bot["active"] = "false"
            # Deal(bot).open_deal()
            resp = tools.JsonResp(
                {"message": "Successfully deactivated bot", "data": bot}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Bot not found", "botId": findId}, 400)
        return resp
