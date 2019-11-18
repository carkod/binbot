from flask import Flask, request, current_app as app
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
from main.tools import EnumDefinitions, handle_error 
from main.account import Account
from main.deals.services import Buy_Order

class Deal():

    def __init__(self, bot):
        self.active_bot = bot
        self.symbol = bot['pair']
        self.botname = bot['name']
        self.base_order_size = bot['base_order_size']
        self.active = bot['active']
        self.balance = bot['balance_usage_size']
        self.base_order_type = bot['base_order_type']
        self.max_so_count = bot['max_so_count']
        self.price_deviation_so = bot['price_deviation_so']
        self.so_size = bot['so_size']
        self.take_profit = bot['take_profit']
        self.trailling = bot['trailling']
        self.trailling_deviation = bot['trailling_deviation']

    def open_deal(self):
        base_order = Buy_Order(symbol=self.symbol, quantity=self.base_order_size, type=self.base_order_type).post_order_limit()

        
        return 


