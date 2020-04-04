from flask import current_app as app
from flask import Flask, request
from passlib.hash import pbkdf2_sha256
from jose import jwt
from main import tools
from main import auth
import json
import time as tm
import hashlib
import hmac
import math
import sys
import time as tm
from urllib.parse import urlparse
import pandas as pd
import json
from main import tools
from main.account.controllers import Account, Balances
from main.tools import Ticker24Data
from main.deals.controllers import Deal
from bson.objectid import ObjectId


class Bot:
    def __init__(self):
        self.defaults = {
            "pair": "BTCUSDT",
            "active": False,
            "strategy": "long",
            "name": "Default Bot",
            "max_so_count": 3,
            "balance_usage": "1",  # 100% of All Btc balance
            "balance_usage_size": "0.0001",
            "base_order_size": "0.003",  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "start_condition": True,
            "so_size": "0.0001",  # Top band
            "take_profit": "0.003",
            "price_deviation_so": "0.0063",  # % percentage
            "trailling": False,
            "trailling_deviation": "0.0063",
            "deal_min_value": 0,
            "cooldown": 0,
            "deals": [],
        }
        self.balance_division = 0
        self.active_bot = None

    def get_start_condition(self):
        return True

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
        findId = ObjectId(request.view_args["id"])
        bot = app.db.bots.find_one({"_id": findId})

        if bot:
            resp = tools.JsonResp({"data": bot}, 200)
        else:
            resp = tools.JsonResp({"message": "Bots not found"}, 404)
        return resp

    def create(self):
        resp = tools.JsonResp({"message": "Bot creation not available"}, 400)
        data = json.loads(request.data)
        get_available_funds = Balances().get_base_balance(data["pair"])
        
        new_bot = {
            "pair": data["pair"],
            "active": data["active"] or False,
            "strategy": data["strategy"] or "long",
            "name": data["name"] or "Default Bot",
            "max_so_count": data["max_so_count"] or 3,
            "balance_usage": data["balance_usage"],  # 100% of All Btc balance
            "balance_usage_size": str(float(data["balance_usage"]) * get_available_funds),
            "base_order_size": data["base_order_size"] or "0.0001",  # MIN by Binance = 0.0001 BTC
            "base_order_type": data["base_order_type"],  # Market or limit
            "start_condition": True,
            "so_size": data["so_size"] or "0.0001",  # Top band
            "take_profit": data["take_profit"] or "0.003",
            "price_deviation_so": data["price_deviation_so"] or "0.0063",  # % percentage
            "trailling": data["trailling"] or False,
            "trailling_deviation": data["trailling_deviation"] or "0.0063",
            "deal_min_value": data["deal_min_value"] or 0,
            "cooldown": data["cooldown"] or 0,
        }
        self.defaults.update(new_bot)
        botId = app.db.bots.save(new_bot)
        if botId:
            resp = tools.JsonResp(
                {"message": "Successfully created new bot", "botId": str(botId)}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Failed to create new bot"}, 400)

        return resp

    def edit(self):
        resp = tools.JsonResp({"message": "Bot update is not available"}, 400)
        data = json.loads(request.data)
        get_available_funds = Balances().get_base_balance(data["pair"])

        existent_bot = {
            "pair": data["pair"],
            "active": data["active"] or False,
            "strategy": data["strategy"] if data.get("strategy") else "long",
            "name": data["name"] if data.get("name") else "Default Bot",
            "max_so_count": data["max_so_count"] if data.get("max_so_count") else 3,
            "balance_usage": data["balance_usage"]
            if data.get("balance_usage") else 1,  # 100% of All Btc balance
            "balance_usage_size": str(float(data["balance_usage"]) * get_available_funds),
            "base_order_size": data["base_order_size"],  # MIN by Binance = 0.0001 BTC
            "base_order_type": data["base_order_type"]
            if data.get("base_order_type") else "limit",  # Market or limit
            "start_condition": True,
            "so_size": data["so_size"],  # Top band
            "take_profit": data["take_profit"],
            "price_deviation_so": data["price_deviation_so"],  # % percentage
            "trailling": data["trailling"],
            "trailling_deviation": data["trailling_deviation"],
            "deal_min_value": data["deal_min_value"],
            "cooldown": data["cooldown"],
        }

        self.defaults.update(existent_bot)
        botId = app.db.bots.update_one(
            {"_id": ObjectId(data["_id"])}, {"$set": existent_bot}, upsert=False
        )
        if botId.acknowledged:
            resp = tools.JsonResp(
                {"message": "Successfully updated bot", "botId": data["_id"]}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Failed to update bot"}, 400)

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

    def delete(self, id):
        resp = tools.JsonResp({"message": "Bot update is not available"}, 400)
        id = ObjectId(request.view_args["id"])
        delete_action = app.db.bots.delete_one({"_id": id})
        if delete_action:
            resp = tools.JsonResp(
                {"message": "Successfully delete bot", "botId": id}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Bot deletion is not available"}, 400)
        return resp

    def activate(self):
        resp = tools.JsonResp({"message": "Bot activation is not available"}, 400)
        findId = ObjectId(request.view_args["botId"])
        bot = app.db.bots.find_one({"_id": findId})
        if bot:
            dealId = Deal(bot).open_deal()
            if dealId["code"]:
                resp = tools.JsonResp(dealId, 200)
                return dealId
            if dealId:
                if "deals" not in bot.keys():
                    bot["deals"] = []
                bot["deals"].append(dealId)
                botId = app.db.bots.save(bot)
                if botId:
                    botId = ObjectId(botId)
                    # Only flag active if everything went well
                    bot["active"] = True
                    resp = tools.JsonResp(
                        {"message": "Successfully activated bot", "bodId": botId},
                        200,
                    )
                else:
                    resp = tools.JsonResp(
                        {"message": "Bot failed to save", "bodId": findId}, 400
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
        findId = ObjectId(request.view_args["botId"])
        bot = app.db.bots.find_one({"_id":findId })
        if bot:
            bot.active = False
            resp = tools.JsonResp(
                {"message": "Successfully deactivated bot", "data": bot}, 200
            )
        else:
            resp = tools.JsonResp({"message": "Bot not found", "botId": findId}, 400)
        return resp


    # @app.errorhandler(200)
    # def page_not_found(e):
    #     if e["msg"]:
    #         print(e["msg"])
    #         flask.abort(404)