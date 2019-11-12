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
import requests
import pandas as pd
import json
from main import tools
from main.account.models import Account
from main.tools import Ticker24Data

class Bot(Account, Ticker24Data):

    def __init__(self):
        self.defaults = {
            "pairs": "",
            "active": False,
            "strategy": 'long',
            "name": 'Default Bot',
            "max_so_count": 3,
            "balance_usage": 1, # 100% of All Btc balance
            "balance_usage_size": 0.0001,
            "base_order_size": 0.003, # MIN by Binance = 0.0001 BTC
            "base_order_type": 'limit',
            "start_condition": True,
            "so_size": 0.0001, # Top band 
            "take_profit": 0.003,
            "price_deviation_so": 0.0063, # % percentage
            "trailling": False,
            "trailling_deviation": 0.0063,
            "deal_min_value": 0,
            "cooldown": 0,
            "active": False
        }

    def get_base_order_size(self, take_profit=0.03):
        df = Ticker24Data(app).api_data()
        #  * self.balance_division
        return 0.0001

    def get_so_size(self):
        return 0.0001

    def get_start_condition(self):
        return True

    def get(self):
        resp = tools.JsonResp({ "message": "No bots found" }, 200)
        bot = list(app.db.bots.find())
        if bot:
            resp = tools.JsonResp({ "data": bot }, 200)
        else:
            resp = tools.JsonResp({ "message": "Bots not found" }, 404)

        return resp

    def create(self):
        resp = tools.JsonResp({ "message": "Bot creation not available" }, 400)
        data = json.loads(request.data)

        new_bot = {
            "pairs": data['pairs'],
            "active": data['active'] or False,
            "strategy": data['strategy'] or 'long',
            "name": data['name'] or 'Default Bot',
            "max_so_count": data['maxSOCount'] or 3,
            "balance_usage": data['balanceUsage'], # 100% of All Btc balance
            "balance_usage_size": data['balanceUsage'] * Account().get_balances(),
            "base_order_size": self.get_base_order_size(data['take_profit']) or 0.003, # MIN by Binance = 0.0001 BTC
            "base_order_type": data['baseOrderType'],
            "start_condition": self.get_start_condition() or True,
            "so_size": self.get_so_size(), # Top band 
            "take_profit": data['takeProfit'] or 0.003,
            "price_deviation_so": data['priceDeviationSO'] or 0.0063, # % percentage
            "trailling": data['trailling'] or False,
            "trailling_deviation": data['trailling_deviation'] or 0.0063,
            "deal_min_value": data['dealMinValue'] or 0,
            "cooldown": data['cooldown'] or 0,
            "active": data['active'] or False
        }
        self.defaults.update(new_bot)
        botId = app.db.bots.save(new_bot)
        if (botId):
            resp = tools.JsonResp({"message": "Successfully created new bot", "botId": str(botId)}, 200)
        else:
            resp = tools.JsonResp({ "message": "Failed to create new bot" }, 400)
            

        return resp

    def edit(self):
        resp = tools.JsonResp({ "message": "Bot update is not available" }, 400)
        data = json.loads(request.data)

        existent_bot = {
            "pairs": data['pairs'],
            "name": data['name'],
            "bot_type": data['botType'],
            "base_order_size": data['baseOrderSize'], # MIN by Binance = 0.0001 BTC
            "base_order_type": data['baseOrderType'],
            "start_condition": data['startCondition'],
            "max_so_count": data['maxSOCount'],
            "so_size": self.so_size, # Top band 
            "price_deviation_so": 0.63, # % percentage
            "deal_min_value": self.deal_min_value,
            "cooldown": self.cooldown,
            "active": data['active']
        }
        
        botId = app.db.bots.update_one({ "_id": data["_id"] }, { "$set": existent_bot }, upsert=False)
        if (botId.acknowledged):
            resp = tools.JsonResp({"message": "Successfully updated bot", "botId": data["_id"]}, 200)
        else:
            resp = tools.JsonResp({ "message": "Failed to update bot" }, 400)
        
        return resp

    def delete(self, id):
        resp = tools.JsonResp({ "message": "Bot update is not available" }, 400)
        id = request.view_args['id']
        delete_action = app.db.bots.delete_one({ "_id": id })
        if (delete_action):
            resp = tools.JsonResp({ "message": "Successfully delete bot", "botId": id }, 200)
        else:
            resp = tools.JsonResp({ "message": "Bot deletion is not available" }, 400)
        return resp