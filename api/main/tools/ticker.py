
import requests
import sys
import pandas as pd

class Ticker24Data():

    def __init__(self, app):
        self.base_url = app.config['BASE']    
        self.ticker24_url = app.config['TICKER24']

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

#     ticker_price = app.config['TICKER_PRICE']

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

#     average_price = app.config['AVERAGE_PRICE']

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
