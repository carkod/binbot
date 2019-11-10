import os

from dotenv import load_dotenv
load_dotenv()

class Binance_api:
  BASE = 'https://api.binance.com'
  TICKER24 = '/api/v1/ticker/24hr'
  CANDLESTICK = '/api/v1/klines'
  TICKER_PRICE = '/api/v3/ticker/price'
  ACCOUNT = '/api/v3/account'
  EXCHANGE_INFO = '/api/v1/exchangeInfo'
  ORDER = '/api/v3/order'
  OPEN_ORDERS = '/api/v3/openOrders'
  ALL_ORDERS = '/api/v3/allOrders'
  AVERAGE_PRICE = '/api/v3/avgPrice'
  BINANCE_KEY = os.getenv("BINANCE_KEY")
  BINANCE_SECRET = os.getenv("BINANCE_SECRET")
  WITHDRAW = '/wapi/v3/withdraw.html'
  DEPOSIT_HISTORY = '/wapi/v3/depositHistory.html'
  WITHDRAW_HISTORY = '/wapi/v3/withdrawHistory.html'
  DEPOSIT_ADDRESS = '/wapi/v3/depositAddress.html'

class Binboard:
  BINBOARD_PROD_ENV = True if os.getenv("BINBOARD_PROD_ENV") == 'True' else False
  BINBOARD_DEV_ENV = True if bool(os.getenv("BINBOARD_DEV_ENV")) == 'True' else False
  