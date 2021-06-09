import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp
from flask import request
import threading


class Candlestick:
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """

    candlestick_url = os.getenv("CANDLESTICK")

    def __init__(self, interval="1m", limit="200"):
        pair = request.view_args["pair"]
        params = {"symbol": pair, "interval": interval, "limit": limit}
        res = requests.get(url=self.candlestick_url, params=params)
        self.data = res.json()
        df = pd.DataFrame(self.data)
        dates = df[0].tolist()
        self.dates = dates

    def _close_prices(self):
        data = self.data
        df = pd.DataFrame(data)
        close = df[4].tolist()
        return close

    def _high_prices(self):
        data = self.data
        df = pd.DataFrame(data)
        high = df[2].tolist()
        return high

    def _low_prices(self):
        data = self.data
        df = pd.DataFrame(data)
        low = df[3].tolist()
        return low

    def _open_prices(self):
        data = self.data
        df = pd.DataFrame(data)
        open = df[1].tolist()
        return open

    def _ma_data(self, limit):
        pair = request.view_args["pair"]
        interval = (
            request.view_args["interval"] if "interval" in request.view_args else "5m"
        )
        params = {"symbol": pair, "interval": interval, "limit": limit}
        res = requests.get(url=self.candlestick_url, params=params)
        df = pd.DataFrame(res.json())
        close = df[4].tolist()
        return close

    def candlestick_trace(self):
        dates = self.dates
        defaults = {
            "x": dates,
            "close": self._close_prices(),
            "high": self._high_prices(),
            "low": self._low_prices(),
            "open": self._open_prices(),
            "decreasing": {"line": {"color": "red"}},
            "increasing": {"line": {"color": "green"}},
            "line": {"color": "#17BECF"},
            "type": "candlestick",
            "xaxis": "x",
            "yaxis": "y",
        }
        return defaults

    def bollinguer_bands(self):
        # 200 limit + 100 ma
        data = self._ma_data(300)
        dates = self.dates

        data_100 = data
        kline_df_100 = pd.DataFrame(data_100)

        data_25 = data
        kline_df_25 = pd.DataFrame(data_25)

        data_7 = data
        kline_df_7 = pd.DataFrame(data_7)

        ma_100 = {
            "x": dates,
            "y": kline_df_100[0].rolling(window=100).mean().dropna().reset_index(drop=True).values.tolist(),
            "line": {"color": "#9368e9"},
            "type": "scatter",
        }
        ma_25 = {
            "x": dates,
            "y": kline_df_25[0].rolling(window=25).mean().dropna().reset_index(drop=True).values.tolist()[76:],
            "line": {"color": "#fb404b"},
            "type": "scatter",
        }
        ma_7 = {
            "x": dates,
            "y": kline_df_7[0].rolling(window=7).mean().dropna().reset_index(drop=True).values.tolist()[94:],
            "line": {"color": "#ffa534"},
            "type": "scatter",
        }

        return ma_100, ma_25, ma_7

    def get(self):
        for thread in threading.enumerate():
            print(thread.name)
        trace = self.candlestick_trace()
        ma_100, ma_25, ma_7 = self.bollinguer_bands()
        resp = jsonResp({"trace": [trace, ma_100, ma_25, ma_7]}, 200)
        return resp

    def get_diff(self):
        today = datetime.today()
        first = today.replace(day=1)
        lastMonth = first - timedelta(days=1)
        # One month from today
        first_lastMonth = today - timedelta(days=lastMonth.day)
        startTime = int(round(first_lastMonth.timestamp() * 1000))

        pair = request.view_args["pair"]
        interval = request.view_args["interval"]
        params = {
            "symbol": pair,
            "interval": interval,
            "limit": lastMonth.day,
            "startTime": startTime,
        }
        url = self.candlestick_url
        res = requests.get(url=url, params=params)
        handle_error(res)
        data = res.json()
        df = pd.DataFrame(data)

        # New df with dates and close
        df_new = df[[0, 3]]
        df_new[3].astype(float)
        close_prices = df_new[3].astype(float).pct_change().iloc[1:].values.tolist()
        dates = df_new[0].iloc[1:].values.tolist()
        trace = {
            "x": dates,
            "y": close_prices,
            "type": "scatter",
            "mode": "lines+markers",
        }
        resp = jsonResp({"message": "Successfully retrieved data", "data": trace}, 200)
        return resp
