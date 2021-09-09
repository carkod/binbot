import requests
import pandas as pd
import os

class Ticker24Data:
    def __init__(self, app):
        self.ticker24_url = os.environ["TICKER24"]

    def request_data(self):
        r = requests.get(self.ticker24_url)
        data = r.json()
        return data

    def formatData(self, data):
        df = pd.DataFrame(data)
        return df

    def api_data(self):
        return self.formatData(self.request_data())
