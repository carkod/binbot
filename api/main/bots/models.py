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


class Bot:

    def __init__(self, pairs='BTCUSDT', bot_type='LONG', base_order_size=0.0001, start_condition=False):
        self.pairs = pairs
        self.name = 'BOT default name'
        self.bot_type = bot_type # LONG OR SHORT
        self.base_order_size = base_order_size # MIN by Binance = 0.0001 BTC
        self.base_order_type = 'LIMIT'
        self.start_condition = start_condition
        self.max_so_count = 3
        self.so_size = 0.0001 # Top band 
        self.price_deviation_so = 0.63 # % percentage
        self.deal_min_value = 0
        self.cooldown = 3000
        self.active = False
    

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