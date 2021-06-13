import os

import pandas as pd
import requests
from api.account.models import Account
from api.app import create_app
from api.tools.jsonresp import jsonResp_message, jsonResp
from api.tools.round_numbers import round_numbers
from scipy import stats
from flask import request


class Correlation(Account):
    candlestick_url = os.getenv("CANDLESTICK")

    def __init__(self):
        self.correlation_data = {
            "market_a": "",
            "market_b": "",
            "r_correlation": "",
            "p_value": "",
        }
        self.app = create_app()

    def candlestick_request(self, pair, interval="5m", limit="300"):
        params = {"symbol": pair, "interval": interval, "limit": limit}
        res = requests.get(url=self.candlestick_url, params=params)
        return res.json()

    def trigger_r(self, interval="1d", limit="20"):
        app = self.app
        symbols = self.get_exchange_info()["symbols"]
        symbols_count = len(symbols) * 2
        total_count = 0
        poll_percentage = 0

        app.db.correlations.remove()
        for i in range(symbols_count):
            for j in range(symbols_count):
                market_a = symbols[j]["symbol"]
                market_b = symbols[i]["symbol"]
                if market_a == market_b:
                    break
                candlestick_a = self.candlestick_request(market_a, interval, limit)
                df_a = pd.DataFrame(candlestick_a)
                close_a = df_a[4].astype(float).tolist()

                candlestick_b = self.candlestick_request(market_b, interval, limit)
                df_b = pd.DataFrame(candlestick_b)
                close_b = df_b[4].astype(float).tolist()

                r = stats.pearsonr(close_a, close_b)
                data = {
                    "market_a": market_a,
                    "market_b": market_b,
                    "r_correlation": r[0],
                    "p_value": r[1],
                }
                app.db.correlations.insert_one(data)
                if total_count <= ((symbols_count) - 1):
                    poll_percentage = round_numbers(
                        (total_count / symbols_count) * 100, 0
                    )
                    total_count += 1

                print(f"Pearson correlation scanning: {poll_percentage}%")

    def response(self):
        resp = jsonResp_message("Pearson correlation scanning started", 200)
        return resp

    def get_pearson(self):
        args = {}
        if request.args.get("market_b"):
            args["market_b"] = request.args.get("market_b")
        if request.args.get("market_a"):
            args["market_a"] = request.args.get("market_a")
        if request.args.get("filter"):
            value = request.args.get("filter")
            if value == "positive":
                args["r_correlation"] = {"$gt": 0}
            else:
                args["r_correlation"] = {"$lt": 0}

        query = self.app.db.correlations.find(args).sort("r_correlation", 1)
        data = list(query)
        resp = jsonResp({"data": data}, 200)
        return resp

    def get_signals(self):
        args = {"bollinguer_bands_signal": {"$exists": True, "$ne": None}}

        query = self.app.db.correlations.find(args).sort([["bollinguer_bands_signal", 1], ["lastModified", -1]])
        data = list(query)
        resp = jsonResp({"data": data}, 200)
        return resp
