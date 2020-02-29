from dotenv import load_dotenv
from flask import Flask, request
from flask import current_app as app
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
import os


load_dotenv()


class Sell_Order:
    """Post order

    Returns:
        [type] -- [description]
    """

    timestamp = int(round(tm.time() * 1000))
    recvWindow = 10000
    # Min amount to be considered for investing (BNB)
    min_funds = 0.000000

    def __init__(self):
        self.key = os.getenv("BINANCE_KEY")
        self.secret = os.getenv("BINANCE_SECRET")
        self.base_url = os.getenv("BASE")
        self.order_url = os.getenv("ORDER")
        self.order_book_url = os.getenv("ORDER_BOOK")
        # Buy order
        self.side = EnumDefinitions.order_side[1]
        # Required by API for Limit orders
        self.timeInForce = EnumDefinitions.time_in_force[0]

    """
    Returns successful order
    Returns validation failed order (MIN_NOTIONAL, LOT_SIZE etc..)
    """

    def post_order_limit(self):
        data = json.loads(request.data)
        symbol = data["pair"]
        qty = data["qty"]
        price = data["price"]

        # Limit order
        type = EnumDefinitions.order_types[0]
        timestamp = int(round(tm.time() * 1000))
        url = self.base_url + self.order_url

        # Get data for a single crypto e.g. BTT in BNB market
        params = [
            ("recvWindow", self.recvWindow),
            ("timestamp", timestamp),
            ("symbol", symbol),
            ("side", self.side),
            ("type", type),
            ("timeInForce", self.timeInForce),
            ("price", price),
            ("quantity", qty),
        ]
        headers = {"X-MBX-APIKEY": self.key}

        # Prepare request for signing
        r = requests.Request("POST", url=url, params=params, headers=headers)
        prepped = r.prepare()
        query_string = urlparse(prepped.url).query
        total_params = query_string

        # Generate and append signature
        signature = hmac.new(
            self.secret.encode("utf-8"), total_params.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params.append(("signature", signature))

        # Response after request
        res = requests.post(url=url, params=params, headers=headers)
        handle_error(res)
        data = res.json()
        return data
