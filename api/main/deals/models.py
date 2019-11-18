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
from dotenv import load_dotenv
import os

load_dotenv()

class Deal():

    def __init__(self, bot):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_url = os.getenv("BASE")
        self.order_url = os.getenv("ORDER")
        self.order_book_url = os.getenv("ORDER_BOOK")
        # Buy order
        self.side = EnumDefinitions.order_side[0]

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

    def last_order_book_price(self, limit_index, quantity):
        url = self.base_url + self.order_book_url
        limit = EnumDefinitions.order_book_limits[limit_index]
        params = [
          ('symbol', self.symbol),
          ('limit', limit),
        ]
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        df = pd.DataFrame(data['bids'], columns=['price','qty'])
        df['qty'] = df['qty'].astype(float)

        # If quantity matches list
        match_qty = df[df['qty'] > float(quantity)]
        condition = df['qty'] > float(quantity)
        if condition.any() == False:
            limit += limit
            self.last_order_book_price(limit)
        
        return match_qty['price'][0]

    def execute_base_order(self, order):
        base_order = {
            'deal_type': 'base_order',
            'order_id': order['orderId'],
            'type': order['base_order'],
            'strategy': 'long', # change accordingly
            'pair': order['symbol'],
            'order_side': order['side'],
            'order_type': order['type'],
            'price': order['price'],
            'qty': order['origQty'],
            'fills': order['fills'],
            'time_in_force': order['timeInForce']
        }
        if 'code' not in order:
            return base_order
        else:
            print(order)
            exit(1)

    def execute_take_profit_order(self, order):
        base_order = {
            'deal_type': 'take_profit',
            'order_id': order['orderId'],
            'type': order['base_order'],
            'strategy': 'long', # change accordingly
            'pair': order['symbol'],
            'order_side': order['side'],
            'order_type': order['type'],
            'price': order['price'],
            'qty': order['origQty'],
            'fills': order['fills'],
            'time_in_force': order['timeInForce']
        }
        if 'code' not in order:
            return base_order
        else:
            print(order)
            exit(1)


    def open_deal(self):
        new_deal = []
        # base_order = Buy_Order(symbol=self.symbol, quantity=self.base_order_size, type=self.base_order_type).post_order_limit()
        # tp_order = Sell_Order(symbol=self.symbol, quantity=self.base_order_size, type=self.base_order_type).post_order_limit()

        base_order = {
            'clientOrderId': 'KxwRuUmnQqgcs5y7KWU77t', 
            'cummulativeQuoteQty': '0.00000000', 
            'executedQty': '0.00000000', 
            'fills': [], 
            'orderId': 263599681, 
            'orderListId': -1, 
            'origQty': '4.00000000', 
            'price': '0.00039920', 
            'side': 'BUY', 
            'status': 'NEW', 
            'symbol': 'EOSBTC', 
            'timeInForce': 'GTC', 
            'transactTime': 1574040139349, 
            'type': 'LIMIT'
        }

        new_deal.append(self.execute_base_order(base_order))
        division = self.balance / (self.max_so_count + 2)
        so_qty = division
        so = []
        for index in range(self.max_so_count):
            price = self.last_order_book_price(0, so_qty) * (1 + self.price_deviation_so)
            so.append(price)
        for index in range(self.max_so_count):
            

            safety_order = Buy_Order(symbol=self.symbol, quantity=so_qty, type='LIMIT', limit_price=price).post_order_limit()
        
        return 


