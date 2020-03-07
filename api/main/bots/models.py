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
from main.account.models import Account
from main.tools import Ticker24Data
from main.deals.models import Deal
from bson.objectid import ObjectId


class Bot:
    def __init__(self):
        self.defaults = {
            "pair": "BTCUSDT",
            "active": False,
            "strategy": "long",
            "name": "Default Bot",
            "max_so_count": 3,
            "balance_usage": float(1),  # 100% of All Btc balance
            "balance_usage_size": 0.0001,
            "base_order_size": 0.003,  # MIN by Binance = 0.0001 BTC
            "base_order_type": "limit",
            "start_condition": True,
            "so_size": 0.0001,  # Top band
            "take_profit": 0.003,
            "price_deviation_so": 0.0063,  # % percentage
            "trailling": False,
            "trailling_deviation": 0.0063,
            "deal_min_value": 0,
            "cooldown": 0,
            "deals": [],
        }
        self.balance_division = 0
        self.active_bot = None

    def get_available_btc(self):
        data = json.loads(Account().get_balances().data)["data"]
        available_balance = 0
        for i in range(len(data)):
            if data[i]["asset"] == "BTC":
                available_balance = data[i]["free"]
                return available_balance
        return available_balance

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
        bot = list(app.db.bots.find_one({"_id": findId}))

        if bot:
            resp = tools.JsonResp({"data": bot}, 200)
        else:
            resp = tools.JsonResp({"message": "Bots not found"}, 404)
        return resp

    def create(self):
        resp = tools.JsonResp({"message": "Bot creation not available"}, 400)
        data = json.loads(request.data)
        btc_balance = self.get_available_btc()
        # base_order_size = self.get_base_order_size(data['pair'], data['maxSOCount'], data['take_profit'])
        new_bot = {
            "pair": data["pair"],
            "active": data["active"] or False,
            "strategy": data["strategy"] or "long",
            "name": data["name"] or "Default Bot",
            "max_so_count": data["maxSOCount"] or 3,
            "balance_usage": data["balanceUsage"],  # 100% of All Btc balance
            "balance_usage_size": float(data["balanceUsage"]) * btc_balance,
            "base_order_size": data["baseOrderSize"] or 0.0001,  # MIN by Binance = 0.0001 BTC
            "base_order_type": data["baseOrderType"],  # Market or limit
            "start_condition": True,
            "so_size": data["soSize"] or 0.0001,  # Top band
            "take_profit": data["takeProfit"] or 0.003,
            "price_deviation_so": data["priceDeviationSO"] or 0.0063,  # % percentage
            "trailling": data["trailling"] or False,
            "trailling_deviation": data["traillingDeviation"] or 0.0063,
            "deal_min_value": data["dealMinValue"] or 0,
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

        existent_bot = {
            "pair": data["pair"],
            "active": data["active"] or False,
            "strategy": data["strategy"] if data.get("strategy") else "long",
            "name": data["name"] if data.get("name") else "Default Bot",
            "max_so_count": data["maxSOCount"] if data.get("maxSOCount") else 3,
            "balance_usage": data["balanceUsage"]
            if data.get("balanceUsage") else 1,  # 100% of All Btc balance
            "base_order_size": data["baseOrderSize"],  # MIN by Binance = 0.0001 BTC
            "base_order_type": data["baseOrderType"]
            if data.get("baseOrderType") else "limit",  # Market or limit
            "start_condition": True,
            "so_size": data["soSize"],  # Top band
            "take_profit": data["takeProfit"],
            "price_deviation_so": data["priceDeviationSO"],  # % percentage
            "trailling": data["trailling"],
            "trailling_deviation": data["traillingDeviation"],
            "deal_min_value": data["dealMinValue"],
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
            bot["active"] = True
            dealId = Deal(bot, app).open_deal()
            if dealId:
                if "deals" not in bot.keys():
                    bot["deals"] = []
                bot["deals"].append(dealId)
                botId = app.db.bots.save(bot)
                if botId:
                    botId = ObjectId(botId)
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