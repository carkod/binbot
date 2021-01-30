
import requests
import sys
import pandas as pd
import os
from datetime import timedelta

class Ticker24Data:

    def __init__(self, app):
        self.ticker24_url = os.environ['TICKER24']

    def request_data(self):
        r = requests.get(self.ticker24_url)
        data = r.json()
        return data

    def formatData(self, data):
        df = pd.DataFrame(data)
        return df

    def api_data(self):
        return self.formatData(self.request_data())

class Conversion:
    nomics_key = os.environ['COINAPI_KEY']
    url = os.environ['COINAPI_EXG_URL']

    def get_conversion(self, time):

        params = {
            "apikey": self.nomics_key,
            "time": time.replace(microsecond=0).isoformat(),
        }
        r = requests.get(self.url, params)
        data = r.json()
        rate = float(data["rate"])
        return rate
