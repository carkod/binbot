import os

import pandas as pd
import requests
from api.account.account import Account
from api.app import create_app
from api.tools.handle_error import jsonResp_message, jsonResp
from api.tools.round_numbers import round_numbers
from scipy import stats
from flask import request

poll_percentage = 0

class Correlation(Account):
    candlestick_url = os.getenv("CANDLESTICK")

    def __init__(self):
        self.app = create_app()

    def candlestick_request(self, pair, interval="5m", limit="300"):
        params = {"symbol": pair, "interval": interval, "limit": limit}
        res = requests.get(url=self.candlestick_url, params=params)
        return res.json()

    def trigger_r(self, interval="1d", limit="20"):
        app = self.app
        symbols = self._exchange_info()["symbols"]
        symbols_count = len(symbols)
        total_count = 0
        global poll_percentage
        poll_percentage = 0

        app.db.correlations.remove()
        for i in range(symbols_count):
            for j in range(symbols_count):
                market = symbols[j]["symbol"]
                r_market = symbols[i]["symbol"]
                if market == r_market:
                    break
                candlestick_a = self.candlestick_request(market, interval, limit)
                df_a = pd.DataFrame(candlestick_a)
                close_a = df_a[4].astype(float).tolist()

                candlestick_b = self.candlestick_request(r_market, interval, limit)
                df_b = pd.DataFrame(candlestick_b)
                close_b = df_b[4].astype(float).tolist()

                # Not enough data to calculate r_correlation
                # New crytos have little data from Binance API
                if len(close_a) < int(limit) or len(close_b) < int(limit):
                    r_correlation = None
                else:
                    r = stats.pearsonr(close_a, close_b)
                    r_correlation = {
                        "r_market": r_market,
                        "r": r[0],
                        "p_value": r[1],
                    }

                data = {
                    "market": market,
                    "r_correlation": r_correlation,
                    "current_price": "",
                    "volatility": "",
                    "last_volume": 0,
                    "spread": 0,
                    "price_change_24": 0,  # MongoDB can't sort string decimals
                    "candlestick_signal": "",
                    "blacklisted": False,
                    "blacklisted_reason": ""
                }
                app.db.correlations.insert_one(data)
                if i <= ((symbols_count) - 1):
                    poll_percentage = round_numbers(
                        (total_count / (symbols_count * 2)) * 100, 0
                    )
                    total_count += 1

                print(f"Pearson correlation scanning: {poll_percentage}%")

    def response(self):
        """
        Start scanning
        """
        resp = jsonResp_message("Pearson correlation scanning started")
        return resp

    def block_response(self):
        """
        Scanning already in progress
        """
        global poll_percentage
        resp = jsonResp_message(f"Pearson correlation scanning is in progress {poll_percentage}%")
        return resp

    def get_signals(self):
        args = {"candlestick_signal": {"$exists": True, "$ne": None}}
        sort = []
        if request.args.get("filter_by") == "signal_side":
            signal_side = {
                "signal_side": request.args.get("filter")
            }
            args.update(signal_side)
        if request.args.get("filter_by") == "signal_strength":
            signal_side = {
                "signal_strength": request.args.get("filter")
            }
            args.update(signal_side)

        if request.args.get("filter_by") == "candlestick_signal":
            signal_side = {
                "candlestick_signal": request.args.get("filter")
            }
            args.update(signal_side)

        query = self.app.db.correlations.find(args)

        if request.args.get("order_by") == "spread":
            sort = [["spread", int(request.args.get("order"))]]
            query.sort(sort)

        if request.args.get("order_by") == "price_change_24":
            sort = [["price_change_24", int(request.args.get("order"))]]
            query.sort(sort)

        data = list(query)
        resp = jsonResp({"data": data})
        return resp

    def post_blacklisted(self):
        args = {}
        set = {}
        data = request.json
        if data.get("symbol"):
            args["market"] = data.get("symbol")
            set["blacklisted"] = True
            set["blacklisted_reason"] = data.get("reason")

        query = self.app.db.correlations.find_one_and_update(args, {"$set": set})

        if query:
            resp = jsonResp({"data": query})
            return resp
        else:
            resp = jsonResp({"error": 1, "data": query})

    def get_blacklisted(self):
        """
        Get blacklisted symbol research data
        """
        args = {"candlestick_signal": {"$exists": True, "$ne": None}}
        query = self.app.db.correlations.find(args)
        if query:
            resp = jsonResp({"error": 0, "data": query})
            return resp
        else:
            resp = jsonResp({"error": 1, "data": query})
