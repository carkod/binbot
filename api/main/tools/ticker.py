
import requests
import sys
import pandas as pd
import os

class Ticker24Data():

    def __init__(self, app):
        self.base_url = os.environ['BASE']    
        self.ticker24_url = os.environ['TICKER24']

    def request_data(self):
        r = requests.get(self.base_url + self.ticker24_url)
        data = r.json()
        return data

    def formatData(self, data):
        df = pd.DataFrame(data)
        return df

    def api_data(self):
        return self.formatData(self.request_data())



# class Ticker_Price:

#     ticker_price =  os.environ['TICKER_PRICE']

#     def __init__(self):
#         """Request only ticker24 data
#         """

#     def request_data(self, symbol=None):
#         url = base_url + self.ticker_price
#         params = {'symbol': symbol }
#         r = requests.get(url=url, params=params)
#         data = r.json()
#         return data

#     def formatData(self, data):
#         df = pd.DataFrame(data)
#         return df

#     def api_data(self):
#         return self.formatData(self.request_data())


# class Average_price:

#     average_price =  os.environ['AVERAGE_PRICE']

#     def __init__(self):
#         """Request only ticker24 data
#         """

#     def request_data(self, symbol=None):
#         url = base_url + self.average_price
#         params = {'symbol': symbol }
#         r = requests.get(url=url, params=params)
#         data = r.json()
#         return data

#     def formatData(self, data):
#         df = pd.DataFrame(data)
#         return df

#     def api_data(self):
#         return self.formatData(self.request_data())
