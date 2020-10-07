import os

 
 

class API_URL:
    BINANCEAPI_BASE = 'https://api.binance.com'
    BINANCEAPI_TICKER24 = '/api/v1/ticker/24hr'
    BINANCEAPI_CANDLESTICK = '/api/v1/klines'
    BINANCEAPI_TICKER_PRICE = '/api/v3/ticker/price'
    BINANCEAPI_ACCOUNT = '/api/v3/account'
    BINANCEAPI_EXCHANGE_INFO = '/api/v1/exchangeInfo'
    BINANCEAPI_ORDER = '/api/v3/order'
    BINANCEAPI_OPEN_ORDERS = '/api/v3/openOrders'
    BINANCEAPI_ALL_ORDERS = '/api/v3/allOrders'
    BINANCEAPI_AVERAGE_PRICE = '/api/v3/avgPrice'
    BINANCE_KEY = os.getenv("BINANCE_KEY")
    BINANCE_SECRET = os.getenv("BINANCE_SECRET")
    BINBOARD_PROD_ENV = True if os.getenv("BINBOARD_PROD_ENV") == 'True' else False
    BINBOARD_DEV_ENV = True if bool(os.getenv("BINBOARD_DEV_ENV")) == 'True' else False
    BINBOARD_WITHDRAW = '/wapi/v3/withdraw.html'
    BINBOARD_DEPOSIT_HISTORY = '/wapi/v3/depositHistory.html'
    BINBOARD_WITHDRAW_HISTORY = '/wapi/v3/withdrawHistory.html'
    BINBOARD_DEPOSIT_ADDRESS = '/wapi/v3/depositAddress.html'
