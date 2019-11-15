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

class Deal(Buy_Order):

    def __init__(self, bot):
        self.active_bot = bot

    def open_deal(self):
        symbol = self.active_bot.pairs
        # Long bot
        buy_order = Buy_Order(symbol).last_order_book_price()
        return buy_order


