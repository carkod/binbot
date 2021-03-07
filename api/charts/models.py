import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from api.tools.handle_error import handle_error
from api.tools.jsonresp import jsonResp
from flask import request


class Candlestick:
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """
    candlestick_url = os.getenv("CANDLESTICK")

    def __init__(self):
        pair = request.view_args["pair"]
        interval = request.view_args["interval"] if "interval" in request.view_args else "5m"
        params = {'symbol': pair, 'interval': interval, "limit": "200"}
        url = self.candlestick_url
        res = requests.get(url=url, params=params)
        self.data = res.json()
        self.dates = None

    def _dates(self):
        data = self.data
        df = pd.DataFrame(data)
        x = df[0].tolist()
        return x

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

    def candlestick_trace(self):
        self.dates = self._dates()
        defaults = {
            "x": self.dates,
            "close": self._close_prices(),
            "high": self._high_prices(),
            "low": self._low_prices(),
            "open": self._open_prices(),
            "decreasing": {"line": {"color": 'red'}},
            "increasing": {"line": {"color": 'green'}},
            "line": {"color": '#17BECF'},
            "type": "candlestick",
            "xaxis": "x",
            "yaxis": "y",
        }
        return defaults

    def get(self):
        trace = self.candlestick_trace()
        resp = jsonResp({"trace": [trace]}, 200)
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
        params = {'symbol': pair, 'interval': interval, "limit": lastMonth.day, "startTime": startTime}
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
            "type": 'scatter',
            "mode": 'lines+markers'
        }
        resp = jsonResp({"message": "Successfully retrieved data", "data": trace}, 200)
        return resp
