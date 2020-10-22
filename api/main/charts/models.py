import json
import os

import pandas as pd
import requests
from flask import request
from main.tools.jsonresp import jsonResp


class Candlestick:
    """
    Return Plotly format of Candlestick
    https://plotly.com/javascript/candlestick-charts/
    """
    candlestick_url = os.getenv("CANDLESTICK")

    def __init__(self):
        pair = request.view_args["pair"]
        params = {'symbol': pair, 'interval': "5m", "limit": "200"}
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

    def layout(self):
        defaults = {
            "dragmode": 'zoom',
            "autosize": "true",
            "line_width": 50,
            "margin": {
                "r": 10,
                "t": 25,
                "b": 40,
                "l": 60
            },
            "showlegend": "false",
            "xaxis": {
                "autorange": "true",
                "title": 'Date',
                "type": 'date'
            },
            "yaxis": {
                "domain": [0, 1],
                "tickformat": '.10f',
                "type": 'linear',
                "maxPoints": 50
            }
        }
        return defaults

    def get(self):
        trace = json.dumps(self.candlestick_trace())
        layout = json.dumps(self.layout())

        resp = jsonResp({"trace": trace, "layout": layout}, 200)
        return resp
